# ============================================================
# Smoke test - storage architecture (Test 1-9 from the audit).
# Runs against the app in-process so it works with STORAGE_PROVIDER
# = local OR r2. Verifies upload -> storage, metadata in MySQL,
# authenticated proxy, presigned serialization, delete cleanup,
# ownership checks, and that nothing lands in Git.
#
# Run:  .venv/Scripts/python.exe smoke_storage.py
# ============================================================
import io
import os
import sys

from src import create_app
from src.config.database import db
from src.services import storage_service

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('[PASS] ' if cond else '[FAIL] ') + name + (f' | {detail}' if detail and not cond else ''))


def make_pdf_bytes():
    return b'%PDF-1.4\n%e-bio-x-smoke-test\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n'


def login(client, email):
    r = client.post('/api/login', json={'email': email, 'password': '123123123'})
    assert r.status_code == 200, f'login {email} failed: {r.status_code}'
    return {'Authorization': f"Bearer {r.get_json()['access_token']}"}


app = create_app()
with app.app_context():
    provider = storage_service.active_provider()
    print(f'provider aktif: {provider}')
    client = app.test_client()
    guru = login(client, 'guru1@ebiox.com')
    murid = login(client, 'murid1@ebiox.com')
    other = None
    for em in ('guru@ebiox.com', 'guru2test@ebiox.com'):
        try:
            other = login(client, em)
            break
        except AssertionError:
            continue

    pdf = make_pdf_bytes()

    # ---- Test 1: guru upload PDF -> storage + metadata MySQL ----
    r = client.post('/api/materials', data={
        'title': '__SMOKE_STORAGE__', 'content': 'smoke', 'course_id': '6', 'file': (io.BytesIO(pdf), 'smoke.pdf'),
    }, headers=guru, content_type='multipart/form-data')
    check('T1 upload PDF -> 201', r.status_code == 201, f'{r.status_code} {r.get_data(as_text=True)[:200]}')
    mat = r.get_json()['material']
    mid = mat['id']
    # canonical value lives in MySQL; API responses carry presigned/signed urls
    stored_url = db.session.execute(
        db.text(f'SELECT file_url FROM materials WHERE id = {mid}')).scalar()
    key = storage_service.resolve_key(stored_url)
    check('T1 url portabel /api/files/', '/api/files/' in stored_url and not stored_url.startswith('http'), stored_url[:80])
    if provider == 'supabase':
        check('T1 respons FE berisi signed URL', '/object/sign/' in mat['file_url'] and 'token=' in mat['file_url'], mat['file_url'][:80])
    check('T1 objek ada di storage', storage_service.exists(key), str(key))

    # ---- Test 2: serializer tetap menyajikan file (presigned/proxy) ----
    r = client.get(f'/api/materials/{mid}', headers=murid)
    check('T2 refresh halaman: detail materi OK', r.status_code == 200)
    check('T2 url serialisasi non-kosong', bool(r.get_json().get('file_url')))

    # ---- Test 3 & 4: stateless provider - konteks baru tetap ketemu ----
    with app.test_request_context():
        check('T3/T4 baca ulang dari storage (restart/deploy-proof)', storage_service.get_bytes(key) == pdf)

    # ---- proxy endpoint ----
    r = client.get(stored_url.replace('/api/files/', '/api/files/').replace('//', '/'), headers=murid)
    rp = client.get('/api/files/' + key, headers=murid)
    check('Proxy: murid terdaftar bisa unduh', rp.status_code == 200 and rp.data == pdf, str(rp.status_code))
    rn = client.get('/api/files/e-bio-x/materials/teacher/71/tidak-ada-xyz.pdf', headers=murid)
    check('Proxy: key tak dikenal -> 403 ditolak (anti-enumerasi)', rn.status_code == 403, str(rn.status_code))
    ra = client.get('/api/files/' + key)  # tanpa JWT
    check('Proxy: tanpa JWT ditolak', ra.status_code in (401, 422), str(ra.status_code))

    # ---- Test 5: upload kedua tidak mengubah git ----
    r2_ = client.post('/api/materials', data={
        'title': '__SMOKE_STORAGE_2__', 'content': 'smoke', 'course_id': '6',
        'file': (io.BytesIO(make_pdf_bytes()), 'smoke2.pdf'),
    }, headers=guru, content_type='multipart/form-data')
    mid2 = r2_.get_json()['material']['id']
    import subprocess

    def _git_upload_leaks():
        out = subprocess.run(['git', 'status', '--porcelain', '--', 'uploads'],
                             capture_output=True, text=True).stdout
        # ignore staged deletions of legacy tracked files (expected until committed)
        return '\n'.join(l for l in out.splitlines() if not l.startswith('D ')).strip()

    dirty = _git_upload_leaks()
    check('T5 git uploads/ bersih setelah 2 upload', dirty == '', dirty or '(kosong)')

    # ---- Test 7: ganti file via files endpoint; lama dibersihkan ----
    r = client.post(f'/api/materials/{mid}/files',
                    data={'file': (io.BytesIO(make_pdf_bytes()), 'ganti.pdf')},
                    headers=guru, content_type='multipart/form-data')
    check('T7 upload pengganti -> 201', r.status_code == 201, str(r.status_code))
    new_file = r.get_json()['file']
    new_stored = db.session.execute(
        db.text(f"SELECT file_url FROM material_files WHERE id = {new_file['id']}")).scalar()
    old_key, new_key = key, storage_service.resolve_key(new_stored)
    check('T7 objek baru ada', storage_service.exists(new_key))

    # ---- Test 8: guru lain / siswa tak bisa hapus-hapus milik orang ----
    if other:
        r = client.delete(f'/api/materials/{mid}', headers=other)
        check('T8 guru lain hapus materi -> 403', r.status_code == 403, str(r.status_code))
        r = client.delete(f"/api/materials/{mid}/files/{new_file['id']}", headers=other)
        check('T8 guru lain hapus file -> 403', r.status_code == 403, str(r.status_code))

    # ---- Test 6: hapus file & material -> storage + metadata bersih ----
    r = client.delete(f'/api/materials/{mid}', headers=guru)
    check('T6 hapus materi pemilik -> 200', r.status_code == 200, str(r.status_code))
    check('T6 objek utama terhapus dari storage', not storage_service.exists(old_key))
    check('T6 metadata MySQL terhapus',
          db.session.execute(db.text(f'SELECT COUNT(*) FROM materials WHERE id={mid}')).scalar() == 0)
    r = client.delete(f'/api/materials/{mid2}', headers=guru)
    check('T6b hapus materi ke-2 -> 200', r.status_code == 200, str(r.status_code))

    # ---- Test 9: repo tetap bersih di akhir ----
    dirty = _git_upload_leaks()
    check('T9 git uploads/ bersih di akhir', dirty == '', dirty or '(kosong)')

print('\n===== SUMMARY =====')
print(f'TOTAL: {len(PASS) + len(FAIL)}  PASS: {len(PASS)}  FAIL: {len(FAIL)}')
sys.exit(1 if FAIL else 0)
