# ============================================================
# FASE 3f - ANALISIS TINGKAT SOAL OTOMATIS + LATIHAN ADAPTIF
#
# Kontrak yang dipatok test ini:
#
#   UNIT (murni, tanpa database):
#     - classify: batas 0.70/0.40 persis; p di bawah ambang 20 siswa ->
#       INSUFFICIENT_DATA, TIDAK ada label yang diklaim
#     - margin 95% dan penanda "dekat batas" (rentang memotong garis)
#     - aggregate_rows: satu siswa dihitung SEKALI memakai jawaban PERTAMA;
#       leave-one-out membuang jawaban siswa yang dinilai sebelum ambang dicek
#     - observed_note menyebut n, %, margin - tidak menyebut tingkat
#
#   INTEGRASI (app + DB nyata, fixture milik sendiri, dihapus lagi):
#     - endpoint guru /api/teacher/practice/difficulty: 403 untuk siswa,
#       200 untuk guru, hanya soal bank (kanal interaktif dihapus),
#       soal ber-n<20 -> INSUFFICIENT_DATA (bukan 'sedang')
#     - soal siswa menyertakan difficulty (terukur bila ada) + declared_difficulty
#       + difficulty_basis; label guru tidak pernah ditimpa diam-diam
#     - sesi adaptif: sasaran = tingkat terlemah siswa, soal sasaran disajikan
#       lebih dulu; basis 'observed' bila terukur, 'declared' bila hanya deklarasi
# ============================================================
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.user import User  # noqa: E402
from src.models.course import Course  # noqa: E402
from src.models.enrollment import Enrollment  # noqa: E402
from src.models.material import Material  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.question_bank import QuestionBank  # noqa: E402
from src.models.question_bank_option import QuestionBankOption  # noqa: E402
from src.models.practice_answer import PracticeAnswer  # noqa: E402
from src.ml import ml_config as cfg  # noqa: E402
from src.services import question_difficulty_service as qds  # noqa: E402
from src.services import student_practice_service as sp  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402

STAMP = 'zzdifficulty'
results = []
created = {}


def check(name, cond, extra=""):
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


def token_for(user):
    return create_access_token(identity=str(user.id))


# ============================================================
# UNIT - murni, tanpa DB
# ============================================================
class _Row:
    """Baris jawaban minimal untuk aggregate_rows (tanpa question_index)."""

    def __init__(self, student_id, slot, correct, order=0, answered_at=None):
        self.student_id = student_id
        self.bank_question_id = slot
        self.is_correct = correct
        self.id = order
        self.answered_at = answered_at or datetime(2024, 1, 1)


def run_unit_tests():
    print('\n[U1] classify: ambang sampel minimum')
    check('n=19 < 20 -> INSUFFICIENT_DATA, tanpa label',
          qds.classify(19, 19)['status'] == 'INSUFFICIENT_DATA'
          and qds.classify(19, 19)['label'] is None)
    check('n=20 tepat -> sudah READY',
          qds.classify(20, 20)['status'] == 'READY')
    check('n=21 -> sudah READY (bukan menunggu kelas penuh)',
          qds.classify(21, 21)['status'] == 'READY')
    check('n=0 -> INSUFFICIENT_DATA',
          qds.classify(0, 0)['status'] == 'INSUFFICIENT_DATA')

    print('\n[U2] classify: batas 0.70 dan 0.40 persis')
    check('p=0.70 -> mudah (batas atas inklusif)',
          qds.classify(100, 70)['label'] == 'easy',
          f"got {qds.classify(100, 70)['label']}")
    check('p=0.69 -> sedang',
          qds.classify(100, 69)['label'] == 'medium',
          f"got {qds.classify(100, 69)['label']}")
    check('p=0.40 -> sedang (batas bawah inklusif)',
          qds.classify(100, 40)['label'] == 'medium',
          f"got {qds.classify(100, 40)['label']}")
    check('p=0.39 -> sulit',
          qds.classify(100, 39)['label'] == 'hard',
          f"got {qds.classify(100, 39)['label']}")

    print('\n[U3] margin 95% + penanda dekat batas')
    m = qds.margin(0.70, 100)
    check('margin(0.70, 100) ~ 0.0898',
          abs(m - 0.0898) < 0.001, f'got {m}')
    check('margin n kecil lebih lebar (keterbatasan jujur)',
          qds.margin(0.70, 20) > qds.margin(0.70, 63))
    check('p=0.70 n=20 -> dekat batas (rentang memotong 0.70)',
          qds.classify(20, 14)['near_boundary'] is True)
    check('p=0.90 n=100 -> tidak dekat batas',
          qds.classify(100, 90)['near_boundary'] is False)
    check('p=0.35 n=100 -> dekat batas (memotong 0.40)',
          qds.classify(100, 35)['near_boundary'] is True)

    print('\n[U4] aggregate_rows: sekali per siswa, jawaban PERTAMA')
    t1 = datetime(2024, 1, 1, 9, 0, 0)
    t2 = datetime(2024, 1, 1, 9, 5, 0)
    rows = [_Row(1, 5, False, order=1, answered_at=t1),
            _Row(1, 5, True, order=2, answered_at=t2)]
    res = qds.aggregate_rows(rows, min_sample=1)
    got = res.get(5, {})
    check('satu siswa dua jawaban dihitung sekali', got.get('n') == 1,
          f'n={got.get("n")}')
    check('yang dipakai jawaban PERTAMA (salah)', got.get('correct') == 0,
          f'correct={got.get("correct")}')

    print('\n[U5] aggregate_rows: leave-one-out sebelum ambang dicek')
    rows = [_Row(1, 5, True), _Row(2, 5, False), _Row(3, 5, True)]
    with_excl = qds.aggregate_rows(rows, exclude_student_id=2, min_sample=2)
    without = qds.aggregate_rows(rows, min_sample=2)
    check('LOO membuang jawaban siswa ybs (n=2)',
          with_excl[5]['n'] == 2, f'n={with_excl[5]["n"]}')
    check('tanpa LOO n=3', without[5]['n'] == 3, f'n={without[5]["n"]}')
    check('LOO bisa mengubah label (2/2 mudah vs 2/3 sedang)',
          with_excl[5]['label'] == 'easy' and without[5]['label'] == 'medium',
          f'{with_excl[5]["label"]} vs {without[5]["label"]}')
    check('LOO di bawah ambang -> INSUFFICIENT_DATA',
          qds.aggregate_rows([_Row(1, 5, True), _Row(2, 5, True)],
                             exclude_student_id=1, min_sample=2)[5]['status']
          == 'INSUFFICIENT_DATA')

    print('\n[U6] observed_note')
    # interactive_slot_key dihapus: kanal soal interaktif sudah tidak ada.

    ready = qds.classify(63, 46)          # p=0.73, dekat batas
    note = qds.observed_note(ready)
    check('observed_note menyebut n dan persen',
          '63 siswa menjawab' in note and '73% benar' in note, f'got {note}')
    check('observed_note menyebut margin', '±' in note, f'got {note}')
    check('observed_note menandai dekat batas',
          'dekat batas' in note, f'got {note}')
    check('observed_note TIDAK menyebut nama tingkat',
          'mudah' not in note and 'sedang' not in note and 'sulit' not in note,
          f'got {note}')
    check('observed_note None saat belum cukup bukti',
          qds.observed_note(qds.classify(3, 1)) is None)

    print('\n[U7] empty_observed: tidak menebak tingkat')
    empty = qds.empty_observed(5)
    check('empty -> INSUFFICIENT_DATA', empty['status'] == 'INSUFFICIENT_DATA')
    check('empty -> label None (bukan sedang)', empty['label'] is None)
    check('konstanta ambang sesuai keputusan',
          cfg.MIN_DIFFICULTY_SAMPLE == 20
          and cfg.DIFFICULTY_P_EASY == 0.70
          and cfg.DIFFICULTY_P_HARD == 0.40)


# ============================================================
# INTEGRASI - fixture milik sendiri
# ============================================================
def add_bank(teacher, section, text, difficulty, status='APPROVED'):
    bq = QuestionBank(
        teacher_id=teacher.id, question_text=text,
        question_type='multiple_choice', section_id=section.id,
        topic=section.title, difficulty=difficulty, explanation='Pembahasan.',
        points=10, misconception=None, source='teacher', status=status)
    db.session.add(bq)
    db.session.flush()
    db.session.add_all([
        QuestionBankOption(bank_question_id=bq.id, option_text=f'Benar {bq.id}',
                           is_correct=True, order_index=0),
        QuestionBankOption(bank_question_id=bq.id, option_text=f'Salah {bq.id}',
                           is_correct=False, order_index=1),
    ])
    db.session.flush()
    return bq


def make_fixture():
    teacher = User(email=f'{STAMP}@test.local', name='Guru Analisis Tingkat',
                   role='teacher')
    student = User(email=f'{STAMP}.student@test.local',
                   name='Siswa Sasaran', role='student')
    declared_student = User(email=f'{STAMP}.declared@test.local',
                            name='Siswa Deklarasi', role='student')
    outsider = User(email=f'{STAMP}.outsider@test.local',
                    name='Siswa Luar', role='student')
    db.session.add_all([teacher, student, declared_student, outsider])
    db.session.flush()

    # 21 siswa kohort untuk mengukur dua soal bank (>= ambang 20).
    cohort = []
    for i in range(21):
        u = User(email=f'{STAMP}.cohort{i}@test.local',
                 name=f'Kohort {i}', role='student')
        cohort.append(u)
    db.session.add_all(cohort)
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    db.session.add(course)
    db.session.flush()
    for u in [student, declared_student] + cohort:
        db.session.add(Enrollment(student_id=u.id, course_id=course.id))

    material = Material(title='Materi Analisis Tingkat', course_id=course.id,
                        teacher_id=teacher.id, status='published', topic='UJI')
    db.session.add(material)
    db.session.flush()

    sec_measured = MaterialSection(material_id=material.id, title='Bagian Terukur',
                                   position=0)
    sec_declared = MaterialSection(material_id=material.id, title='Bagian Deklarasi',
                                   position=1)
    db.session.add_all([sec_measured, sec_declared])
    db.session.flush()

    # Soal berlabel guru 'medium'/'sulit', tapi hasil ukur nanti berbeda.
    bq_easy = add_bank(teacher, sec_measured, 'Soal terukur mudah', 'medium')
    bq_hard = add_bank(teacher, sec_measured, 'Soal terukur sulit', 'medium')
    bq_declared = add_bank(teacher, sec_declared, 'Soal hanya deklarasi', 'sulit')

    created.update(
        teacher=teacher, student=student, declared_student=declared_student,
        outsider=outsider, cohort=cohort, course=course, material=material,
        sec_measured=sec_measured, sec_declared=sec_declared,
        bq_easy=bq_easy, bq_hard=bq_hard, bq_declared=bq_declared,
        banks=[bq_easy, bq_hard, bq_declared],
    )

    # Kohort mengukur bq_easy -> mudah (18/21 benar), bq_hard -> sulit (3/21).
    base = datetime(2024, 2, 1, 8, 0, 0)
    for i, u in enumerate(cohort):
        db.session.add(PracticeAnswer(
            student_id=u.id, material_id=material.id, section_id=sec_measured.id,
            bank_question_id=bq_easy.id, selected_option=0,
            is_correct=(i < 18), attempt_no=1, question_snapshot='q',
            answered_at=base + timedelta(seconds=i)))
        db.session.add(PracticeAnswer(
            student_id=u.id, material_id=material.id, section_id=sec_measured.id,
            bank_question_id=bq_hard.id, selected_option=0,
            is_correct=(i < 3), attempt_no=1, question_snapshot='q',
            answered_at=base + timedelta(seconds=i)))

    # Siswa sasaran: benar di soal mudah, salah di soal sulit -> sasaran = sulit.
    db.session.add(PracticeAnswer(
        student_id=student.id, material_id=material.id, section_id=sec_measured.id,
        bank_question_id=bq_easy.id, selected_option=0, is_correct=True,
        attempt_no=1, question_snapshot='q', answered_at=base + timedelta(minutes=5)))
    db.session.add(PracticeAnswer(
        student_id=student.id, material_id=material.id, section_id=sec_measured.id,
        bank_question_id=bq_hard.id, selected_option=0, is_correct=False,
        attempt_no=1, question_snapshot='q', answered_at=base + timedelta(minutes=6)))

    # Siswa deklarasi: hanya menjawab soal yang belum terukur (salah).
    db.session.add(PracticeAnswer(
        student_id=declared_student.id, material_id=material.id,
        section_id=sec_declared.id, bank_question_id=bq_declared.id,
        selected_option=0, is_correct=False, attempt_no=1,
        question_snapshot='q', answered_at=base + timedelta(minutes=7)))

    db.session.commit()


def drop_fixture():
    bank_ids = [b.id for b in created.get('banks', [])]
    if bank_ids:
        PracticeAnswer.query.filter(
            PracticeAnswer.bank_question_id.in_(bank_ids)).delete(
            synchronize_session=False)
        QuestionBankOption.query.filter(
            QuestionBankOption.bank_question_id.in_(bank_ids)).delete(
            synchronize_session=False)
    db.session.flush()
    for bq in created.get('banks', []):
        db.session.delete(bq)
    db.session.flush()
    for key in ('sec_measured', 'sec_declared'):
        db.session.delete(created[key])
    db.session.delete(created['material'])
    db.session.flush()
    for key in ('student', 'declared_student'):
        db.session.query(Enrollment).filter_by(
            student_id=created[key].id).delete(synchronize_session=False)
    for u in created.get('cohort', []):
        db.session.query(Enrollment).filter_by(
            student_id=u.id).delete(synchronize_session=False)
    db.session.flush()
    db.session.delete(created['course'])
    for key in ('teacher', 'student', 'declared_student', 'outsider'):
        db.session.delete(created[key])
    for u in created.get('cohort', []):
        db.session.delete(u)
    db.session.commit()


def run_integration_tests(app):
    make_fixture()
    client = app.test_client()
    teacher = created['teacher']
    student = created['student']
    declared_student = created['declared_student']
    material = created['material']

    h_t = {'Authorization': f'Bearer {token_for(teacher)}'}
    h_s = {'Authorization': f'Bearer {token_for(student)}'}
    h_d = {'Authorization': f'Bearer {token_for(declared_student)}'}
    h_out = {'Authorization': f'Bearer {token_for(created["outsider"])}'}

    try:
        # ------------------------------------------------ 1. ENDPOINT GURU
        print('\n[I1] endpoint guru: hak akses')
        r = client.get('/api/teacher/practice/difficulty', headers=h_s)
        check('siswa ditolak 403', r.status_code == 403, f'status={r.status_code}')
        r = client.get('/api/teacher/practice/difficulty', headers=h_out)
        check('non-guru ditolak 403', r.status_code == 403)

        r = client.get('/api/teacher/practice/difficulty', headers=h_t)
        body = r.get_json()
        check('guru dapat 200', r.status_code == 200, f'status={r.status_code}')
        check('respons punya items/counts/rules',
              all(k in body for k in ('items', 'counts', 'rules')))
        check('aturan menyebut ambang 20 dan batas 0.70/0.40',
              body['rules']['min_sample'] == 20
              and body['rules']['p_easy'] == 0.70
              and body['rules']['p_hard'] == 0.40)

        items = {it.get('question_id'): it for it in body['items']
                 if it['kind'] == 'bank'}
        easy_it = items.get(created['bq_easy'].id, {})
        hard_it = items.get(created['bq_hard'].id, {})
        decl_it = items.get(created['bq_declared'].id, {})

        print('\n[I2] dua sumber berdampingan (deklarasi vs terukur)')
        check('soal terukur mudah: observed READY easy',
              easy_it.get('observed', {}).get('status') == 'READY'
              and easy_it['observed']['label'] == 'easy',
              f'got {easy_it.get("observed")}')
        check('soal terukur sulit: observed READY hard',
              hard_it.get('observed', {}).get('status') == 'READY'
              and hard_it['observed']['label'] == 'hard',
              f'got {hard_it.get("observed")}')
        check('label guru tetap terlihat (tidak ditimpa)',
              easy_it.get('declared_label') == 'sedang',
              f'got {easy_it.get("declared_label")}')
        check('soal kurang data: INSUFFICIENT_DATA, bukan sedang',
              decl_it.get('observed', {}).get('status') == 'INSUFFICIENT_DATA'
              and decl_it['observed']['label'] is None,
              f'got {decl_it.get("observed")}')
        check('deklarasi soal kurang data tetap "sulit"',
              decl_it.get('declared_label') == 'sulit',
              f'got {decl_it.get("declared_label")}')
        check('catatan sumber n/p ikut dikirim',
              'siswa menjawab' in (easy_it.get('observed_note') or '')
              and 'benar' in (easy_it.get('observed_note') or ''),
              f'got {easy_it.get("observed_note")}')
        check('counts melaporkan berapa yang siap diukur',
              body['counts'].get('observed_ready', 0) >= 2
              and body['counts'].get('total', 0) >= 3,
              f'got {body["counts"]}')

        # --------------------------------------------- 2. PAYLOAD SOAL SISWA
        print('\n[I3] soal siswa: tingkat terukur + deklarasi terpisah')
        r = client.get(
            f'/api/student/practice/{material.id}/sections/{created["sec_measured"].id}',
            headers=h_s)
        body = r.get_json()
        check('pemuatan soal 200', r.status_code == 200, f'status={r.status_code}')
        check('respons menyertakan deskripsi sesi', 'session' in body)
        q_by_id = {q['id']: q for q in body['questions']}
        q_easy = q_by_id.get(created['bq_easy'].id, {})
        check('soal mudah: difficulty terukur = easy',
              q_easy.get('difficulty') == 'easy',
              f'got {q_easy.get("difficulty")}')
        check('soal mudah: declared_difficulty tetap medium',
              q_easy.get('declared_difficulty') == 'medium',
              f'got {q_easy.get("declared_difficulty")}')
        check('soal mudah: difficulty_basis = observed',
              q_easy.get('difficulty_basis') == 'observed',
              f'got {q_easy.get("difficulty_basis")}')
        check('semua soal punya declared_difficulty + basis',
              all('declared_difficulty' in q and 'difficulty_basis' in q
                  for q in body['questions']))
        check('kunci jawaban tetap tidak bocor',
              'is_correct' not in str(body))

        # ------------------------------------------------- 3. SESI ADAPTIF
        print('\n[I4] sesi adaptif: sasaran tingkat terlemah')
        session = body['session']
        check('basis sesi = observed (tingkat terukur dari performa)',
              session.get('basis') == 'observed', f'got {session.get("basis")}')
        check('sasaran = sulit (satu-satunya level yang salah)',
              session.get('target_level') == 'hard',
              f'got {session.get("target_level")}')
        check('akurasi sasaran 0% (dijawab salah)',
              session.get('target_accuracy') == 0.0,
              f'got {session.get("target_accuracy")}')
        ids = [q['id'] for q in body['questions']]
        check('soal sasaran disajikan lebih dulu',
              ids and ids[0] == created['bq_hard'].id, f'order={ids}')
        check('komposisi 60/30/10 dilaporkan',
              session.get('mix', {}).get('target') == 1
              and session.get('mix', {}).get('below') == 1,
              f'got {session.get("mix")}')
        check('basis_text menyebut n latihan + interaktif',
              'jawabanmu' in (session.get('basis_text') or '')
              and 'latihan' in (session.get('basis_text') or ''),
              f'got {session.get("basis_text")}')

        print('\n[I5] sesi adaptif: basis deklarasi bila belum terukur')
        r = client.get(
            f'/api/student/practice/{material.id}/sections/{created["sec_declared"].id}',
            headers=h_d)
        body_d = r.get_json()
        sess_d = body_d['session']
        check('basis sesi = declared (belum cukup data performa)',
              sess_d.get('basis') == 'declared', f'got {sess_d.get("basis")}')
        check('sasaran = sulit dari label guru',
              sess_d.get('target_level') == 'hard',
              f'got {sess_d.get("target_level")}')
        qd_ = body_d['questions'][0]
        check('soal tetap disajikan walau belum terukur',
              qd_.get('difficulty') == 'hard'
              and qd_.get('difficulty_basis') == 'declared',
              f'got {qd_.get("difficulty")}/{qd_.get("difficulty_basis")}')

        print('\n[I6] siswa tanpa jawaban -> sesi berurutan, bukan mengarang')
        # siswa luar tidak boleh masuk; pakai siswa kohort (tanpa jawaban
        # latihan? kohort punya) -> pakai outsider? 403. Buat cek via service.
        no_answers = User(email=f'{STAMP}.blank@test.local', name='Siswa Kosong',
                          role='student')
        db.session.add(no_answers)
        db.session.flush()
        db.session.add(Enrollment(student_id=no_answers.id, course_id=created['course'].id))
        db.session.commit()
        entries, sess = sp.session_for_section(
            material.id, created['sec_measured'].id, no_answers)
        check('basis = sequential tanpa riwayat jawaban',
              sess.get('basis') == 'sequential', f'got {sess.get("basis")}')
        check('target_level None (tidak mengarang sasaran)',
              sess.get('target_level') is None)
        check('semua soal APPROVED tetap disajikan berurutan',
              [e['bq'].id for e in entries]
              == sorted(e['bq'].id for e in entries))
        # bersihkan siswa kosong
        db.session.query(Enrollment).filter_by(student_id=no_answers.id).delete(
            synchronize_session=False)
        db.session.delete(no_answers)
        db.session.commit()
    finally:
        db.session.rollback()
        drop_fixture()


def main():
    print('=' * 68)
    print('FASE 3f - ANALISIS TINGKAT SOAL OTOMATIS + LATIHAN ADAPTIF')
    print('=' * 68)
    run_unit_tests()
    app = create_app()
    with app.app_context():
        run_integration_tests(app)

    print('\n' + '=' * 68)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = [r for r in results if not r[1]]
    print(f'TOTAL {len(results)} check | PASS {passed} | FAIL {len(failed)}')
    for name, _ok, extra in failed:
        print(f'  FAIL: {name} {extra}')
    print('=' * 68)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
