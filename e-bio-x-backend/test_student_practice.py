# ============================================================
# FASE 3d - LATIHAN SISWA DARI SOAL BANK YANG SUDAH DISETUJUI
#
# Kontrak yang dipatok test ini:
#   - tabel practice_answers ada dan terpisah dari student_answers
#   - HANYA soal APPROVED yang terlihat siswa: DRAFT dan REJECTED tak
#     bisa diambil, tidak bisa dijawab, tidak muncul di daftar
#   - kunci jawaban TIDAK PERNAH ada di respons pemuatan soal
#     (dicek dengan menelusuri seluruh payload, bukan hanya kunci teratas)
#   - bagian tanpa soal APPROVED -> 200 + daftar kosong + alasan,
#     bukan 404 dan bukan soal karangan
#   - jawaban dinilai dari order_index tersimpan, jadi kiriman yang
#     memalsukan kunci ditolak
#   - soal dari bagian lain / status DRAFT ditolak saat menjawab
#   - mengulang soal tidak menambah jumlah soal terjawab (yang dihitung
#     jawaban terakhir), jadi angka tidak bisa digelembungkan
#   - jawaban latihan masuk ke diagnosis Fase 2 sebagai sumber TERPISA
#     dan ambang INSUFFICIENT_DATA tetap berlaku
#   - akses: hanya siswa kelas yang mengikuti; guru/siswa lain 403
#
# Berjalan pada app + database nyata, membuat lalu menghapus fixture
# miliknya sendiri. Baris lama hanya dibaca.
# ============================================================
import os
import sys

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
from src.services import learning_analytics_service as analytics  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

STAMP = 'zzstudentpractice'
results = []
created = {}


def check(name, cond, extra=""):
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


def token_for(user):
    return create_access_token(identity=str(user.id))


def add_bank(teacher, section, status, text, feedback=True):
    bq = QuestionBank(
        teacher_id=teacher.id,
        question_text=text,
        question_type='multiple_choice',
        section_id=section.id if section else None,
        topic=section.title if section else None,
        difficulty='medium',
        explanation='Penjelasan resmi guru.',
        points=10,
        misconception='Virus dianggap sel hidup',
        source='ai',
        status=status,
    )
    db.session.add(bq)
    db.session.flush()
    db.session.add_all([
        QuestionBankOption(
            bank_question_id=bq.id, option_text=f'Benar {bq.id}',
            is_correct=True, order_index=0,
            feedback='Tepat sekali.' if feedback else None),
        QuestionBankOption(
            bank_question_id=bq.id, option_text=f'Salah {bq.id}',
            is_correct=False, order_index=1,
            feedback='Virus bukan sel.' if feedback else None),
    ])
    db.session.flush()
    return bq


def make_fixture():
    teacher = User(email=f'{STAMP}@test.local', name='Siswa Latihan Guru',
                   role='teacher')
    outsider = User(email=f'{STAMP}.other@test.local',
                    name='Siswa Latihan Guru Lain', role='teacher')
    student = User(email=f'{STAMP}.student@test.local', name='Siswa Latihan Siswa',
                   role='student')
    outsider_student = User(email=f'{STAMP}.outsider@test.local',
                            name='Siswa Luar Kelas', role='student')
    db.session.add_all([teacher, outsider, student, outsider_student])
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    other_course = Course(name=f'{STAMP} kelas lain', teacher_id=outsider.id)
    db.session.add_all([course, other_course])
    db.session.flush()
    db.session.add(Enrollment(student_id=student.id, course_id=course.id))

    material = Material(title='Materi Latihan Siswa', course_id=course.id,
                        teacher_id=teacher.id, status='published', topic='UJI')
    other_material = Material(title='Materi Kelas Lain', course_id=other_course.id,
                              teacher_id=outsider.id, status='published')
    draft_material = Material(title='Materi Belum Terbit', course_id=course.id,
                              teacher_id=teacher.id, status='draft')
    db.session.add_all([material, other_material, draft_material])
    db.session.flush()

    sec_a = MaterialSection(material_id=material.id, title='Siklus Replikasi', position=0)
    sec_b = MaterialSection(material_id=material.id, title='Struktur Virus', position=1)
    sec_empty = MaterialSection(material_id=material.id, title='Bagian Tanpa Latihan',
                                position=2)
    sec_other = MaterialSection(material_id=other_material.id, title='Bagian Asing',
                                position=0)
    sec_draft = MaterialSection(material_id=draft_material.id, title='Bagian Draft',
                                position=0)
    db.session.add_all([sec_a, sec_b, sec_empty, sec_other, sec_draft])
    db.session.flush()

    created.update(
        teacher=teacher, outsider=outsider, student=student,
        outsider_student=outsider_student, course=course, other_course=other_course,
        material=material, other_material=other_material,
        draft_material=draft_material, sec_a=sec_a, sec_b=sec_b,
        sec_empty=sec_empty, sec_other=sec_other, sec_draft=sec_draft,
        banks=[],
    )


def drop_fixture():
    rows = created.get('banks') or []
    if rows:
        for bq in rows:
            PracticeAnswer.query.filter_by(bank_question_id=bq.id).delete(
                synchronize_session=False)
    db.session.flush()
    for bq in rows:
        for opt in list(bq.options):
            db.session.delete(opt)
    db.session.flush()
    for bq in rows:
        db.session.delete(bq)
    db.session.flush()
    for key in ('sec_a', 'sec_b', 'sec_empty', 'sec_other', 'sec_draft'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    for key in ('material', 'other_material', 'draft_material'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.flush()
    db.session.query(Enrollment).filter_by(student_id=created['student'].id).delete(
        synchronize_session=False)
    for key in ('course', 'other_course'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    for key in ('teacher', 'outsider', 'student', 'outsider_student'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.commit()


def payload_has_key(obj, needle):
    """Apakah string ini muncul di mana saja di dalam payload?"""
    return needle in str(obj)


def main():
    app = create_app()
    with app.app_context():
        print('=' * 68)
        print('FASE 3d - LATIHAN SISWA (SOAL BANK APPROVED)')
        print('=' * 68)

        make_fixture()
        client = app.test_client()
        teacher = created['teacher']
        student = created['student']
        sec_a = created['sec_a']
        sec_b = created['sec_b']
        sec_empty = created['sec_empty']
        material = created['material']
        other_material = created['other_material']
        draft_material = created['draft_material']

        h_s = {'Authorization': f'Bearer {token_for(student)}'}
        h_t = {'Authorization': f'Bearer {token_for(teacher)}'}
        h_out = {'Authorization': f'Bearer {token_for(created["outsider_student"])}'}

        try:
            # ------------------------------------------------- 1. SKEMA
            print('\n[1] TABEL practice_answers')
            tables = set(inspect(db.engine).get_table_names())
            check('tabel practice_answers ada', 'practice_answers' in tables)
            cols = {c['name'] for c in inspect(db.engine).get_columns('practice_answers')}
            for name in ('student_id', 'material_id', 'section_id',
                         'bank_question_id', 'selected_option', 'is_correct',
                         'attempt_no', 'question_snapshot', 'answered_at'):
                check(f'kolom practice_answers.{name} ada', name in cols)
            check('student_answers tidak ikut berubah',
                  'source' not in {c['name'] for c in
                                   inspect(db.engine).get_columns('student_answers')},
                  'tabel lama tetap seperti semula')

            # ------------------------------------ 2. HANYA YANG APPROVED
            print('\n[2] HANYA SOAL APPROVED YANG TERLIHAT')
            approved = add_bank(teacher, sec_a, 'APPROVED', 'Soal latihan disetujui')
            draft = add_bank(teacher, sec_a, 'DRAFT', 'Draf belum disetujui')
            rejected = add_bank(teacher, sec_a, 'REJECTED', 'Draf ditolak guru')
            untagged = add_bank(teacher, None, 'APPROVED', 'Soal tanpa tag bagian')
            created['banks'] = [approved, draft, rejected, untagged]
            db.session.commit()

            r = client.get(f'/api/student/practice/{material.id}/sections', headers=h_s)
            body = r.get_json()
            check('daftar bagian 200', r.status_code == 200, f'status={r.status_code}')
            sec_row = next((x for x in body['sections'] if x['section_id'] == sec_a.id), {})
            check('bagian A punya 1 soal latihan', sec_row.get('practice_total') == 1,
                  f'total={sec_row.get("practice_total")}')
            ids = [x['section_id'] for x in body['sections']]
            empty_row = next((x for x in body['sections']
                              if x['section_id'] == sec_empty.id), {})
            check('semua bagian materi dilaporkan',
                  set(ids) == {sec_a.id, sec_b.id, sec_empty.id}, f'id={ids}')
            check('bagian tanpa soal: 0 dan tidak tersedia',
                  empty_row.get('practice_total') == 0 and empty_row.get('available') is False)
            check('catatan soal disetujui ada di respons',
                  'disetujui guru' in (body.get('note') or ''))

            r = client.get(f'/api/student/practice/{material.id}/sections/{sec_a.id}',
                           headers=h_s)
            body = r.get_json()
            served = [q['id'] for q in body['questions']]
            check('hanya soal APPROVED bagian A yang tersaji', served == [approved.id],
                  f'served={served}')
            check('soal DRAFT tidak tersaji', draft.id not in served)
            check('soal REJECTED tidak tersaji', rejected.id not in served)
            check('soal tanpa tag bagian tidak ikut', untagged.id not in served)
            check('total_available = 1', body.get('total_available') == 1)

            # ------------------------------ 3. KUNCI TIDAK BOCOR SAAT MUAT
            print('\n[3] KUNCI JAWABAN TIDAK BOCOR')
            raw = str(body)
            check('tidak ada is_correct di respons muat',
                  not payload_has_key(raw, 'is_correct'))
            check('kunci tidak bocor lewat explanation',
                  not payload_has_key(raw, 'Penjelasan resmi guru'))
            check('misconception tidak bocor',
                  not payload_has_key(raw, 'Virus dianggap sel hidup'))
            check('feedback opsi tidak bocor',
                  not payload_has_key(raw, 'Tepat sekali'))
            opts = body['questions'][0]['options']
            check('opsi hanya punya teks + order_index',
                  set(opts[0].keys()) == {'option_id', 'option_text', 'order_index'},
                  f"keys={sorted(opts[0].keys())}")

            # --------------------------------------- 4. BAGIAN KOSONG
            print('\n[4] BAGIAN TANPA SOAL TIDAK DIKARYAKAN')
            r = client.get(f'/api/student/practice/{material.id}/sections/{sec_empty.id}',
                           headers=h_s)
            body = r.get_json()
            check('status 200 bukan 404', r.status_code == 200, f'status={r.status_code}')
            check('daftar soal kosong', body['questions'] == [])
            check('total_available 0', body['total_available'] == 0)
            check('ada penjelasan jujur', bool(body.get('message')),
                  body.get('message'))

            # ------------------------------------------ 5. MENJAWAB BENAR
            print('\n[5] MENJAWAB DAN PENILAIAN')
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s, json={'bank_question_id': approved.id, 'selected_option': 0})
            body = r.get_json()
            check('jawaban benar dinilai benar', r.status_code == 200
                  and body['is_correct'] is True, f'status={r.status_code}')
            check('opsi benar disebut', body['correct_option'] == 0)
            check('pembahasan guru ikut', body['explanation'] == 'Penjelasan resmi guru.')
            check('misconception ikut', bool(body['misconception']))
            check('feedback tiap opsi ikut',
                  all(o['is_correct'] in (True, False) for o in body['options']))
            check('percobaan pertama', body['attempt_no'] == 1)
            check('baris tersimpan', PracticeAnswer.query.filter_by(
                bank_question_id=approved.id).count() == 1)

            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s, json={'bank_question_id': approved.id, 'selected_option': 1})
            body = r.get_json()
            check('jawaban salah dinilai salah', body['is_correct'] is False)
            check('percobaan kedua tercatat', body['attempt_no'] == 2)
            check('opsi salah ditolak semua baris', PracticeAnswer.query.filter_by(
                bank_question_id=approved.id, is_correct=True).count() == 1)

            # -------------------------------------- 6. MENGULANG TIDAK NAIK
            print('\n[6] MENGULANG TIDAK MENGGELOMBUNGI ANGKA')
            for _ in range(3):
                client.post(
                    f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                    headers=h_s,
                    json={'bank_question_id': approved.id, 'selected_option': 0})
            r = client.get(f'/api/student/practice/{material.id}/sections/{sec_a.id}',
                           headers=h_s)
            body = r.get_json()
            check('soal terjawab tetap 1 meski 5 percobaan',
                  body['practice_answered'] == 1,
                  f"answered={body['practice_answered']} percobaan={PracticeAnswer.query.count()}")
            check('total percobaan tetap tercatat apa adanya',
                  PracticeAnswer.query.filter_by(bank_question_id=approved.id).count() == 5)

            # ------------------------------------ 7. KIRIMAN PALSU DITOLAK
            print('\n[7] KIRIMAN PALSU / SILANG BAGIAN DITOLAK')
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s,
                json={'bank_question_id': approved.id, 'selected_option': 99})
            check('order_index di luar jangkauan ditolak', r.status_code == 400,
                  f'status={r.status_code}')

            opt_id = opts[0]['option_id']  # id baris opsi yang BENAR
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s,
                json={'bank_question_id': approved.id, 'selected_option': opt_id})
            check('option_id baris bukan order_index, jadi ditolak',
                  r.status_code == 400, f'status={r.status_code} option_id={opt_id}')
            check('kiriman palsukan tidak menambah baris',
                  PracticeAnswer.query.filter_by(bank_question_id=approved.id).count() == 5)

            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s, json={'bank_question_id': draft.id, 'selected_option': 0})
            check('soal DRAFT tidak bisa dijawab', r.status_code == 403,
                  f'status={r.status_code}')
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s, json={'bank_question_id': rejected.id, 'selected_option': 0})
            check('soal REJECTED tidak bisa dijawab', r.status_code == 403,
                  f'status={r.status_code}')

            sec_b_bank = add_bank(teacher, sec_b, 'APPROVED', 'Soal bagian lain')
            created['banks'].append(sec_b_bank)
            db.session.commit()
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s,
                json={'bank_question_id': sec_b_bank.id, 'selected_option': 0})
            check('soal bagian lain ditolak', r.status_code == 400,
                  f'status={r.status_code}')

            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s, json={'selected_option': 0})
            check('tanpa bank_question_id ditolak', r.status_code == 404,
                  f'status={r.status_code}')
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s, json={'bank_question_id': 99999999, 'selected_option': 0})
            check('soal tidak ada -> 404', r.status_code == 404, f'status={r.status_code}')

            # ------------------------------------------- 8. BATAS AKSES
            print('\n[8] AKSES SISWA')
            r = client.get(f'/api/student/practice/{material.id}/sections', headers=h_t)
            check('guru ditolak', r.status_code == 403, f'status={r.status_code}')
            r = client.get(f'/api/student/practice/{other_material.id}/sections',
                           headers=h_s)
            check('materi kelas lain ditolak', r.status_code == 403,
                  f'status={r.status_code}')
            r = client.get(f'/api/student/practice/{draft_material.id}/sections',
                           headers=h_s)
            check('materi belum terbit ditolak', r.status_code == 403,
                  f'status={r.status_code}')
            r = client.get('/api/student/practice/99999999/sections', headers=h_s)
            check('materi tidak ada -> 404', r.status_code == 404, f'status={r.status_code}')
            r = client.get(f'/api/student/practice/{material.id}/sections/'
                           f'{created["sec_other"].id}', headers=h_s)
            check('bagian materi lain -> 404', r.status_code == 404,
                  f'status={r.status_code}')
            r = client.get(f'/api/student/practice/{draft_material.id}/sections/'
                           f'{created["sec_draft"].id}', headers=h_s)
            check('materi belum terbit dicek lebih dulu', r.status_code == 403,
                  f'status={r.status_code}')
            r = client.get(f'/api/student/practice/{material.id}/sections', headers=h_out)
            check('siswa di luar kelas tidak bisa', r.status_code == 403,
                  f'status={r.status_code}')

            # Kiriman rusak harus jadi 4xx yang jujur, bukan 500 dari dalam
            # SQLAlchemy karena id bukan angka.
            r = client.get('/api/student/practice/bukan-angka/sections', headers=h_s)
            check('material_id rusak -> 404', r.status_code == 404,
                  f'status={r.status_code}')
            r = client.get(f'/api/student/practice/{material.id}/sections/bukan-angka',
                           headers=h_s)
            check('section_id rusak -> 404', r.status_code == 404,
                  f'status={r.status_code}')
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s,
                json={'bank_question_id': 'bukan-angka', 'selected_option': 0})
            check('bank_question_id rusak -> 404', r.status_code == 404,
                  f'status={r.status_code}')
            r = client.post(
                f'/api/student/practice/{material.id}/sections/{sec_a.id}/answer',
                headers=h_s,
                json={'bank_question_id': approved.id, 'selected_option': 'abc'})
            check('selected_option rusak -> 400', r.status_code == 400,
                  f'status={r.status_code}')

            # ------------------------ 9. MASUK KE DIAGNOSIS FASE 2 (TERPISA)
            print('\n[9] DIAGNOSIS FASE 2 MENERIMA LATIHAN')
            report = analytics.section_mastery_for_student(student.id, material.id)
            row_a = next(r for r in report['sections'] if r['section_id'] == sec_a.id)
            check('practice_answered muncul terpisah',
                  row_a['practice_answered'] == 1 and row_a['practice_correct'] == 1,
                  f"practice={row_a['practice_answered']}/{row_a['practice_correct']}")
            check('gabungan memasukkan latihan',
                  row_a['answered'] == row_a['practice_answered'])
            check('sumber angka dinyatakan terbuka',
                  'latihan' in row_a['score_sources'], f"sumber={row_a['score_sources']}")
            check('di bawah ambang tetap INSUFFICIENT_DATA',
                  row_a['status'] == 'INSUFFICIENT_DATA' and row_a['score'] is None,
                  f"status={row_a['status']} n={row_a['answered']}")

            row_empty = next(r for r in report['sections']
                             if r['section_id'] == sec_empty.id)
            check('bagian tanpa jawaban tetap 0 dan tanpa skor',
                  row_empty['answered'] == 0 and row_empty['status'] == 'INSUFFICIENT_DATA')

            # ------------------------- 10. MENCAPAI AMBANG MINIMUM
            print('\n[10] AMBANG MINIMUM DAPAT TERCAPAI DARI LATIHAN')
            sec_c = MaterialSection(material_id=material.id, title='Bagian Uji Ambang',
                                    position=3)
            db.session.add(sec_c)
            db.session.flush()
            b1 = add_bank(teacher, sec_c, 'APPROVED', 'Ambang soal 1')
            b2 = add_bank(teacher, sec_c, 'APPROVED', 'Ambang soal 2')
            b3 = add_bank(teacher, sec_c, 'APPROVED', 'Ambang soal 3')
            created['banks'] += [b1, b2, b3]
            db.session.commit()
            for i, bq in enumerate((b1, b2, b3)):
                client.post(
                    f'/api/student/practice/{material.id}/sections/{sec_c.id}/answer',
                    headers=h_s,
                    json={'bank_question_id': bq.id, 'selected_option': 0 if i < 2 else 1})
            report = analytics.section_mastery_for_student(student.id, material.id)
            row_c = next(r for r in report['sections'] if r['section_id'] == sec_c.id)
            check('3 soal latihan -> status READY',
                  row_c['status'] == 'READY' and row_c['answered'] == 3,
                  f"status={row_c['status']} n={row_c['answered']}")
            check('skor = 2 benar dari 3 (tidak dikarang)',
                  row_c['score'] == 66.7, f"score={row_c['score']}")
            check('hanya latihan yang menyumbang',
                  row_c['score_sources'] == ['latihan'],
                  f"sumber={row_c['score_sources']}")

            # ------------------------------ 11. DATA PROGRES SIWA
            print('\n[11] PROGRES SIWA MENYIAPKAN TOMBOL LATIHAN')
            r = client.get(f'/api/student/progress/{material.id}', headers=h_s)
            detail = r.get_json()
            rows = {x['section_id']: x for x in detail['sections']}
            check('practice_total ikut di detail progres',
                  rows[sec_a.id]['practice_total'] == 1
                  and rows[sec_empty.id]['practice_total'] == 0,
                  f"A={rows[sec_a.id]['practice_total']} kosong={rows[sec_empty.id]['practice_total']}")
            check('practice_answered ikut di detail progres',
                  rows[sec_a.id]['practice_answered'] == 1)

            # ------------------------------- 12. DATA LAMA TIDAK RUSAK
            print('\n[12] DATA LAMA TIDAK RUSAK')
            legacy = db.session.execute(db.text(
                "select count(*) from student_answers")).scalar()
            check('student_answers lama utuh', legacy is not None and legacy > 0,
                  f'total={legacy}')
            legacy_bank = db.session.execute(db.text(
                "select count(*) from question_bank where teacher_id in "
                "(select id from users where email like 'guru%' or email like 'admin%')"
            )).scalar()
            check('soal bank lama utuh', legacy_bank is not None and legacy_bank > 0,
                  f'total={legacy_bank}')

        finally:
            db.session.rollback()
            drop_fixture()

        print('\n' + '=' * 68)
        failed = [r for r in results if not r[1]]
        print(f'TOTAL {len(results)} check | PASS {len(results) - len(failed)} '
              f'| FAIL {len(failed)}')
        for name, _ok, extra in failed:
            print(f'  FAIL: {name} {extra}')
        print('=' * 68)
        return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())