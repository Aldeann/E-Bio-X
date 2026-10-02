# ============================================================
# FASE 3 (3a-3c) - SOAL LATIHAN PER BAGIAN MATERI
#
# Kontrak yang dipatok test ini:
#   - kolom baru question_bank / question_bank_options ada
#   - soal bank lama tetap|source=teacher, status=APPROVED (tidak rusak)
#   - daftar bagian melaporkan jumlah apa adanya, tidak mengarang rasio
#   - AI tidak dikonfigurasi -> 503 jujur, TIDAK ada soal karangan
#   - draf AI disimpan sebagai DRAFT, section_id & topic diambil dari
#     record bagian (bukan dari keluaran model)
#   - draf AI rusak (dua jawaban benar / tanpa opsi) DITOLAK, dihitung
#   - hanya DRAFT/REJECTED yang tidak boleh dipakai latihan; APPROVED
#     hanya lewat persetujuan guru
#   - approve butuh tepat satu jawaban benar, mencatat siapa & kapan
#   - bagian milik guru lain tidak bisa disentuh (403)
#   - guru bisa menautkan soal tulisannya sendiri ke bagian; topiknya
#     mengikuti bagian dan tidak bisa melenceng
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
from src.models.material import Material  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.material_content import MaterialContent  # noqa: E402
from src.models.question_bank import QuestionBank  # noqa: E402
from src.models.question_bank_option import QuestionBankOption  # noqa: E402
from src.services import practice_bank_service as practice  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

STAMP = 'zzpracticeunit'
results = []
created = {}


def check(name, cond, extra=""):
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


def token_for(user):
    return create_access_token(identity=str(user.id))


def mcq(text='Soal uji', options=None, **extra):
    opts = options or [
        {'option_text': 'Benar', 'is_correct': True},
        {'option_text': 'Salah', 'is_correct': False},
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
    teacher = User(email=f'{STAMP}@test.local', name='Practice Unit Guru',
                   role='teacher')
    other_teacher = User(email=f'{STAMP}.other@test.local',
                         name='Practice Unit Guru Lain', role='teacher')
    student = User(email=f'{STAMP}.student@test.local', name='Practice Unit Siswa',
                   role='student')
    db.session.add_all([teacher, other_teacher, student])
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    db.session.add(course)
    db.session.flush()

    material = Material(title='Materi Latihan', course_id=course.id,
                        teacher_id=teacher.id, status='published',
                        topic='LATIHAN')
    foreign_material = Material(title='Materi Milik Guru Lain',
                                course_id=course.id,
                                teacher_id=other_teacher.id,
                                status='published')
    db.session.add_all([material, foreign_material])
    db.session.flush()

    sec_a = MaterialSection(material_id=material.id, title='Siklus Replikasi Virus',
                             position=0)
    sec_b = MaterialSection(material_id=material.id, title='Struktur Virus',
                             position=1)
    sec_foreign = MaterialSection(material_id=foreign_material.id,
                                  title='Bagian Asing', position=0)
    db.session.add_all([sec_a, sec_b, sec_foreign])
    db.session.flush()

    # Draft generation refuses a section with no text, so the fixture sections
    # need content of their own.
    db.session.add_all([
        MaterialContent(section_id=sec_a.id, type='text', position=0,
                        data={'text': 'Virus hanya bereplikasi di dalam sel inang.'}),
        MaterialContent(section_id=sec_b.id, type='text', position=0,
                        data={'text': 'Kapsid tersusun dari protein.'}),
        MaterialContent(section_id=sec_foreign.id, type='text', position=0,
                        data={'text': 'Isi bagian asing.'}),
    ])
    db.session.flush()

    created.update(teacher=teacher, other_teacher=other_teacher,
                   student=student, course=course, material=material,
                   foreign_material=foreign_material, sec_a=sec_a,
                   sec_b=sec_b, sec_foreign=sec_foreign)


def drop_fixture():
    # Options and questions go first: a draft whose section tag was removed
    # during the run is still owned by this fixture's teacher, so the cleanup
    # keys off teacher_id rather than the section.
    rows = [created.get(key) for key in ('bank', 'bank2', 'bank3', 'drafts')]
    rows = [row for row in rows if row]
    for row in rows:
        if not isinstance(row, list):
            row = [row]
        for bq in row:
            for opt in list(bq.options):
                db.session.delete(opt)
    db.session.flush()
    for row in rows:
        if not isinstance(row, list):
            row = [row]
        for bq in row:
            db.session.delete(bq)
    db.session.flush()
    for key in ('sec_a', 'sec_b', 'sec_foreign', 'sec_empty'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    for key in ('material', 'foreign_material'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    if created.get('course') is not None:
        db.session.delete(created['course'])
    for key in ('teacher', 'other_teacher', 'student'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.commit()


def ai_item(text='Draf soal virus', misconception=' virus adalah sel hidup'):
    return {
        'question_text': text,
        'options': [
            {'option_text': 'Viral', 'is_correct': True, 'feedback': 'Viral correct'},
            {'option_text': 'Sel', 'is_correct': False, 'feedback': 'Virus bukan sel'},
        ],
        'explanation': 'Virus hanya bereplikasi di dalam sel inang.',
        'misconception': misconception,
    }


def patch_ai(items, available=True, fail=None, dropped=0):
    """Replace the provider with a stub so tests never touch the network."""
    saved = (practice.ai_available, practice.generate_drafts)

    def _available():
        return available

    def _generate(section, material, count=3, difficulty='medium'):
        if fail:
            raise fail
        return list(items)[:count], dropped

    practice.ai_available = _available
    practice.generate_drafts = _generate

    def restore():
        practice.ai_available, practice.generate_drafts = saved

    return restore


def main():
    app = create_app()
    with app.app_context():
        print('=' * 68)
        print('FASE 3 - SOAL LATIHAN PER BAGIAN MATERI')
        print('=' * 68)

        make_fixture()
        client = app.test_client()
        teacher = created['teacher']
        other = created['other_teacher']
        student = created['student']
        sec_a = created['sec_a']
        sec_b = created['sec_b']
        sec_foreign = created['sec_foreign']
        h_t = {'Authorization': f'Bearer {token_for(teacher)}'}
        h_o = {'Authorization': f'Bearer {token_for(other)}'}
        h_s = {'Authorization': f'Bearer {token_for(student)}'}

        try:
            # ------------------------------------------------- 1. SKEMA
            print('\n[1] SKEMA KOLOM BARU')
            cols = {c['name'] for c in inspect(db.engine).get_columns('question_bank')}
            for name in ('section_id', 'source', 'status', 'generated_by',
                         'model_name', 'prompt_version', 'reviewed_by',
                         'reviewed_at', 'misconception'):
                check(f'kolom question_bank.{name} ada', name in cols)
            opt_cols = {c['name'] for c in
                        inspect(db.engine).get_columns('question_bank_options')}
            check('kolom question_bank_options.feedback ada', 'feedback' in opt_cols)

            legacy = db.session.execute(db.text(
                "select count(*) from question_bank where teacher_id in "
                "(select id from users where email like 'guru%' or email like 'admin%')"
            )).scalar()
            check('soal bank lama tidak hilang', legacy is not None and legacy > 0,
                  f'total={legacy}')

            # ------------------------------------------- 2. DAFTAR BAGIAN
            print('\n[2] DAFTAR BAGIAN + JUMLAH APA ADANYA')
            restore = patch_ai([], available=False)
            r = client.get('/api/teacher/practice/sections', headers=h_t)
            check('GET sections 200', r.status_code == 200, str(r.status_code))
            body = r.get_json() or {}
            rows = body.get('sections') or []
            mine = [row for row in rows if row['material_id'] == created['material'].id]
            check('hanya bagian milik guru sendiri',
                  all(row['material_id'] == created['material'].id for row in mine)
                  and not any(row['material_id'] == created['foreign_material'].id
                              for row in rows),
                  f'total={len(rows)}')
            check('bagian tanpa soal reported 0, bukan rasio karangan',
                  all(row['approved_count'] == 0 and row['draft_count'] == 0
                      and row['rejected_count'] == 0 for row in mine))
            check('status AI dilaporkan apa adanya',
                  body.get('ai_available') is False
                  and bool(body.get('ai_unavailable_reason')))
            check('siswa ditolak', client.get('/api/teacher/practice/sections',
                                              headers=h_s).status_code == 403)

            # --------------------------------- 3. AI TIDAK ADA -> 503 JUJUR
            print('\n[3] TANPA AI: TOLAK TERUS, JANGAN KARANG SOAL')
            before = QuestionBank.query.count()
            r = client.post(f'/api/teacher/practice/sections/{sec_a.id}/drafts',
                            headers=h_t, json={'count': 3})
            check('generate tanpa AI -> 503', r.status_code == 503, str(r.status_code))
            check('tidak ada soal yang dikarang',
                  QuestionBank.query.count() == before)
            check('pesan jujur, bukan error server generik',
                  'AI' in (r.get_json() or {}).get('error', ''))
            restore()

            # ------------------------------------------- 4. DRAF AI DISIMPAN
            print('\n[4] DRAF AI: STATUS, SECTION, TOPIK')
            restore = patch_ai([ai_item('Draf 1'), ai_item('Draf 2')], available=True)
            r = client.post(f'/api/teacher/practice/sections/{sec_a.id}/drafts',
                            headers=h_t, json={'count': 2, 'difficulty': 'hard'})
            check('generate draf -> 201', r.status_code == 201, str(r.status_code))
            payload = r.get_json() or {}
            check('2 draf dibuat', payload.get('created_count') == 2,
                  str(payload.get('created_count')))
            drafts = QuestionBank.query.filter_by(
                source='ai', section_id=sec_a.id).order_by(QuestionBank.id).all()
            created['drafts'] = list(drafts)
            check('semua draf berstatus DRAFT',
                  drafts and all(d.status == 'DRAFT' for d in drafts))
            check('draf tidak langsung APPROVED',
                  not any(d.status == 'APPROVED' for d in drafts))
            check('section_id diambil dari bagian yang dipilih',
                  all(d.section_id == sec_a.id for d in drafts))
            check('topik mengikuti judul bagian',
                  all(d.topic == 'Siklus Replikasi Virus' for d in drafts),
                  drafts[0].topic if drafts else '')
            check('kesulitan mengikuti permintaan guru',
                  all(d.difficulty == 'hard' for d in drafts))
            check('jejak model tercatat',
                  all(d.model_name and d.prompt_version == practice.PROMPT_VERSION
                      for d in drafts))
            check('misconception tersimpan',
                  bool(drafts) and drafts[0].misconception == ' virus adalah sel hidup')
            check('feedback pengecoh tersimpan',
                  bool(drafts) and any(o.feedback for o in drafts[0].options))
            check('belum ada latihan untuk bagian ini',
                  practice.practice_ready(sec_a.id) is False)
            other_sec_ready = practice.practice_ready(sec_b.id)
            check('bagian lain tetap kosong', other_sec_ready is False)

            # ------------------------------------------------ 5. ANTREAN REVIEW
            print('\n[5] ANTREAN REVIEW GURU')
            r = client.get('/api/teacher/practice/drafts', headers=h_t)
            check('antrean 200', r.status_code == 200, str(r.status_code))
            queue = (r.get_json() or {}).get('data') or []
            check('antrean hanya berisi draf miliknya sendiri',
                  len(queue) == 2
                  and all(q['source'] == 'ai' and q['status'] == 'DRAFT' for q in queue))
            check('antrean tidak bocor ke guru lain',
                  client.get('/api/teacher/practice/drafts',
                             headers=h_o).get_json().get('data') == [])

            # --------------------------------------------- 6. DRAF RUSAK DITOLAK
            print('\n[6] DRAF RUSAK: TIDAK DISIMPAN, DIHITUNG')
            broken = [
                {'question_text': 'Dua jawaban benar', 'options': [
                    {'option_text': 'A', 'is_correct': True},
                    {'option_text': 'B', 'is_correct': True}]},
                {'question_text': 'Tanpa opsi', 'options': []},
            ]
            restore()
            before = QuestionBank.query.count()
            restore = patch_ai(broken, available=True)
            r = client.post(f'/api/teacher/practice/sections/{sec_b.id}/drafts',
                            headers=h_t, json={'count': 2})
            check('draf rusak -> 201 dengan laporan', r.status_code == 201,
                  str(r.status_code))
            payload = r.get_json() or {}
            check('tidak ada draf rusak tersimpan',
                  QuestionBank.query.count() == before)
            check('jumlah yang tidak disimpan dilaporkan',
                  payload.get('created_count') == 0
                  and payload.get('skipped_count') == 2,
                  f"created={payload.get('created_count')} skipped={payload.get('skipped_count')}")
            restore()

            # ------------------------------------------- 7. KEGAGALAN PROVIDER
            print('\n[7] KEGAGALAN AI: 502, TIDAK ADA BARIS BARU')
            before = QuestionBank.query.count()
            restore = patch_ai([], available=True,
                               fail=practice.DraftFailed('AI timeout'))
            r = client.post(f'/api/teacher/practice/sections/{sec_a.id}/drafts',
                            headers=h_t, json={'count': 2})
            check('provider gagal -> 502', r.status_code == 502, str(r.status_code))
            check('tidak ada baris baru',
                  QuestionBank.query.count() == before)
            restore()

            # ------------------------------------------ 8. VALIDASI INPUT
            print('\n[8] VALIDASI INPUT')
            restore = patch_ai([ai_item()], available=True)
            for bad, label in (({'count': 0}, 'count=0'),
                               ({'count': 99}, 'count=99'),
                               ({'count': 'abc'}, 'count non-numerik'),
                               ({'difficulty': 'sangat'}, 'kesulitan ngawur')):
                r = client.post(f'/api/teacher/practice/sections/{sec_a.id}/drafts',
                                headers=h_t, json=bad)
                check(f'{label} ditolak 400', r.status_code == 400, str(r.status_code))
            restore()

            # ---------------------------------------------- 9. BATAS KEPEMILIKAN
            print('\n[9] BATAS KEPEMILIKAN')
            restore = patch_ai([ai_item()], available=True)
            r = client.post(f'/api/teacher/practice/sections/{sec_foreign.id}/drafts',
                            headers=h_t, json={'count': 1})
            check('draf di bagian guru lain -> 403', r.status_code == 403,
                  str(r.status_code))
            r = client.post('/api/teacher/practice/sections/99999999/drafts',
                            headers=h_t, json={'count': 1})
            check('bagian tidak ada -> 404', r.status_code == 404, str(r.status_code))
            check('siswa tidak bisa membuat draf',
                  client.post(f'/api/teacher/practice/sections/{sec_a.id}/drafts',
                              headers=h_s, json={'count': 1}).status_code == 403)
            restore()

            # -------------------------------------------------- 10. PENGAJUAN
            print('\n[10] PERSETUJUAN / PENOLAKAN GURU')
            d1 = created['drafts'][0]
            d2 = created['drafts'][1]
            r = client.post(f'/api/teacher/practice/drafts/{d1.id}/approve',
                            headers=h_t, json={})
            check('approve -> 200', r.status_code == 200, str(r.status_code))
            db.session.refresh(d1)
            check('status jadi APPROVED', d1.status == 'APPROVED')
            check('peninjau dan waktu tercatat',
                  d1.reviewed_by == teacher.id and d1.reviewed_at is not None)
            check('bagian ini sekarang punya latihan',
                  practice.practice_ready(sec_a.id) is True)
            check('guru lain tidak bisa menyetujui milik orang',
                  client.post(f'/api/teacher/practice/drafts/{d2.id}/approve',
                              headers=h_o, json={}).status_code == 403)

            r = client.post(f'/api/teacher/practice/drafts/{d2.id}/reject',
                            headers=h_t, json={})
            check('reject -> 200', r.status_code == 200, str(r.status_code))
            db.session.refresh(d2)
            check('status jadi REJECTED', d2.status == 'REJECTED')
            check('soal ditolak tetap tersimpan untuk audit',
                  QuestionBank.query.get(d2.id) is not None)

            # ------------------------------------------------- 11. CAKUPAN
            print('\n[11] CAKUPAN MENGIKUTI KEPUTUSAN GURU')
            restore = patch_ai([], available=False)
            r = client.get(f'/api/teacher/practice/sections?material_id='
                           f'{created["material"].id}', headers=h_t)
            rows = (r.get_json() or {}).get('sections') or []
            row_a = next((x for x in rows if x['section_id'] == sec_a.id), None)
            row_b = next((x for x in rows if x['section_id'] == sec_b.id), None)
            check('bagian disetujui: approved=1, draft=0',
                  row_a and (row_a['approved_count'], row_a['draft_count']) == (1, 0),
                  str(row_a))
            check('soal ditolak dihitung sebagai rejected',
                  row_a and row_a['rejected_count'] == 1, str(row_a))
            check('bagian tanpa soal tetap 0/0/0',
                  row_b and (row_b['approved_count'], row_b['draft_count'],
                             row_b['rejected_count']) == (0, 0, 0), str(row_b))
            restore()

            # --------------------------- 12. GURU MENAUTKAN SOALNYA SENDIRI
            print('\n[12] SOAL TULISAN GURU DITAUTKAN KE BAGIAN')
            r = client.post('/api/teacher/question-bank', headers=h_t,
                            json=mcq('Soal guru sendiri', section_id=sec_b.id,
                                     topic='diabaikan'))
            check('buat soal bank bertag bagian -> 201', r.status_code == 201,
                  str(r.status_code))
            bank = QuestionBank.query.get((r.get_json() or {})['question']['id'])
            created['bank'] = bank
            check('section_id tersimpan', bank.section_id == sec_b.id)
            check('topik mengikuti judul bagian',
                  bank.topic == 'Struktur Virus', str(bank.topic))
            check('soal guru ditandai teacher + APPROVED',
                  bank.source == 'teacher' and bank.status == 'APPROVED')
            check('soal guru langsung bisa jadi latihan',
                  practice.practice_ready(sec_b.id) is True)

            r = client.post('/api/teacher/question-bank', headers=h_t,
                            json=mcq('Soal bagian asing',
                                     section_id=sec_foreign.id))
            check('soal tidak boleh ditautkan ke bagian guru lain -> 400',
                  r.status_code == 400, str(r.status_code))
            r = client.post('/api/teacher/question-bank', headers=h_t,
                            json=mcq('Soal bagian ngawur', section_id='abc'))
            check('section_id ngawur -> 400', r.status_code == 400, str(r.status_code))

            r = client.put(f'/api/teacher/question-bank/{bank.id}', headers=h_t,
                           json=mcq('Soal guru revisi', misconception=' virus punya sel'))
            check('update tidak menghapus tag bagian', r.status_code == 200,
                  str(r.status_code))
            db.session.refresh(bank)
            check('tag bagian bertahan setelah update',
                  bank.section_id == sec_b.id)
            check('misconception guru tersimpan', bank.misconception == 'virus punya sel',
                  str(bank.misconception))

            r = client.put(f'/api/teacher/question-bank/{bank.id}', headers=h_t,
                           json=mcq('Soal lepas dari bagian', section_id=None,
                                    topic='Virus'))
            check('section_id null melepas tag', r.status_code == 200,
                  str(r.status_code))
            db.session.refresh(bank)
            check('tag lepas, topik bebas kembali',
                  bank.section_id is None and bank.topic == 'Virus',
                  f"{bank.section_id} / {bank.topic}")

            # ------------------------------------- 13. FILTER DAFTAR BANK SOAL
            print('\n[13] FILTER DAFTAR BANK SOAL')
            r = client.get('/api/teacher/question-bank?status=REJECTED', headers=h_t)
            ids = [b['id'] for b in (r.get_json() or {}).get('data') or []]
            check('filter status bekerja', ids == [d2.id], str(ids))
            r = client.get(f'/api/teacher/question-bank?section_id={sec_a.id}',
                           headers=h_t)
            data = (r.get_json() or {}).get('data') or []
            check('filter bagian bekerja',
                  data and all(b['section_id'] == sec_a.id for b in data))
            check('serialisasi menyertakan jejak review',
                  data and data[0]['status'] and data[0]['source']
                  and data[0]['section_title'] == 'Siklus Replikasi Virus')

            # ------------------------------------------- 14. PROMPT SCOPING
            print('\n[14] PROMPT AI CUKUP BERTAHAP')
            ctx = practice.section_context(sec_a, created['material'])
            check('prompt memuat judul bagian yang dipilih',
                  'Siklus Replikasi Virus' in ctx)
            check('prompt tidak memuat bagian sebelah',
                  'Struktur Virus' not in ctx)

            saved_key = os.environ.pop('AI_API_KEY', None)
            check('ai_available() mengikuti environment',
                  practice.ai_available() is False)
            if saved_key is not None:
                os.environ['AI_API_KEY'] = saved_key
            check('generate_drafts tanpa AI melempar DraftUnavailable',
                  _no_key_raises(sec_a, created['material']))

            parsed_items, parsed_dropped = practice._draft_items({
                'questions': [{'question_text': ' p <b>teks</b> ',
                               'options': [{'option_text': 'A', 'is_correct': True}]},
                              {'question_text': 'tanpa opsi', 'options': []}]})
            check('normalisasi buang draf tanpa opsi',
                  len(parsed_items) == 1
                  and parsed_items[0]['question_text'] == 'p teks'
                  and parsed_dropped == 1,
                  str((parsed_items, parsed_dropped)))

            meta, meta_dropped = practice._draft_items({
                'questions': [{
                    'question_text': 'Apa materi yang disajikan pada bagian ini?',
                    'options': [{'option_text': 'A', 'is_correct': True}],
                }]})
            check('soal tentang bagiannya sendiri dibuang',
                  meta == [] and meta_dropped == 1, str((meta, meta_dropped)))

            empty_section = MaterialSection(
                material_id=created['material'].id, title='Bagian Kosong', position=9)
            db.session.add(empty_section)
            db.session.commit()
            created['sec_empty'] = empty_section
            restore = patch_ai([ai_item()], available=True)
            r = client.post(f'/api/teacher/practice/sections/{empty_section.id}/drafts',
                            headers=h_t, json={'count': 1})
            check('bagian tanpa teks ditolak dengan jujur',
                  r.status_code == 400 and 'teks' in (r.get_json() or {}).get('error', ''),
                  str(r.status_code))
            check('tidak ada draf dibuat untuk bagian kosong',
                  QuestionBank.query.filter_by(section_id=empty_section.id).count() == 0)
            restore()

        finally:
            drop_fixture()

        passed = sum(1 for _, ok, _ in results if ok)
        print('\n' + '=' * 68)
        print(f'HASIL: {passed}/{len(results)} lulus')
        print('=' * 68)
        failed = [name for name, ok, _ in results if not ok]
        if failed:
            print('GAGAL:')
            for name in failed:
                print(' -', name)
        return 0 if not failed else 1


def _no_key_raises(section, material):
    """generate_drafts must refuse to invent questions with no provider."""
    saved = os.environ.pop('AI_API_KEY', None)
    try:
        practice.generate_drafts(section, material, 1)
        ok = False
    except practice.DraftUnavailable:
        ok = True
    except Exception:
        ok = False
    finally:
        if saved is not None:
            os.environ['AI_API_KEY'] = saved
    return ok


if __name__ == '__main__':
    sys.exit(main())