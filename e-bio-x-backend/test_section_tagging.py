# ============================================================
# FASE 1 - Penandaan bagian (section) pada soal kuis.
#
# Tujuan fitur: jawaban salah harus bisa ditelusuri per BAGIAN materi
# ("Struktur Tubuh Virus"), bukan hanya per materi. Itu butuh soal
# menyimpan `section_id`.
#
# Yang dipatok test ini:
#   - kolom questions.section_id ada, boleh kosong
#   - tambah soal mewarisi bagian kuis, atau menerima bagian eksplisit
#   - bagian milik materi lain DITOLAK (tidak boleh salah tag)
#   - ubah soal bisa mengganti / menghapus tag, dan mempertahankannya
#     bila payload tidak menyertakan section_id
#   - duplikat menyalin tag
#   - aksi massal "terapkan bagian kuis ke semua soal"
#   - soal bank dipetakan hanya bila topiknya PERSIS sama dengan judul
#     bagian (tidak mengarang)
#   - fungsi backfill berperilaku sama
#   - guru lain tidak bisa menyentuh kuis ini
#
# Berjalan pada app + database nyata, membuat lalu menghapus fixture
# miliknya sendiri. Baris lama hanya dibaca.
# ============================================================
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.user import User  # noqa: E402
from src.models.course import Course  # noqa: E402
from src.models.material import Material  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.quiz import Quiz  # noqa: E402
from src.models.question import Question  # noqa: E402
from src.models.question_bank import QuestionBank  # noqa: E402
from src.models.question_bank_option import QuestionBankOption  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

STAMP = 'zzsectionunit'
results = []
created = {}


def check(name, cond, extra=""):
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


def _load_backfill():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'scripts', 'backfill_question_sections.py')
    spec = importlib.util.spec_from_file_location('backfill_qs', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def token_for(user):
    return create_access_token(identity=str(user.id))


def mcq_body(text='Soal uji', options=None, **extra):
    opts = options or [
        {'option_text': 'A', 'is_correct': True},
        {'option_text': 'B', 'is_correct': False},
    ]
    body = {
        'question_type': 'multiple_choice',
        'question_text': text,
        'difficulty': 'medium',
        'explanation': 'pembahasan',
        'points': 10,
        'options': opts,
    }
    body.update(extra)
    return body


def make_fixture():
    teacher = User(email=f'{STAMP}@test.local', name='Section Unit Guru',
                   role='teacher')
    other_teacher = User(email=f'{STAMP}.other@test.local',
                         name='Section Unit Guru Lain', role='teacher')
    db.session.add_all([teacher, other_teacher])
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    db.session.add(course)
    db.session.flush()

    material = Material(title='Materi Uji', course_id=course.id,
                        teacher_id=teacher.id, status='published',
                        topic='MATERI UJI')
    other_material = Material(title='Materi Lain', course_id=course.id,
                              teacher_id=teacher.id, status='published')
    single_material = Material(title='Materi Satu Bagian',
                               course_id=course.id, teacher_id=teacher.id,
                               status='published')
    db.session.add_all([material, other_material, single_material])
    db.session.flush()

    sec_a = MaterialSection(material_id=material.id, title='Bagian A',
                            position=0)
    sec_b = MaterialSection(material_id=material.id, title='Bagian B',
                            position=1)
    sec_other = MaterialSection(material_id=other_material.id,
                                title='Bagian Materi Lain', position=0)
    sec_single = MaterialSection(material_id=single_material.id,
                                 title='Satu-satunya Bagian', position=0)
    db.session.add_all([sec_a, sec_b, sec_other, sec_single])
    db.session.flush()

    quiz = Quiz(title='Kuis Uji A', course_id=course.id,
                material_id=material.id, created_by=teacher.id,
                section_id=sec_a.id, status='draft')
    quiz_plain = Quiz(title='Kuis Uji B', course_id=course.id,
                      material_id=material.id, created_by=teacher.id,
                      status='draft')
    quiz_single = Quiz(title='Kuis Uji C', course_id=course.id,
                       material_id=single_material.id,
                       created_by=teacher.id, status='draft')
    db.session.add_all([quiz, quiz_plain, quiz_single])
    db.session.flush()

    bank = QuestionBank(teacher_id=teacher.id, question_text='Bank soal A',
                        question_type='multiple_choice', topic='Bagian B',
                        difficulty='medium', points=10)
    db.session.add(bank)
    db.session.flush()
    db.session.add_all([
        QuestionBankOption(bank_question_id=bank.id, option_text='X',
                           is_correct=True, order_index=0),
        QuestionBankOption(bank_question_id=bank.id, option_text='Y',
                           is_correct=False, order_index=1),
    ])
    db.session.commit()

    created.update(teacher=teacher, other_teacher=other_teacher,
                   course=course, material=material,
                   other_material=other_material,
                   single_material=single_material,
                   sec_a=sec_a, sec_b=sec_b, sec_other=sec_other,
                   sec_single=sec_single, quiz=quiz, quiz_plain=quiz_plain,
                   quiz_single=quiz_single, bank=bank)


def drop_fixture():
    for quiz in (created.get('quiz'), created.get('quiz_plain'),
                 created.get('quiz_single')):
        if quiz is not None:
            for q in list(quiz.questions):
                db.session.delete(q)
            db.session.delete(quiz)
    db.session.flush()
    for key in ('bank', 'bank2', 'bank3'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    for key in ('sec_a', 'sec_b', 'sec_other', 'sec_single'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    for key in ('material', 'other_material', 'single_material'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    if created.get('course') is not None:
        db.session.delete(created['course'])
    for key in ('teacher', 'other_teacher'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        print('=' * 68)
        print('FASE 1 - TAG BAGIAN PADA SOAL')
        print('=' * 68)

        make_fixture()
        client = app.test_client()
        h_t = {'Authorization': f'Bearer {token_for(created["teacher"])}'}
        h_o = {'Authorization': f'Bearer {token_for(created["other_teacher"])}'}
        quiz = created['quiz']
        quiz_plain = created['quiz_plain']
        sec_a = created['sec_a']
        sec_b = created['sec_b']
        sec_other = created['sec_other']
        sec_single = created['sec_single']
        backfill = _load_backfill()

        try:
            # ------------------------------------------------- SKEMA
            print('\n[1] SKEMA')
            cols = {c['name']: c for c in
                    inspect(db.engine).get_columns('questions')}
            check('kolom questions.section_id ada', 'section_id' in cols,
                  ', '.join(sorted(cols)))
            check('questions.section_id boleh kosong',
                  cols.get('section_id', {}).get('nullable') is True)
            check('relasi Question.section tersedia',
                  hasattr(Question, 'section'))
            check('relasi MaterialSection.questions tersedia',
                  hasattr(MaterialSection, 'questions'))

            # ------------------------------------------- TAMBAH SOAL
            print('\n[2] TAMBAH SOAL')
            r = client.post(f'/api/teacher/quizzes/{quiz.id}/questions',
                            json=mcq_body('Soal mewarisi'), headers=h_t)
            data = r.get_json() or {}
            q_default = data.get('question', {})
            check('soal baru mewarisi bagian kuis (default)',
                  r.status_code == 201
                  and q_default.get('section_id') == sec_a.id,
                  f"status={r.status_code} section={q_default.get('section_id')}")
            check('respons memuat section_id & section_title',
                  q_default.get('section_title') == 'Bagian A',
                  repr(q_default.get('section_title')))
            qid_default = q_default.get('question_id')
            row = Question.query.get(qid_default)
            check('tersimpan di database',
                  row is not None and row.section_id == sec_a.id)

            r = client.post(f'/api/teacher/quizzes/{quiz.id}/questions',
                            json=mcq_body('Soal eksplisit',
                                          section_id=sec_b.id), headers=h_t)
            q_exp = (r.get_json() or {}).get('question', {})
            check('soal dengan section_id eksplisit disimpan',
                  r.status_code == 201 and q_exp.get('section_id') == sec_b.id,
                  f"status={r.status_code} section={q_exp.get('section_id')}")

            r = client.post(f'/api/teacher/quizzes/{quiz.id}/questions',
                            json=mcq_body('Soal materi lain',
                                          section_id=sec_other.id), headers=h_t)
            check('bagian dari materi lain DITOLAK (400)',
                  r.status_code == 400, f"status={r.status_code}")

            r = client.post(f'/api/teacher/quizzes/{quiz.id}/questions',
                            json=mcq_body('Soal section ngawur',
                                          section_id='abc'), headers=h_t)
            check('section_id tidak valid ditolak (400)',
                  r.status_code == 400, f"status={r.status_code}")

            r = client.post(f'/api/teacher/quizzes/{quiz.id}/questions',
                            json=mcq_body('Soal tanpa materi',
                                          section_id=sec_b.id),
                            headers=h_o)
            check('guru lain tidak bisa menambah soal (403)',
                  r.status_code == 403, f"status={r.status_code}")

            # --------------------------------------------- UBAH SOAL
            print('\n[3] UBAH SOAL')
            r = client.put(f'/api/questions/{qid_default}',
                           json=mcq_body('Soal diubah',
                                         section_id=sec_b.id), headers=h_t)
            check('ubah section_id berhasil',
                  r.status_code == 200
                  and (r.get_json() or {}).get('question', {}).get('section_id') == sec_b.id,
                  f"status={r.status_code}")

            body = mcq_body('Soal diubah lagi')
            r = client.put(f'/api/questions/{qid_default}', json=body,
                           headers=h_t)
            check('tanpa section_id -> tag lama dipertahankan',
                  r.status_code == 200
                  and (r.get_json() or {}).get('question', {}).get('section_id') == sec_b.id,
                  f"status={r.status_code}")

            body = mcq_body('Soal diubah clear', section_id=None)
            r = client.put(f'/api/questions/{qid_default}', json=body,
                           headers=h_t)
            check('section_id null menghapus tag',
                  r.status_code == 200
                  and (r.get_json() or {}).get('question', {}).get('section_id') is None,
                  f"status={r.status_code}")

            # ------------------------------------------------ DUPLIKAT
            print('\n[4] DUPLIKAT')
            r = client.post(f'/api/teacher/quizzes/{quiz.id}/questions',
                            json=mcq_body('Soal untuk duplikat',
                                          section_id=sec_b.id), headers=h_t)
            src_id = (r.get_json() or {}).get('question', {}).get('question_id')
            r = client.post(f'/api/questions/{src_id}/duplicate', headers=h_t)
            check('duplikat menyalin section_id',
                  r.status_code == 201
                  and (r.get_json() or {}).get('question', {}).get('section_id') == sec_b.id,
                  f"status={r.status_code}")

            # --------------------------------------------- AKSI MASSAL
            print('\n[5] AKSI MASSAL (TERAPKAN KE SEMUA SOAL)')
            db.session.expire_all()
            n_questions = len(quiz.questions)
            r = client.put(f'/api/teacher/quizzes/{quiz.id}/questions/section',
                           json={'section_id': sec_a.id}, headers=h_t)
            body = r.get_json() or {}
            db.session.expire_all()
            all_a = all(q.section_id == sec_a.id for q in quiz.questions)
            check('terapkan bagian ke semua soal',
                  r.status_code == 200 and all_a
                  and body.get('section_id') == sec_a.id,
                  f"status={r.status_code} updated={body.get('updated')} n={n_questions}")

            r = client.put(f'/api/teacher/quizzes/{quiz.id}/questions/section',
                           json={'section_id': None}, headers=h_t)
            db.session.expire_all()
            check('terapkan null menghapus semua tag',
                  r.status_code == 200
                  and all(q.section_id is None for q in quiz.questions),
                  f"status={r.status_code}")

            r = client.put(f'/api/teacher/quizzes/{quiz.id}/questions/section',
                           json={'section_id': sec_other.id}, headers=h_t)
            check('terapkan bagian materi lain ditolak',
                  r.status_code == 400, f"status={r.status_code}")

            # ------------------------------------------ BANK & TOPIK
            print('\n[6] SOAL BANK & PEMETAAN TOPIK')
            r = client.post(f'/api/teacher/quizzes/{quiz_plain.id}/questions',
                            json={'bank_question_id': created['bank'].id},
                            headers=h_t)
            q_bank = (r.get_json() or {}).get('question', {})
            check('soal bank bertopik = judul bagian dipetakan',
                  r.status_code == 201 and q_bank.get('section_id') == sec_b.id,
                  f"status={r.status_code} section={q_bank.get('section_id')}")

            bank2 = QuestionBank(teacher_id=created['teacher'].id,
                                 question_text='Bank soal tanpa padanan',
                                 question_type='multiple_choice',
                                 topic='Topik Tidak Ada', difficulty='medium',
                                 points=10)
            db.session.add(bank2)
            db.session.flush()
            db.session.add_all([
                QuestionBankOption(bank_question_id=bank2.id, option_text='X',
                                   is_correct=True, order_index=0),
                QuestionBankOption(bank_question_id=bank2.id, option_text='Y',
                                   is_correct=False, order_index=1),
            ])
            db.session.commit()
            created['bank2'] = bank2
            r = client.post(f'/api/teacher/quizzes/{quiz_plain.id}/questions',
                            json={'bank_question_id': bank2.id}, headers=h_t)
            q_bank2 = (r.get_json() or {}).get('question', {})
            check('topik tak cocok dibiarkan kosong (tidak mengarang)',
                  r.status_code == 201 and q_bank2.get('section_id') is None,
                  f"status={r.status_code} section={q_bank2.get('section_id')}")

            # ------------------------------------------------- BACKFILL
            print('\n[7] FUNGSI BACKFILL')
            q_quiz = Question(quiz_id=quiz.id, text='Backfill ikut kuis',
                              question_type='multiple_choice',
                              difficulty='medium', points=10, order_index=99)
            db.session.add(q_quiz)
            # quiz still has section_id = sec_a from earlier update? It was
            # cleared by the bulk null test. Set it for the backfill check.
            quiz.section_id = sec_a.id
            db.session.commit()
            sec, reason = backfill.propose_section(q_quiz)
            check('backfill mengikuti section kuis', sec == sec_a.id,
                  f"sec={sec} reason={reason}")

            bank3 = QuestionBank(teacher_id=created['teacher'].id,
                                 question_text='Bank topik Bagian A',
                                 question_type='multiple_choice', topic='Bagian A',
                                 difficulty='medium', points=10)
            db.session.add(bank3)
            db.session.flush()
            q_bank_bf = Question(quiz_id=quiz_plain.id, text='Backfill topik',
                                 question_type='multiple_choice',
                                 difficulty='medium', points=10, order_index=99,
                                 bank_question_id=bank3.id)
            db.session.add(q_bank_bf)
            db.session.commit()
            created['bank3'] = bank3
            sec, reason = backfill.propose_section(q_bank_bf)
            check('backfill dari topik bank yang persis sama',
                  sec == sec_a.id, f"sec={sec} reason={reason}")

            q_single = Question(quiz_id=created['quiz_single'].id,
                                text='Backfill satu bagian',
                                question_type='multiple_choice',
                                difficulty='medium', points=10, order_index=99)
            db.session.add(q_single)
            db.session.commit()
            sec, reason = backfill.propose_section(q_single)
            check('backfill materi dengan tepat 1 bagian',
                  sec == sec_single.id, f"sec={sec} reason={reason}")

            q_amb = Question(quiz_id=quiz_plain.id, text='Backfill ambigu',
                             question_type='multiple_choice',
                             difficulty='medium', points=10, order_index=100)
            db.session.add(q_amb)
            db.session.commit()
            sec, reason = backfill.propose_section(q_amb)
            check('backfill tidak mengarang saat ambigu', sec is None,
                  f"sec={sec} reason={reason}")

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
