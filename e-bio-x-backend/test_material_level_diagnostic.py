# ============================================================
# FASE 4 LEVEL - SET DIAGNOSTIK & LEVEL MATERI TERUKUR
#
# Kontrak yang dipatok test ini:
#   - `question_bank.purpose` ada, bernilai 'practice'/'diagnostic', dan
#     baris lama otomatis jadi 'practice' (default migrasi).
#   - DUA POOL TIDAK PERNAH BERCAMPUR:
#       * endpoint latihan hanya menyajikan soal purpose='practice'
#       * endpoint diagnostik hanya menyajikan soal purpose='diagnostic'
#       * menjawab lintas-jalur ditolak (400), jadi catatan tidak bisa
#         dipindahkan diam-diam ke pool yang salah.
#   - Urutan soal diagnostik TETAP (tidak diacak/adaptif), supaya hasil
#     antar-siswa sebanding.
#   - Kunci jawaban TIDAK bocor di respons pemuatan soal diagnostik.
#   - `material_level_observed` memberi label HANYA bila lolos DUA gerbang:
#     jumlah soal READY >= K (3) dan jumlah siswa berbeda >= N (20).
#     Di bawah itu -> INSUFFICIENT_DATA + alasan, bukan label karangan.
#   - Angka pooled persis seperti spesifikasi: p = Σ benar / Σ n (soal READY),
#     margin CI 95% aproksimasi normal, penanda "dekat batas".
#   - Satu siswa dihitung SEKALI per soal (jawaban pertama), jadi mengulang
#     soal tidak bisa menggeser level materi.
#   - Sisi guru: `diagnostic_count` terpisah dari `approved_count`, dan
#     `difficulty_observed` dikirim berdampingan `difficulty_declared`.
#
# Berjalan pada app + database nyata, membuat lalu menghapus fixture
# miliknya sendiri. Baris lama HANYA dibaca.
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
from src.services import question_difficulty_service as qds  # noqa: E402
from src.services import student_practice_service as spractice  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

STAMP = 'zzmateriallevel'
results = []
created = {}
BASE_T = datetime(2026, 1, 1, 8, 0, 0)

# Distribusi jawaban (jumlah siswa yang benar dari 25) supaya pooled p-nya
# persis contoh spesifikasi: 14 + 18 + 11 = 43 benar dari 75 jawaban = 0.573.
READY_DISTRIBUTION = [14, 18, 11]
N_ANSWERERS = 25


def check(name, cond, extra=""):
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


def token_for(user):
    return create_access_token(identity=str(user.id))


def add_bank(teacher, section, status, text, purpose='practice'):
    bq = QuestionBank(
        teacher_id=teacher.id,
        question_text=text,
        question_type='multiple_choice',
        section_id=section.id if section else None,
        topic=section.title if section else None,
        difficulty='medium',
        explanation='Penjelasan resmi guru.',
        points=10,
        misconception='Miskonsepsi rahasia',
        source='ai',
        status=status,
        purpose=purpose,
    )
    db.session.add(bq)
    db.session.flush()
    db.session.add_all([
        QuestionBankOption(
            bank_question_id=bq.id, option_text=f'Benar {bq.id}',
            is_correct=True, order_index=0, feedback='Tepat sekali.'),
        QuestionBankOption(
            bank_question_id=bq.id, option_text=f'Salah {bq.id}',
            is_correct=False, order_index=1, feedback='Bukan itu.'),
    ])
    db.session.flush()
    return bq


def make_fixture():
    teacher = User(email=f'{STAMP}@test.local', name='Guru Level', role='teacher')
    outsider = User(email=f'{STAMP}.other@test.local', name='Guru Lain Level',
                    role='teacher')
    student = User(email=f'{STAMP}.student@test.local', name='Murid Level',
                   role='student')
    db.session.add_all([teacher, outsider, student])
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    db.session.add(course)
    db.session.flush()
    db.session.add(Enrollment(student_id=student.id, course_id=course.id))

    ready = Material(title='Materi Siap Ukur', course_id=course.id,
                     teacher_id=teacher.id, status='published', difficulty='hard')
    few = Material(title='Materi Soal Kurang', course_id=course.id,
                   teacher_id=teacher.id, status='published')
    empty = Material(title='Materi Tanpa Diagnostik', course_id=course.id,
                     teacher_id=teacher.id, status='published')
    db.session.add_all([ready, few, empty])
    db.session.flush()

    sec_ready_diag = MaterialSection(material_id=ready.id, title='Bagian Diagnostik',
                                     position=0)
    sec_ready_practice = MaterialSection(material_id=ready.id, title='Bagian Latihan',
                                         position=1)
    sec_few = MaterialSection(material_id=few.id, title='Bagian Kurang', position=0)
    sec_empty = MaterialSection(material_id=empty.id, title='Bagian Kosong', position=0)
    db.session.add_all([sec_ready_diag, sec_ready_practice, sec_few, sec_empty])
    db.session.flush()

    ready_diag = [
        add_bank(teacher, sec_ready_diag, 'APPROVED', f'Diagnostik siap {i}',
                 purpose='diagnostic')
        for i in range(3)
    ]
    ready_practice = add_bank(teacher, sec_ready_practice, 'APPROVED',
                              'Latihan siap', purpose='practice')
    few_diag = [
        add_bank(teacher, sec_few, 'APPROVED', f'Diagnostik kurang {i}',
                 purpose='diagnostic')
        for i in range(2)
    ]

    # 25 siswa "pengukur": hanya baris USER yang dipakai service level (yang
    # dibaca hanya PracticeAnswer), jadi tidak perlu enrollment.
    answerers = []
    for i in range(N_ANSWERERS):
        u = User(email=f'{STAMP}.a{i}@test.local', name=f'Pengukur {i}',
                 role='student')
        db.session.add(u)
        answerers.append(u)
    db.session.flush()

    rows = []
    for idx, bq in enumerate(ready_diag):
        n_correct = READY_DISTRIBUTION[idx]
        for i, u in enumerate(answerers):
            rows.append(_answer(u, ready, sec_ready_diag, bq,
                                 i < n_correct, minutes=idx * 100 + i,
                                 mode='diagnostic'))
    for bq in few_diag:
        for i, u in enumerate(answerers):
            rows.append(_answer(u, few, sec_few, bq, i < 15,
                                 minutes=1000 + i, mode='diagnostic'))
    db.session.add_all(rows)
    db.session.flush()

    created.update(
        teacher=teacher, outsider=outsider, student=student, course=course,
        ready=ready, few=few, empty=empty,
        sec_ready_diag=sec_ready_diag, sec_ready_practice=sec_ready_practice,
        sec_few=sec_few, sec_empty=sec_empty,
        ready_diag=ready_diag, ready_practice=ready_practice, few_diag=few_diag,
        answerers=answerers, banks=ready_diag + [ready_practice] + few_diag,
    )
    db.session.commit()


def _answer(user, material, section, bq, is_correct, minutes=0, mode='practice'):
    """Bangun satu baris jawaban.

    `mode` harus diisi eksplisit: 'diagnostic' bila ini dipakai untuk
    membuktikan pengukuran tingkat materi, 'practice' bila dipakai untuk
    membuktikan jawaban latihan TIDAK ikut.
    """
    return PracticeAnswer(
        student_id=user.id, material_id=material.id, section_id=section.id,
        bank_question_id=bq.id,
        selected_option=0 if is_correct else 1,
        is_correct=bool(is_correct), attempt_no=1,
        question_snapshot=bq.question_text,
        mode=mode,
        answered_at=BASE_T + timedelta(minutes=minutes),
    )


def drop_fixture():
    rows = created.get('banks') or []
    if rows:
        PracticeAnswer.query.filter(
            PracticeAnswer.bank_question_id.in_([b.id for b in rows])
        ).delete(synchronize_session=False)
        db.session.flush()
        for bq in rows:
            for opt in list(bq.options):
                db.session.delete(opt)
        db.session.flush()
        for bq in rows:
            db.session.delete(bq)
        db.session.flush()
    for key in ('sec_ready_diag', 'sec_ready_practice', 'sec_few', 'sec_empty'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.flush()
    for key in ('ready', 'few', 'empty'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.flush()
    db.session.query(Enrollment).filter_by(student_id=created['student'].id).delete(
        synchronize_session=False)
    if created.get('course') is not None:
        db.session.delete(created['course'])
    for u in (created.get('answerers') or []):
        db.session.delete(u)
    for key in ('teacher', 'outsider', 'student'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.commit()


def payload_has_key(obj, needle):
    return needle in str(obj)


def main():
    app = create_app()
    with app.app_context():
        print('=' * 68)
        print('FASE 4 LEVEL - SET DIAGNOSTIK & LEVEL MATERI TERUKUR')
        print('=' * 68)

        make_fixture()
        client = app.test_client()
        teacher = created['teacher']
        student = created['student']
        ready = created['ready']
        few = created['few']
        empty = created['empty']
        sec_diag = created['sec_ready_diag']
        sec_practice = created['sec_ready_practice']
        ready_diag = created['ready_diag']

        h_s = {'Authorization': f'Bearer {token_for(student)}'}
        h_t = {'Authorization': f'Bearer {token_for(teacher)}'}

        try:
            # ------------------------------------------------- 1. SKEMA
            print('\n[1] SKEMA: kolom purpose')
            cols = {c['name'] for c in
                    inspect(db.engine).get_columns('question_bank')}
            check('kolom question_bank.purpose ada', 'purpose' in cols)
            fresh = add_bank(teacher, created['sec_empty'], 'APPROVED',
                             'Soal tanpa purpose eksplisit')
            db.session.flush()
            check('default purpose = practice', fresh.purpose == 'practice',
                  f'purpose={fresh.purpose}')
            created['banks'].append(fresh)
            db.session.commit()

            # ------------------------------- 2. DUA POOL TIDAK BERCAMPUR
            print('\n[2] POOL TERPISAH (latihan vs diagnostik)')
            r = client.get(f'/api/student/practice/{ready.id}/sections', headers=h_s)
            body = r.get_json()
            check('daftar bagian 200', r.status_code == 200, f'status={r.status_code}')
            row_diag = next((x for x in body['sections']
                             if x['section_id'] == sec_diag.id), {})
            row_prac = next((x for x in body['sections']
                             if x['section_id'] == sec_practice.id), {})
            check('bagian berisi diagnostik: practice_total 0',
                  row_diag.get('practice_total') == 0,
                  f"total={row_diag.get('practice_total')}")
            check('bagian berisi diagnostik: diagnostic_total 3',
                  row_diag.get('diagnostic_total') == 3,
                  f"diag={row_diag.get('diagnostic_total')}")
            check('bagian latihan: practice_total 1 + tersedia',
                  row_prac.get('practice_total') == 1
                  and row_prac.get('available') is True)
            check('bagian latihan: diagnostic_total 0',
                  row_prac.get('diagnostic_total') == 0)

            r = client.get(
                f'/api/student/practice/{ready.id}/sections/{sec_diag.id}',
                headers=h_s)
            body = r.get_json()
            check('endpoint latihan tidak menyajikan soal diagnostik',
                  body['questions'] == [], f"n={len(body['questions'])}")

            r = client.get(
                f'/api/student/diagnostic/{ready.id}/sections/{sec_diag.id}',
                headers=h_s)
            body = r.get_json()
            check('endpoint diagnostik 200', r.status_code == 200,
                  f'status={r.status_code}')
            served = [q['id'] for q in body['questions']]
            check('urutan diagnostik TETAP (urut id, tidak diacak)',
                  served == [b.id for b in ready_diag], f'served={served}')
            check('total_available 3', body.get('total_available') == 3)
            check('basis sesi = diagnostic',
                  (body.get('session') or {}).get('basis') == 'diagnostic')

            # --------------------------------- 3. KUNCI TIDAK BOCOR
            print('\n[3] KUNCI JAWABAN TIDAK BOCOR (diagnostik)')
            raw = str(body)
            check('tidak ada is_correct di respons muat',
                  not payload_has_key(raw, 'is_correct'))
            check('penjelasan guru tidak bocor',
                  not payload_has_key(raw, 'Penjelasan resmi guru.'))
            check('miskonsepsi tidak bocor',
                  not payload_has_key(raw, 'Miskonsepsi rahasia'))
            check('feedback opsi tidak bocor',
                  not payload_has_key(raw, 'Tepat sekali.'))
            opts = body['questions'][0]['options']
            check('opsi hanya teks + order_index',
                  set(opts[0].keys()) == {'option_id', 'option_text', 'order_index'},
                  f"keys={sorted(opts[0].keys())}")

            r = client.get(
                f'/api/student/diagnostic/{ready.id}/sections/{sec_practice.id}',
                headers=h_s)
            body = r.get_json()
            check('endpoint diagnostik tidak menyajikan soal latihan',
                  body['questions'] == [], f"n={len(body['questions'])}")
            check('bagian tanpa diagnostik: ada alasan jujur',
                  bool(body.get('message')), body.get('message'))

            # ------------------------- 4. LINTAS-JALUR DITOLAK
            print('\n[4] MENJAWAB LINTAS-JALUR DITOLAK')
            r = client.post(
                f'/api/student/practice/{ready.id}/sections/{sec_diag.id}/answer',
                headers=h_s,
                json={'bank_question_id': ready_diag[0].id, 'selected_option': 0})
            check('soal diagnostik ditolak di jalur latihan (400)',
                  r.status_code == 400, f'status={r.status_code}')
            check('alasan menyebut diagnostik',
                  'diagnostik' in (r.get_json().get('error') or '').lower(),
                  r.get_json().get('error'))
            r = client.post(
                f'/api/student/diagnostic/{ready.id}/sections/{sec_practice.id}/answer',
                headers=h_s,
                json={'bank_question_id': created['ready_practice'].id,
                      'selected_option': 0})
            check('soal latihan ditolak di jalur diagnostik (400)',
                  r.status_code == 400, f'status={r.status_code}')
            check('tidak ada baris tercatat dari jawaban lintas-jalur',
                  PracticeAnswer.query.filter_by(
                      student_id=student.id).count() == 0)

            # ------------------------ 5. GERBANG & ANGKA LEVEL
            print('\n[5] LEVEL MATERI: GERBANG & ANGKA')
            lv = qds.material_level_observed(empty.id)
            check('tanpa soal diagnostik -> INSUFFICIENT_DATA',
                  lv['status'] == 'INSUFFICIENT_DATA')
            check('alasan no_questions', lv.get('reason') == 'no_questions',
                  lv.get('reason'))
            check('tanpa label yang dikarang', lv.get('label') is None)

            lv = qds.material_level_observed(few.id)
            check('soal < K -> INSUFFICIENT_DATA', lv['status'] == 'INSUFFICIENT_DATA')
            check('alasan items', lv.get('reason') == 'items', lv.get('reason'))
            check('melaporkan 2 soal READY dari 2 total',
                  lv.get('n_items') == 2 and lv.get('n_items_total') == 2,
                  f"n_items={lv.get('n_items')} total={lv.get('n_items_total')}")

            lv = qds.material_level_observed(ready.id, min_students=30)
            check('siswa < N -> INSUFFICIENT_DATA (gerbang kedua)',
                  lv['status'] == 'INSUFFICIENT_DATA' and lv.get('reason') == 'students',
                  f"reason={lv.get('reason')}")
            check('jumlah siswa berbeda dilaporkan 25', lv.get('n_students') == 25,
                  f"n_students={lv.get('n_students')}")

            lv = qds.material_level_observed(ready.id, min_items=5)
            check('soal READY < min_items kustom -> items',
                  lv.get('reason') == 'items', lv.get('reason'))

            print('\n[6] LEVEL MATERI: PERHITUNGAN POOLED (SIAP)')
            lv = qds.material_level_observed(ready.id)
            check('status READY', lv['status'] == 'READY', lv['status'])
            check('label kanonik medium (p 0.573)', lv.get('label') == 'medium',
                  f"label={lv.get('label')}")
            check('label Indonesia sedang', lv.get('label_id') == 'sedang',
                  f"label_id={lv.get('label_id')}")
            check('p = 43/75 = 0.573', abs((lv.get('p') or 0) - 0.573) < 0.001,
                  f"p={lv.get('p')}")
            check('n_answers = 75', lv.get('n_answers') == 75,
                  f"n={lv.get('n_answers')}")
            check('correct = 43', lv.get('correct') == 43, f"correct={lv.get('correct')}")
            check('n_items = 3', lv.get('n_items') == 3, f"n_items={lv.get('n_items')}")
            check('n_students = 25', lv.get('n_students') == 25,
                  f"n_students={lv.get('n_students')}")
            check('margin CI 95% ~ 0.112', abs((lv.get('margin') or 0) - 0.112) < 0.002,
                  f"margin={lv.get('margin')}")
            check('margin_points ikut (11 poin)', lv.get('margin_points') == 11,
                  f"margin_points={lv.get('margin_points')}")
            check('tidak dekat batas', lv.get('near_boundary') is False)
            check('basis = observed_diagnostic',
                  lv.get('basis') == 'observed_diagnostic', lv.get('basis'))
            check('computed_at ada', bool(lv.get('computed_at')))

            # --------------- 7. SATU SISWA DIHITUNG SEKALI PER SOAL
            print('\n[7] JAWABAN ULANG TIDAK MENGGESER LEVEL')
            dup = _answer(created['answerers'][0], ready, sec_diag, ready_diag[0],
                          is_correct=False, minutes=999999, mode='diagnostic')
            db.session.add(dup)
            db.session.commit()
            lv2 = qds.material_level_observed(ready.id)
            check('jumlah jawaban tetap 75', lv2.get('n_answers') == 75,
                  f"n={lv2.get('n_answers')}")
            check('jumlah benar tetap 43 (jawaban pertama menang)',
                  lv2.get('correct') == 43, f"correct={lv2.get('correct')}")
            check('p tetap 0.573', abs((lv2.get('p') or 0) - 0.573) < 0.001,
                  f"p={lv2.get('p')}")

            # ------- 7b. JAWABAN LATIHAN LAMA TIDAK JADI BUKTI DIAGNOSTIK
            print('\n[7b] SOAL YANG BARU DITANDAI DIAGNOSTIK TIDAK MENARIK '
                  'JAWABAN LATIHAN LAMANYA')
            # Soal boleh berpindah jalur: guru menandai soal latihan lama
            # sebagai diagnostik. Jawaban adaptif siswa atas soal itu harus
            # TETAP diabaikan - kalau tidak, sampelnya kembali bias mesin
            # 60/30/10, persis yang ingin dihindari fitur ini.
            leaker = User(email=f'{STAMP}.leak@test.local', name='Pengukur Leak',
                          role='student')
            db.session.add(leaker)
            db.session.flush()
            leak_rows = [
                _answer(leaker, ready, sec_diag, bq, i < 2, minutes=7000 + i)
                for i, bq in enumerate(created['ready_diag'])
            ]
            db.session.add_all(leak_rows)
            db.session.commit()

            lv3 = qds.material_level_observed(ready.id)
            check('jawaban mode=practice tidak ditambahkan',
                  lv3.get('n_answers') == 75, f"n={lv3.get('n_answers')}")
            check('jumlah benar tidak berubah',
                  lv3.get('correct') == 43, f"correct={lv3.get('correct')}")
            check('n_students tetap 25 (siswa latihan tidak dihitung)',
                  lv3.get('n_students') == 25,
                  f"n_students={lv3.get('n_students')}")

            spstats = spractice.diagnostic_stats(leaker.id, ready.id).get(
                sec_diag.id, {'answered': 0, 'correct': 0})
            check('diagnostic_stats: 0 soal (jawaban latihan diabaikan)',
                  spstats.get('answered') == 0,
                  f"answered={spstats.get('answered')}")

            for _row in leak_rows:
                db.session.delete(_row)
            db.session.delete(leaker)
            db.session.commit()
            check('pembuktian tidak meninggalkan jejak',
                  qds.material_level_observed(ready.id).get('n_answers') == 75)

            # ---------------------- 8. SISI GURU: SECTION ROWS
            print('\n[8] SISI GURU: diagnostic_count TERPISAH')
            r = client.get(
                f'/api/teacher/practice/sections?material_id={ready.id}',
                headers=h_t)
            body = r.get_json()
            check('sections guru 200', r.status_code == 200, f'status={r.status_code}')
            row = next((x for x in body['sections'] if x['section_id'] == sec_diag.id), {})
            check('diagnostic_count 3 di bagian diagnostik',
                  row.get('diagnostic_count') == 3, f"diag={row.get('diagnostic_count')}")
            check('approved_count TIDAK menghitung diagnostik',
                  row.get('approved_count') == 0, f"appr={row.get('approved_count')}")
            row = next((x for x in body['sections']
                        if x['section_id'] == sec_practice.id), {})
            check('approved_count 1 di bagian latihan',
                  row.get('approved_count') == 1 and row.get('diagnostic_count') == 0)

            # ---------------------- 9. SISI GURU: BANK SOAL
            print('\n[9] SISI GURU: BANK SOAL & PURPOSE')
            r = client.get('/api/teacher/question-bank?purpose=diagnostic',
                           headers=h_t)
            body = r.get_json()
            items = body.get('data', body.get('items', body if isinstance(body, list) else []))
            diag_ids = {b['id'] for b in items}
            check('filter purpose=diagnostic hanya diagnostik',
                  {b.id for b in ready_diag + created['few_diag']} <= diag_ids
                  and created['ready_practice'].id not in diag_ids)
            check('serializer mengirim purpose',
                  all('purpose' in b for b in items), f"n={len(items)}")
            r = client.get('/api/teacher/question-bank?purpose=bogus', headers=h_t)
            check('purpose tidak dikenal -> 400', r.status_code == 400,
                  f'status={r.status_code}')

            toggle = add_bank(teacher, created['sec_empty'], 'APPROVED',
                              'Soal toggle purpose')
            created['banks'].append(toggle)
            db.session.commit()
            base_payload = {
                'question_text': toggle.question_text,
                'question_type': 'multiple_choice',
                'points': 10,
                'options': [
                    {'option_text': f'Benar {toggle.id}', 'is_correct': True},
                    {'option_text': f'Salah {toggle.id}', 'is_correct': False},
                ],
            }
            r = client.put(f'/api/teacher/question-bank/{toggle.id}', headers=h_t,
                           json={**base_payload, 'purpose': 'ngawur'})
            check('purpose tidak valid ditolak 400', r.status_code == 400,
                  f'status={r.status_code}')
            # 400 sebelum commit: buang perubahan setengah jalan seperti yang
            # dilakukan teardown request, supaya percobaan berikut bersih.
            db.session.rollback()
            db.session.expire_all()
            check('purpose tetap practice setelah penolakan',
                  QuestionBank.query.get(toggle.id).purpose == 'practice',
                  f"purpose={QuestionBank.query.get(toggle.id).purpose}")

            r = client.put(f'/api/teacher/question-bank/{toggle.id}', headers=h_t,
                           json={**base_payload, 'purpose': 'diagnostic'})
            check('guru bisa mengubah purpose (200)', r.status_code == 200,
                  f'status={r.status_code} {r.get_json()}')
            db.session.expire_all()
            check('perubahan tersimpan',
                  QuestionBank.query.get(toggle.id).purpose == 'diagnostic',
                  f"purpose={QuestionBank.query.get(toggle.id).purpose}")

            # ------------------- 10. ANALITIK GURU
            print('\n[10] ANALITIK GURU: DEKLARASI vs TERUKUR')
            r = client.get(f'/api/teacher/analytics/materials/{ready.id}',
                           headers=h_t)
            check('analitik materi guru 200', r.status_code == 200,
                  f'status={r.status_code}')
            ma = r.get_json()
            check('difficulty_declared = hard (deklarasi utuh)',
                  ma.get('difficulty_declared') == 'hard',
                  f"declared={ma.get('difficulty_declared')}")
            obs = ma.get('difficulty_observed') or {}
            check('difficulty_observed READY', obs.get('status') == 'READY',
                  f"status={obs.get('status')}")
            check('observed berdampingan tanpa menimpa deklarasi',
                  obs.get('label') == 'medium' and ma.get('difficulty_declared') == 'hard')

            r = client.get(f'/api/materials/{ready.id}/analytics', headers=h_t)
            check('analitik materi 200', r.status_code == 200, f'status={r.status_code}')
            ma = (r.get_json() or {}).get('analytics') or {}
            check('analytics punya difficulty_observed',
                  (ma.get('difficulty_observed') or {}).get('status') == 'READY')
            sec_diags = {s['section_id']: s['diagnostic_count']
                         for s in ma.get('section_diagnostics', [])}
            check('section_diagnostics melaporkan 3 dan 0',
                  sec_diags.get(sec_diag.id) == 3
                  and sec_diags.get(sec_practice.id) == 0, f"{sec_diags}")

            # ----------- 11. SISWA MENJAWAB DIAGNOSTIK (jalur asli)
            print('\n[11] SISWA MENJAWAB DIAGNOSTIK')
            r = client.post(
                f'/api/student/diagnostic/{ready.id}/sections/{sec_diag.id}/answer',
                headers=h_s,
                json={'bank_question_id': ready_diag[0].id, 'selected_option': 0})
            body = r.get_json()
            check('jawaban diagnostik dinilai 200', r.status_code == 200,
                  f'status={r.status_code}')
            check('benar dinilai benar', body.get('is_correct') is True)
            check('pembahasan ikut di balasan jawaban',
                  body.get('explanation') == 'Penjelasan resmi guru.')
            check('counter diagnostik ikut', body.get('diagnostic_answered') == 1,
                  f"answered={body.get('diagnostic_answered')}")
            check('baris tersimpan sebagai bukti',
                  PracticeAnswer.query.filter_by(
                      student_id=student.id,
                      bank_question_id=ready_diag[0].id).count() == 1)

            stats = spractice.diagnostic_stats(student.id, ready.id)
            check('diagnostic_stats memisahkan dari latihan',
                  stats.get(sec_diag.id, {}).get('answered') == 1
                  and stats.get(sec_practice.id) is None, f"{stats}")

        finally:
            drop_fixture()

        total = len(results)
        passed = sum(1 for _n, ok, _e in results if ok)
        print('\n' + '=' * 68)
        print(f'TOTAL: {total}  PASS: {passed}  FAIL: {total - passed}')
        failed = [n for n, ok, _e in results if not ok]
        if failed:
            print('GAGAL:')
            for n in failed:
                print(f'  - {n}')
        print('=' * 68)
        return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
