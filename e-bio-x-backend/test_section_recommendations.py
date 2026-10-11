# ============================================================
# FASE 3e - REKOMENDASI PER BAGIAN (section-level recommendation).
#
# Tujuan fitur: siswa tidak hanya diberi tahu materi mana yang perlu
# dibuka, tapi bagian mana di dalam materi itu yang paling perlu
# diperkuat - dan angka di balik peringkat itu harus benar-benar
# berasal dari jawabannya sendiri.
#
# Prinsip yang dipatok test ini:
#   - hanya bagian dengan diagnosis READY yang diberi SKOR; bagian
#     dengan jawaban < MIN_SECTION_SAMPLE dilaporkan apa adanya sebagai
#     "belum bisa dinilai" dengan skor NULL (tidak dikarang)
#   - "belum bisa dinilai" TIDAK pernah ditulis ke database, jadi tidak
#     ada angka 0.0 yang menyamar sebagai prioritas
#   - bagian yang sudah dikuasai (>= HIGH_MASTERY_CUTOFF) tidak
#     direkomendasikan, sama seperti aturan di level materi
#   - baris level-bagian dan level-materi hidup di tabel yang sama,
#     jadi keduanya harus terisolasi: menyegarkan materi tidak boleh
#     menghapus saran bagian, dan sebaliknya
#   - klik dengan section_id menandai baris BAGIAN saja; klik tanpa
#     section_id menandai baris MATERI saja
#   - evaluasi tertutup guru tetap hanya menghitung baris level-materi
#   - akses tetap ter-scope: siswa di luar kelas tidak melihat bagian
#     materi orang lain
#
# Berjalan pada app + database nyata, membuat lalu menghapus fixture
# miliknya sendiri. Baris lama hanya dibaca.
# ============================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.ml import ml_config as cfg  # noqa: E402
from src.ml.recommendation import score_section  # noqa: E402
from src.models.user import User  # noqa: E402
from src.models.course import Course  # noqa: E402
from src.models.enrollment import Enrollment  # noqa: E402
from src.models.material import Material  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.quiz import Quiz  # noqa: E402
from src.models.question import Question  # noqa: E402
from src.models.answer import Answer  # noqa: E402
from src.models.submission import Submission  # noqa: E402
from src.models.recommendation import Recommendation  # noqa: E402
from src.models.question_bank import QuestionBank  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402

STAMP = 'zzsecrec'
results = []
created = {}


def check(name, cond, extra=""):
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


def token_for(user):
    return create_access_token(identity=str(user.id))


def make_fixture():
    teacher = User(email=f'{STAMP}@test.local', name='Sec Rec Guru',
                   role='teacher')
    outsider = User(email=f'{STAMP}.outsider@test.local',
                    name='Sec Rec Murid Luar', role='student')
    student = User(email=f'{STAMP}.student@test.local', name='Sec Rec Murid',
                   role='student')
    db.session.add_all([teacher, outsider, student])
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    db.session.add(course)
    db.session.flush()
    db.session.add(Enrollment(student_id=student.id, course_id=course.id))
    db.session.flush()

    material = Material(title='Materi Uji Saran Bagian', course_id=course.id,
                        teacher_id=teacher.id, status='published',
                        topic='UJI SARAN BAGIAN')
    db.session.add(material)
    db.session.flush()

    # A: 4 dijawab / 3 benar  -> 75.0  (READY, tapi belum menguasai)
    # B: 4 dijawab / 1 benar  -> 25.0  (READY, paling lemah)
    # C: 2 dijawab            -> insufficient (ada bukti, belum cukup)
    # D: 0 dijawab            -> insufficient (belum disentuh)
    # E: 4 dijawab / 4 benar  -> 100.0 (sudah dikuasai, jangan disarankan)
    secs = [MaterialSection(material_id=material.id, title=t, position=i)
            for i, t in enumerate(['Bagian A', 'Bagian B', 'Bagian C',
                                   'Bagian D', 'Bagian E'])]
    db.session.add_all(secs)
    db.session.flush()

    quiz = Quiz(title='Kuis Saran Bagian', course_id=course.id,
                material_id=material.id, created_by=teacher.id, status='draft')
    db.session.add(quiz)
    db.session.flush()

    plan = [(secs[0], 4, 3), (secs[1], 4, 1), (secs[2], 2, 1), (secs[4], 4, 4)]
    questions = []
    order = 0
    for sec, total, _correct in plan:
        for i in range(total):
            q = Question(quiz_id=quiz.id, text=f'{sec.title} #{i}',
                         question_type='multiple_choice', difficulty='medium',
                         points=10, order_index=order, section_id=sec.id)
            db.session.add(q)
            questions.append(q)
            order += 1
    db.session.flush()

    sub = Submission(quiz_id=quiz.id, student_id=student.id, attempt_number=1,
                     score=50.0, percentage=50.0, correct_count=9,
                     wrong_count=5, unanswered_count=0, status='submitted')
    db.session.add(sub)
    db.session.flush()

    idx = 0
    for sec, total, correct in plan:
        for i in range(total):
            db.session.add(Answer(submission_id=sub.id,
                                  question_id=questions[idx].id,
                                  student_id=student.id,
                                  is_correct=i < correct))
            idx += 1

    # Soal latihan untuk menguji ketersediaan latihan (Tahap 1): satu
    # APPROVED di Bagian B, satu DRAFT di Bagian A. Hanya APPROVED yang
    # boleh dihitung - soal draf milik guru belum boleh disajikan ke siswa.
    bank_b = QuestionBank(teacher_id=teacher.id, section_id=secs[1].id,
                          question_text='Soal latihan Bagian B',
                          difficulty='medium', status='APPROVED',
                          source='teacher')
    bank_draft = QuestionBank(teacher_id=teacher.id, section_id=secs[0].id,
                              question_text='Draf Bagian A',
                              difficulty='medium', status='DRAFT',
                              source='ai')
    db.session.add_all([bank_b, bank_draft])
    db.session.commit()

    created.update(teacher=teacher, outsider=outsider, student=student,
                   course=course, material=material,
                   sec_a=secs[0], sec_b=secs[1], sec_c=secs[2], sec_d=secs[3],
                   sec_e=secs[4], quiz=quiz, sub=sub,
                   bank_b=bank_b, bank_draft=bank_draft)


def drop_fixture():
    student = created.get('student')
    if student is not None:
        Recommendation.query.filter_by(student_id=student.id).delete()
        Answer.query.filter_by(student_id=student.id).delete()
        Submission.query.filter_by(student_id=student.id).delete()
        db.session.flush()
    for key in ('bank_b', 'bank_draft'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.flush()
    for key in ('sec_a', 'sec_b', 'sec_c', 'sec_d', 'sec_e'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    if created.get('material') is not None:
        db.session.delete(created['material'])
    if created.get('quiz') is not None:
        for q in list(created['quiz'].questions):
            db.session.delete(q)
        db.session.delete(created['quiz'])
    db.session.flush()
    if created.get('course') is not None:
        Enrollment.query.filter_by(course_id=created['course'].id).delete()
        db.session.delete(created['course'])
    for key in ('teacher', 'outsider', 'student'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.commit()


def by_title(items, title):
    for s in items:
        if s['section_title'] == title:
            return s
    return {}


def main():
    app = create_app()
    with app.app_context():
        print('=' * 68)
        print('FASE 3e - REKOMENDASI PER BAGIAN')
        print('=' * 68)

        # ------------------------------------- ATURAN MURNI (tanpa DB)
        print('\n[0] ATURAN SKOR (murni, tanpa database)')
        w = dict(cfg.REC_SECTION_WEIGHTS)
        check('bobot jumlah = 1.0', abs(sum(w.values()) - 1.0) < 1e-9, str(w))
        weak = score_section({'score': 25.0, 'answered': 4, 'correct': 1}, w)
        strong = score_section({'score': 75.0, 'answered': 4, 'correct': 3}, w)
        check('bagian lemah > bagian kuat', weak > strong, f'{weak} > {strong}')
        check('skor lemah = 0.75', weak == 0.75, str(weak))
        check('skor kuat = 0.25', strong == 0.25, str(strong))
        # Error rate menaikkan prioritas pada penguasaan sama.
        more_wrong = score_section({'score': 75.0, 'answered': 4, 'correct': 0}, w)
        check('error rate menaikkan prioritas', more_wrong > strong,
              f'{more_wrong} > {strong}')
        # Tanpa jawaban tidak boleh melempar exception / tidak mengarang.
        empty = score_section({'score': None, 'answered': 0, 'correct': 0}, w)
        check('tanpa jawaban tidak crash', isinstance(empty, float), str(empty))
        check('tanpa jawaban -> 0.0 (tidak mengarang angka)', empty == 0.0,
              str(empty))
        # Skor yang hilang TIDAK boleh dibaca sebagai "tahu 0%", karena itu
        # akan memberi prioritas tertinggi justru pada bagian yang paling
        # sedikit buktinya. Hanya term error-rate yang boleh dihitung.
        blind = score_section({'score': None, 'answered': 4, 'correct': 2}, w)
        check('skor hilang tidak diANGGAP 0% (bukan prioritas maks)',
              blind == 0.2, str(blind))
        known = score_section({'score': 50.0, 'answered': 4, 'correct': 2}, w)
        check('skor 50% dengan error sama -> di atas yang skornya hilang',
              known > blind, f'{known} > {blind}')

        make_fixture()
        client = app.test_client()
        h_s = {'Authorization': f'Bearer {token_for(created["student"])}'}
        h_x = {'Authorization': f'Bearer {token_for(created["outsider"])}'}
        h_t = {'Authorization': f'Bearer {token_for(created["teacher"])}'}
        material = created['material']
        student = created['student']

        # Satu baris level-MATI RI yang dibuat manual, untuk memastikan
        # penyegaran level-materi tidak menghapus baris level-bagian.
        manual = Recommendation(student_id=student.id, material_id=material.id,
                                recommendation_score=0.5, reason_json=['manual'],
                                recommendation_type='rule', model_version=None)
        db.session.add(manual)
        db.session.commit()

        try:
            # ------------------------------------- ENDPOINT SISWA
            print('\n[1] SISWA - DAFTAR SARAN BAGIAN')
            r = client.get('/api/student/recommendations', headers=h_s)
            check('endpoint 200', r.status_code == 200, r.text[:200])
            d = r.get_json() or {}
            check('kunci section_recommendations ada',
                  'section_recommendations' in d, str(list(d.keys())))
            check('section_ranking_method = rule',
                  d.get('section_ranking_method') == 'rule',
                  str(d.get('section_ranking_method')))
            items = d.get('section_recommendations') or []
            ranked = [i for i in items if i['ranked']]
            hints = [i for i in items if not i['ranked']]

            check('tepat 2 bagian ber-skor', len(ranked) == 2,
                  str([i['section_title'] for i in ranked]))
            check('lemah (25%) ranking pertama',
                  ranked and ranked[0]['section_title'] == 'Bagian B'
                  and ranked[0]['score'] == 0.75,
                  str(ranked[0] if ranked else None))
            check('kuat (75%) ranking kedua',
                  len(ranked) > 1 and ranked[1]['section_title'] == 'Bagian A'
                  and ranked[1]['score'] == 0.25,
                  str(ranked[1] if len(ranked) > 1 else None))
            check('skor benar-benar 0..1',
                  all(0.0 <= i['score'] <= 1.0 for i in ranked))
            b_item = by_title(ranked, 'Bagian B')
            check('skor mastery ikut dibawa (25.0)',
                  b_item.get('mastery_score') == 25.0,
                  str(b_item.get('mastery_score')))
            check('status READY ikut dibawa',
                  b_item.get('status') == 'READY', str(b_item.get('status')))
            check('hitungan mentah ikut dibawa (4/1)',
                  b_item.get('answered') == 4 and b_item.get('wrong') == 3,
                  f"{b_item.get('answered')}/{b_item.get('wrong')}")
            check('judul materi ikut dibawa',
                  b_item.get('material_title') == 'Materi Uji Saran Bagian',
                  str(b_item.get('material_title')))
            reasons = ' '.join(b_item.get('reasons') or [])
            check('alasan memakai angka nyata',
                  '25%' in reasons and '3 jawaban salah dari 4' in reasons,
                  reasons)
            check('bagian terkuasai tidak disarankan',
                  by_title(items, 'Bagian E') == {},
                  str(by_title(items, 'Bagian E')))

            print('\n[1b] KETERSEDIAAN SOAL LATIHAN (Tahap 1)')
            check('Bagian B punya soal APPROVED -> latihan tersedia',
                  b_item.get('practice_available') is True
                  and b_item.get('practice_total') == 1,
                  str((b_item.get('practice_available'),
                       b_item.get('practice_total'))))
            a_item = by_title(ranked, 'Bagian A')
            check('soal DRAFT tidak dihitung sebagai latihan',
                  a_item.get('practice_available') is False
                  and a_item.get('practice_total') == 0,
                  str((a_item.get('practice_available'),
                       a_item.get('practice_total'))))
            check('setiap baris (skor & hint) membawa info latihan',
                  all('practice_available' in i and 'practice_total' in i
                      for i in items),
                  str([(i['section_title'], i.get('practice_available'),
                        i.get('practice_total')) for i in items]))

            print('\n[2] BAGIAN YANG BELUM BISA DINILAI')
            check('tepat 2 hint', len(hints) == 2,
                  str([i['section_title'] for i in hints]))
            check('hint TIDAK diberi skor',
                  all(i['score'] is None for i in hints),
                  str([i['score'] for i in hints]))
            check('hint ditandai INSUFFICIENT_DATA',
                  all(i['status'] == 'INSUFFICIENT_DATA' for i in hints),
                  str([i['status'] for i in hints]))
            check('hint mastery_score tetap None',
                  all(i['mastery_score'] is None for i in hints),
                  str([i['mastery_score'] for i in hints]))
            check('hint tetap melaporkan hitungan mentah',
                  sorted(i['answered'] for i in hints) == [0, 2],
                  str([i['answered'] for i in hints]))
            check('hint paling banyak bukti didahulukan',
                  hints and hints[0]['section_title'] == 'Bagian C',
                  str([i['section_title'] for i in hints]))
            c_hint = by_title(hints, 'Bagian C')
            check('alasan hint jujur ("belum cukup")',
                  'belum cukup' in ' '.join(c_hint.get('reasons') or []).lower(),
                  str(c_hint.get('reasons')))
            d_hint = by_title(hints, 'Bagian D')
            check('alasan hint jujur ("belum ada jawaban")',
                  'belum ada jawaban' in ' '.join(d_hint.get('reasons') or []).lower(),
                  str(d_hint.get('reasons')))

            # ------------------------------------- PERSISTENSI
            print('\n[3] PERSISTENSI & ISOLASI DUA LEVEL')
            sec_rows = Recommendation.query.filter_by(
                student_id=student.id).filter(
                Recommendation.section_id.isnot(None)).all()
            mat_rows = Recommendation.query.filter_by(
                student_id=student.id).filter(
                Recommendation.section_id.is_(None)).all()
            check('2 baris bagian tersimpan', len(sec_rows) == 2,
                  str([(r.material_id, r.section_id) for r in sec_rows]))
            check('baris materi manual utuh', len(mat_rows) == 1
                  and mat_rows[0].id == manual.id, str(len(mat_rows)))
            check('baris bagian ber-type rule tanpa model_version',
                  all(r.recommendation_type == 'rule'
                      and r.model_version is None for r in sec_rows))
            b_row = [r for r in sec_rows if r.section_id == created['sec_b'].id]
            check('baris bagian B = 0.75', bool(b_row)
                  and b_row[0].recommendation_score == 0.75,
                  str(b_row[0].recommendation_score if b_row else None))
            check('baris bagian B menyimpan alasannya',
                  bool(b_row) and isinstance(b_row[0].reason_json, list)
                  and len(b_row[0].reason_json) > 0, str(
                      b_row[0].reason_json if b_row else None))
            check('hint TIDAK pernah ditulis ke DB',
                  not any(r.section_id in (created['sec_c'].id,
                                           created['sec_d'].id)
                          for r in sec_rows),
                  str([r.section_id for r in sec_rows]))

            # Panggil sekali lagi: baris level-materi disegarkan oleh
            # _persist, baris level-bagian harus utuh.
            r2 = client.get('/api/student/recommendations', headers=h_s)
            again = Recommendation.query.filter_by(
                student_id=student.id).filter(
                Recommendation.section_id.isnot(None)).all()
            check('penyegaran materi tidak menghapus saran bagian',
                  r2.status_code == 200 and len(again) == 2,
                  str(len(again)))
            check('tidak ada baris bagian ganda setelah refresh',
                  len({(r.material_id, r.section_id) for r in again}) == 2,
                  str([(r.material_id, r.section_id) for r in again]))

            # ------------------------------- KLIK TER-SCOPE
            print('\n[4] KLIK: BAGIAN != MATERI')
            r = client.post('/api/student/recommendations/click', headers=h_s,
                            json={'material_id': material.id,
                                  'section_id': created['sec_b'].id})
            check('klik bagian 200', r.status_code == 200, r.text[:160])
            b_row = Recommendation.query.filter_by(
                student_id=student.id, section_id=created['sec_b'].id).first()
            man = Recommendation.query.get(manual.id)
            check('baris bagian B tercatat diklik', b_row.clicked_at is not None)
            check('baris materi TIDAK ikut tersentuh',
                  man.clicked_at is None, str(man.clicked_at))
            r = client.post('/api/student/recommendations/click', headers=h_s,
                            json={'material_id': material.id})
            man = Recommendation.query.get(manual.id)
            check('klik tanpa section_id menandai baris materi saja',
                  man.clicked_at is not None
                  and b_row.clicked_at is not None)
            a_row = Recommendation.query.filter_by(
                student_id=student.id, section_id=created['sec_a'].id).first()
            check('klik materi tidak menandai baris bagian lain',
                  a_row.clicked_at is None, str(a_row.clicked_at))
            r = client.post('/api/student/recommendations/click', headers=h_s,
                            json={'material_id': material.id,
                                  'section_id': 999999999})
            check('section_id tidak dikenal -> 404', r.status_code == 404,
                  str(r.status_code))
            r = client.post('/api/student/recommendations/click', headers=h_s,
                            json={'material_id': material.id,
                                  'section_id': 'bukan-angka'})
            check('section_id bukan angka -> 400', r.status_code == 400,
                  str(r.status_code))
            r = client.post('/api/student/recommendations/click', headers=h_s,
                            json={})
            check('tanpa material_id -> 400', r.status_code == 400,
                  str(r.status_code))
            r = client.post('/api/student/recommendations/click', headers=h_x,
                            json={'material_id': material.id})
            check('siswa luar kelas tidak bisa mengklik materi orang lain',
                  r.status_code == 404, str(r.status_code))

            # ------------------------------- EVALUASI & GURU
            print('\n[5] EVALUASI TERTUTUP & TAMPILAN GURU')
            r = client.get('/api/ml/evaluation/recommendations', headers=h_t)
            ev = r.get_json() or {}
            check('evaluasi hanya level-materi', ev.get('level') == 'material',
                  str(ev.get('level')))
            r = client.get('/api/teacher/analytics/ml', headers=h_t)
            ml = r.get_json() or {}
            tops = {t['material_id']: t for t in (ml.get('top_recommendations') or [])}
            ours = tops.get(material.id, {})
            check('top_recommendations guru TIDAK menghitung baris bagian',
                  ours.get('count') == 1, str(ours))

            # ------------------------------- AKSES
            print('\n[6] AKSES TER-SCOPE')
            r = client.get('/api/student/recommendations', headers=h_x)
            out = r.get_json() or {}
            check('siswa luar kelas 200 tanpa error', r.status_code == 200,
                  str(r.status_code))
            check('siswa luar kelas tidak melihat bagian materi orang lain',
                  (out.get('section_recommendations') or []) == [],
                  str(out.get('section_recommendations')))
        finally:
            drop_fixture()

        print('\n' + '=' * 68)
        passed = sum(1 for _, ok, _ in results if ok)
        failed = [(n, e) for n, ok, e in results if not ok]
        print(f'TOTAL: {len(results)}  PASS: {passed}  FAIL: {len(failed)}')
        for n, e in failed:
            print(f'  FAIL> {n} {e}')
        return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())