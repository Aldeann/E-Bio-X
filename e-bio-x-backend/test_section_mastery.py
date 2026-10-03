# ============================================================
# FASE 2 - Diagnosis penguasaan per BAGIAN materi.
#
# Tujuan fitur: jawaban salah harus bisa ditelusuri per bagian
# ("Struktur Tubuh Virus"), bukan hanya per materi. Diagnosis
# menggabungkan jawaban kuis (Answer -> Question.section_id) dan
# jawaban soal interaktif (StudentAnswer.section_id).
#
# Prinsip yang dipatok test ini:
#   - bagian dengan jawaban < ambang minimum TIDAK dikarang skornya
#     (score None, status INSUFFICIENT_DATA, hanya hitungan mentah)
#   - jawaban tanpa tag bagian TIDAK dipetakan ke bagian mana pun
#   - kuis dengan section_id eksplisit tetapi soal tanpa tag tetap
#     diatribusikan (aturan eksplisit, bukan tebakan)
#   - submission in_progress tidak ikut dihitung
#   - ringkasan kelas per bagian jujur pada ambang yang sama
#   - peta (siswa x bagian) untuk guru memakai aturan & ambang yang sama
#   - saran prasyarat (Fase 4) memakai aturan eksplisit & tidak memblokir
#   - akses materi tetap ter-scope (siswa/guru di luar kelas ditolak)
#
# Berjalan pada app + database nyata, membuat lalu menghapus fixture
# miliknya sendiri. Baris lama hanya dibaca.
# ============================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.services.learning_analytics_service import (  # noqa: E402
    _prerequisite_advisory as advisory_rule,
    PREREQUISITE_PASS_SCORE,
)
from src.models.user import User  # noqa: E402
from src.models.course import Course  # noqa: E402
from src.models.enrollment import Enrollment  # noqa: E402
from src.models.material import Material  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.material_content import MaterialContent  # noqa: E402
from src.models.quiz import Quiz  # noqa: E402
from src.models.question import Question  # noqa: E402
from src.models.answer import Answer  # noqa: E402
from src.models.submission import Submission  # noqa: E402
from src.models.student_answer import StudentAnswer  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402

STAMP = 'zzsecmaster'
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
    teacher = User(email=f'{STAMP}@test.local', name='Sec Master Guru',
                   role='teacher')
    other_teacher = User(email=f'{STAMP}.other@test.local',
                         name='Sec Master Guru Lain', role='teacher')
    student = User(email=f'{STAMP}.student@test.local', name='Sec Master Murid',
                   role='student')
    outsider = User(email=f'{STAMP}.outsider@test.local',
                    name='Sec Master Murid Luar', role='student')
    db.session.add_all([teacher, other_teacher, student, outsider])
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    db.session.add(course)
    db.session.flush()
    db.session.add(Enrollment(student_id=student.id, course_id=course.id))
    db.session.flush()

    material = Material(title='Materi Uji Bagian', course_id=course.id,
                        teacher_id=teacher.id, status='published',
                        topic='MATERI UJI BAGIAN')
    db.session.add(material)
    db.session.flush()

    sec_a = MaterialSection(material_id=material.id, title='Struktur Bagian',
                            position=0)
    sec_b = MaterialSection(material_id=material.id, title='Bagian B',
                            position=1)
    sec_c = MaterialSection(material_id=material.id, title='Bagian C',
                            position=2)
    sec_d = MaterialSection(material_id=material.id, title='Bagian D',
                            position=3)
    db.session.add_all([sec_a, sec_b, sec_c, sec_d])
    db.session.flush()

    # konten interaktif minimal untuk StudentAnswer.content_id (NOT NULL)
    content_a = MaterialContent(section_id=sec_a.id, type='question',
                                data={'difficulty': 'medium'}, position=0)
    db.session.add(content_a)
    db.session.flush()

    quiz = Quiz(title='Kuis Uji', course_id=course.id,
                material_id=material.id, created_by=teacher.id, status='draft')
    quiz_fallback = Quiz(title='Kuis Fallback', course_id=course.id,
                         material_id=material.id, created_by=teacher.id,
                         section_id=sec_c.id, status='draft')
    db.session.add_all([quiz, quiz_fallback])
    db.session.flush()

    def mkq(qz, text, sec, idx):
        return Question(quiz_id=qz.id, text=text, question_type='multiple_choice',
                        difficulty='medium', points=10, order_index=idx,
                        section_id=sec.id if sec else None)

    q_a1 = mkq(quiz, 'A1', sec_a, 0)
    q_a2 = mkq(quiz, 'A2', sec_a, 1)
    q_a3 = mkq(quiz, 'A3', sec_a, 2)
    q_b1 = mkq(quiz, 'B1', sec_b, 3)
    q_none = mkq(quiz, 'Tanpa bagian', None, 4)
    # Soal pada kuis yang section_id-nya eksplisit tetapi soal tanpa tag.
    q_c1 = mkq(quiz_fallback, 'C1 tanpa tag soal', None, 0)
    db.session.add_all([q_a1, q_a2, q_a3, q_b1, q_none, q_c1])
    db.session.flush()

    # Submission submitted: A => 3 dijawab/2 benar, B => 1 benar,
    # tanpa tag => 1 (tidak boleh terhitung ke bagian mana pun).
    sub = Submission(quiz_id=quiz.id, student_id=student.id, attempt_number=1,
                     score=60.0, percentage=60.0, correct_count=3,
                     wrong_count=1, unanswered_count=0, status='submitted')
    db.session.add(sub)
    db.session.flush()
    db.session.add_all([
        Answer(submission_id=sub.id, question_id=q_a1.id, student_id=student.id,
               is_correct=True),
        Answer(submission_id=sub.id, question_id=q_a2.id, student_id=student.id,
               is_correct=True),
        Answer(submission_id=sub.id, question_id=q_a3.id, student_id=student.id,
               is_correct=False),
        Answer(submission_id=sub.id, question_id=q_b1.id, student_id=student.id,
               is_correct=True),
        Answer(submission_id=sub.id, question_id=q_none.id, student_id=student.id,
               is_correct=True),
    ])

    # Kuis fallback: soal tanpa tag dijawab benar -> harus masuk Bagian C
    # lewat Quiz.section_id (aturan eksplisit).
    sub_fb = Submission(quiz_id=quiz_fallback.id, student_id=student.id,
                        attempt_number=1, score=100.0, percentage=100.0,
                        correct_count=1, wrong_count=0, unanswered_count=0,
                        status='submitted')
    db.session.add(sub_fb)
    db.session.flush()
    db.session.add(Answer(submission_id=sub_fb.id, question_id=q_c1.id,
                          student_id=student.id, is_correct=True))

    # Submission in_progress: TIDAK boleh dihitung.
    sub_prog = Submission(quiz_id=quiz.id, student_id=student.id,
                          attempt_number=2, status='in_progress')
    db.session.add(sub_prog)
    db.session.flush()
    db.session.add(Answer(submission_id=sub_prog.id, question_id=q_a1.id,
                          student_id=student.id, is_correct=True))

    # Jawaban interaktif: 1 benar di Bagian A -> A jadi 4 dijawab/3 benar.
    db.session.add(StudentAnswer(student_id=student.id, material_id=material.id,
                                 section_id=sec_a.id, content_id=content_a.id,
                                 selected_answer=1, is_correct=True))
    db.session.commit()

    created.update(teacher=teacher, other_teacher=other_teacher,
                   student=student, outsider=outsider, course=course,
                   material=material, sec_a=sec_a, sec_b=sec_b, sec_c=sec_c,
                   sec_d=sec_d, quiz=quiz, quiz_fallback=quiz_fallback,
                   q_a1=q_a1, q_c1=q_c1, sub=sub, sub_fb=sub_fb,
                   sub_prog=sub_prog)


def drop_fixture():
    student = created.get('student')
    if student is not None:
        Answer.query.filter_by(student_id=student.id).delete()
        StudentAnswer.query.filter_by(student_id=student.id).delete()
        Submission.query.filter_by(student_id=student.id).delete()
        db.session.flush()
    for key in ('quiz', 'quiz_fallback'):
        qz = created.get(key)
        if qz is not None:
            for q in list(qz.questions):
                db.session.delete(q)
            db.session.delete(qz)
    db.session.flush()
    for key in ('sec_a', 'sec_b', 'sec_c', 'sec_d'):
        sec = created.get(key)
        if sec is not None:
            MaterialContent.query.filter_by(section_id=sec.id).delete()
    db.session.flush()
    for key in ('sec_a', 'sec_b', 'sec_c', 'sec_d'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    if created.get('material') is not None:
        db.session.delete(created['material'])
    if created.get('course') is not None:
        Enrollment.query.filter_by(course_id=created['course'].id).delete()
        db.session.delete(created['course'])
    for key in ('teacher', 'other_teacher', 'student', 'outsider'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.commit()


def sec_by_title(sections, title):
    for s in sections:
        if s['title'] == title:
            return s
    return {}


def main():
    app = create_app()
    with app.app_context():
        print('=' * 68)
        print('FASE 2 - DIAGNOSIS PENGUASAAN PER BAGIAN')
        print('=' * 68)

        make_fixture()
        client = app.test_client()
        h_s = {'Authorization': f'Bearer {token_for(created["student"])}'}
        h_t = {'Authorization': f'Bearer {token_for(created["teacher"])}'}
        h_o = {'Authorization': f'Bearer {token_for(created["other_teacher"])}'}
        h_x = {'Authorization': f'Bearer {token_for(created["outsider"])}'}
        material = created['material']

        try:
            # ------------------------------------------- SISWA / BAGIAN
            print('\n[1] SISWA - DIAGNOSIS PER BAGIAN')
            r = client.get(f'/api/student/sections/{material.id}', headers=h_s)
            check('endpoint 200', r.status_code == 200, r.text[:200])
            d = r.get_json() or {}
            check('min_sample terlaporkan', d.get('min_sample') == 3,
                  str(d.get('min_sample')))
            check('semua bagian dilaporkan', len(d.get('sections', [])) == 4,
                  str(len(d.get('sections', []))))
            check('sections_with_data = 1', d.get('sections_with_data') == 1,
                  str(d.get('sections_with_data')))
            check('sections_insufficient = 3', d.get('sections_insufficient') == 3,
                  str(d.get('sections_insufficient')))

            a = sec_by_title(d.get('sections', []), 'Struktur Bagian')
            check('A: jumlah jawaban kuis 3', a.get('quiz_answered') == 3,
                  str(a.get('quiz_answered')))
            check('A: benar kuis 2', a.get('quiz_correct') == 2,
                  str(a.get('quiz_correct')))
            check('A: interaktif 1/1', a.get('interactive_total') == 1
                  and a.get('interactive_correct') == 1)
            check('A: total 4 dijawab 3 benar', a.get('answered') == 4
                  and a.get('correct') == 3, f"{a.get('answered')}/{a.get('correct')}")
            check('A: skor 75.0 READY', a.get('score') == 75.0
                  and a.get('status') == 'READY', str(a.get('score')))
            check('A: label mastery Baik',
                  (a.get('mastery') or {}).get('label') == 'Baik',
                  str(a.get('mastery')))

            b = sec_by_title(d.get('sections', []), 'Bagian B')
            check('B: 1 dijawab < ambang', b.get('answered') == 1)
            check('B: skor TIDAK dikarang (None)',
                  b.get('score') is None and b.get('status') == 'INSUFFICIENT_DATA',
                  str(b.get('score')))
            check('B: mastery None', b.get('mastery') is None)
            check('B: catatan menyebut ambang',
                  '3' in (b.get('note') or ''), repr(b.get('note')))

            c = sec_by_title(d.get('sections', []), 'Bagian C')
            check('C: fallback kuis-section diatribusikan',
                  c.get('quiz_answered') == 1 and c.get('answered') == 1,
                  f"{c.get('quiz_answered')}/{c.get('answered')}")
            check('C: tetap insufficient', c.get('status') == 'INSUFFICIENT_DATA')

            dd = sec_by_title(d.get('sections', []), 'Bagian D')
            check('D: bagian tanpa data tetap muncul',
                  dd.get('answered') == 0
                  and dd.get('status') == 'INSUFFICIENT_DATA')

            total_answered = sum(s.get('answered', 0) for s in d.get('sections', []))
            check('jawaban tanpa tag TIDAK dipetakan (total 6, bukan 7)',
                  total_answered == 6, str(total_answered))

            # ------------------------------------------- SARAN PRASYARAT
            print('\n[1b] SARAN PRASYARAT (advisory, tidak memblokir)')
            check('aturan prasyarat terlaporkan',
                  bool(d.get('prerequisite_rule'))
                  and d.get('prerequisite_pass_score') == PREREQUISITE_PASS_SCORE,
                  f"{d.get('prerequisite_rule')}/{d.get('prerequisite_pass_score')}")
            check('aturan: bagian pertama tanpa prasyarat & tanpa saran',
                  a.get('prerequisite_section_id') is None
                  and a.get('prerequisite_met') is True
                  and a.get('advisory') is None)
            check('aturan: prasyarat tuntas (A 75 >= 75) -> tanpa saran',
                  b.get('prerequisite_section_id') == created['sec_a'].id
                  and b.get('prerequisite_met') is True
                  and b.get('advisory') is None)
            check('aturan: prasyarat belum berskor -> tidak menegur',
                  c.get('prerequisite_met') is None and c.get('advisory') is None)
            check('aturan: advisory_count 0 pada fixture ini',
                  d.get('advisory_count') == 0, str(d.get('advisory_count')))
            met, adv = advisory_rule({'status': 'READY', 'score': 50.0, 'title': 'X'})
            check('aturan: READY < ambang -> met False + saran',
                  met is False and bool(adv) and 'X' in adv, f'{met}/{adv}')
            met, adv = advisory_rule({'status': 'INSUFFICIENT_DATA', 'score': None,
                                      'title': 'X'})
            check('aturan: INSUFFICIENT_DATA -> None + tanpa saran',
                  met is None and adv is None, f'{met}/{adv}')
            met, adv = advisory_rule(None)
            check('aturan: tanpa bagian sebelumnya -> True + tanpa saran',
                  met is True and adv is None, f'{met}/{adv}')

            # ------------------------------------------- DETAIL PROGRES
            print('\n[2] SISWA - DETAIL PROGRES IKUT JUJUR')
            r = client.get(f'/api/student/progress/{material.id}', headers=h_s)
            check('detail 200', r.status_code == 200, r.text[:200])
            det = r.get_json() or {}
            check('detail: mastery_status READY', det.get('mastery_status') == 'READY',
                  str(det.get('mastery_status')))
            check('detail: mastery_score 75.0', det.get('mastery_score') == 75.0,
                  str(det.get('mastery_score')))
            check('detail: section_mastery memuat min_sample',
                  (det.get('section_mastery') or {}).get('min_sample') == 3)
            mr_a = next((m for m in det.get('mastery_rows', [])
                         if m.get('title') == 'Struktur Bagian'), {})
            mr_b = next((m for m in det.get('mastery_rows', [])
                         if m.get('title') == 'Bagian B'), {})
            check('detail: baris A punya skor',
                  mr_a.get('score') == 75.0
                  and (mr_a.get('mastery') or {}).get('label') == 'Baik')
            check('detail: baris B jujur (score None)',
                  mr_b.get('score') is None and mr_b.get('status') == 'INSUFFICIENT_DATA',
                  str(mr_b.get('score')))
            sec_row_a = next((m for m in det.get('sections', [])
                              if m.get('title') == 'Struktur Bagian'), {})
            check('detail: baris bagian punya hitungan kuis',
                  sec_row_a.get('quiz_answered') == 3
                  and sec_row_a.get('interactive_total') == 1)
            sec_row_b = next((m for m in det.get('sections', [])
                              if m.get('title') == 'Bagian B'), {})
            check('detail: baris bagian membawa kunci advisory',
                  'advisory' in sec_row_b and sec_row_b.get('advisory') is None,
                  str(sec_row_b.get('advisory')))

            # ------------------------------------------- GURU / KELAS
            print('\n[3] GURU - RINGKASAN KELAS PER BAGIAN')
            r = client.get(f'/api/teacher/analytics/materials/{material.id}',
                           headers=h_t)
            check('material analytics 200', r.status_code == 200, r.text[:200])
            ma = r.get_json() or {}
            smk = ma.get('section_mastery') or {}
            check('section_mastery terlaporkan', bool(smk), str(list(ma.keys())))
            check('kelas: total_students 1', smk.get('total_students') == 1,
                  str(smk.get('total_students')))
            ca = sec_by_title(smk.get('sections', []), 'Struktur Bagian')
            cb = sec_by_title(smk.get('sections', []), 'Bagian B')
            check('kelas A: READY skor 75.0', ca.get('score') == 75.0
                  and ca.get('status') == 'READY', str(ca.get('score')))
            check('kelas A: coverage 1/1', ca.get('students_answered') == 1
                  and ca.get('total_students') == 1)
            check('kelas B: jujur insufficient', cb.get('score') is None
                  and cb.get('status') == 'INSUFFICIENT_DATA')

            # ------------------------------------------- GURU / GRID
            print('\n[3b] GURU - PETA (SISWA x BAGIAN)')
            mx = ma.get('section_matrix') or {}
            check('section_matrix terlaporkan', bool(mx), str(list(ma.keys())))
            check('grid: 4 bagian + min_sample 3',
                  len(mx.get('sections', [])) == 4 and mx.get('min_sample') == 3,
                  f"{len(mx.get('sections', []))}/{mx.get('min_sample')}")
            check('grid: 1 siswa berbukti dari 1 siswa',
                  mx.get('students_with_data') == 1
                  and mx.get('total_students') == 1,
                  f"{mx.get('students_with_data')}/{mx.get('total_students')}")
            gs = (mx.get('students') or [{}])[0]
            check('grid: baris hanya siswa kelas ini',
                  gs.get('student_id') == created['student'].id,
                  str(gs.get('student_id')))
            cells = gs.get('cells') or {}
            ga = cells.get(str(created['sec_a'].id), {})
            gb = cells.get(str(created['sec_b'].id), {})
            gd = cells.get(str(created['sec_d'].id), {})
            check('grid A: sama dengan per-siswa (READY 75.0)',
                  ga.get('score') == 75.0 and ga.get('status') == 'READY',
                  str(ga.get('score')))
            check('grid B: mentah 1, insufficient',
                  gb.get('answered') == 1
                  and gb.get('status') == 'INSUFFICIENT_DATA',
                  f"{gb.get('answered')}/{gb.get('status')}")
            check('grid D: tanpa bukti NO_DATA',
                  gd.get('status') == 'NO_DATA' and gd.get('answered') == 0,
                  str(gd.get('status')))

            # ------------------------------------------- AKSES
            print('\n[4] AKSES TER-SCOPE')
            r = client.get(f'/api/student/sections/{material.id}', headers=h_x)
            check('siswa luar kelas ditolak (403)', r.status_code == 403,
                  str(r.status_code))
            r = client.get(f'/api/teacher/analytics/materials/{material.id}',
                           headers=h_o)
            check('guru lain ditolak dari analytics materi (403)',
                  r.status_code == 403, str(r.status_code))

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
