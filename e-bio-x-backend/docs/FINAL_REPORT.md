# E-Bio X — Laporan Audit, Integrasi, dan Finalisasi (Prompt 6)

Dokumen ini merangkum hasil audit menyeluruh tahap akhir: konsistensi arsitektur,
penegakan otorisasi peran (admin/guru/siswa) di backend, perbaikan bug,
validasi input, integritas data, serta hasil pengujian untuk keperluan
demo, penelitian, dan pengembangan selanjutnya.

---

## 1. Arsitektur & Konsistensi

- Backend: **Flask** (`e-bio-x-backend`, `src/`) dengan struktur controller/`,
  `models/`, `services/`, `ml/`, `config/database.py`. Skema dikelola via
  Flask-Migrate/Alembic di `migrations/`.
- Frontend: **Nuxt 3** (`e-bio-x-frontend`) dengan `app/pages`, `components/`,
  `layouts/`, `middleware/`, `utils/`, `assets/css/main.css`.
  Versi kunci: nuxt 3.17.5, @nuxt/ui 3, chart.js, sweetalert2, nuxt-toast, google signin.
- DB: **MySQL** `e_bio`. Koneksi & secret via `.env` (tidak ikut ter-commit;
  `.env.example` selalu sinkron).
- Autentikasi: JWT (`Flask-JWT-Extended`) — access 3 jam; token dikirim frontend
  melalui header `Authorization: Bearer <token>`; middleware `auth.js`/`guest.js`
  mengarahkan akses tanpa token ke `/login` dan peran salah ke `/forbidden`.
- Login email+password (hash werkzeug) dan **Google OAuth** (verifikasi `id_token`
  dengan `GOOGLE_CLIENT_ID`). Akun Google tanpa password: set password pertama
  diperbolehkan tanpa memerlukan password lama.

### Konsistensi respons
- Seluruh endpoint error memakai bentuk `{"error": "<pesan>"}` (kode 4xx/5xx) atau
  `{"message": "<pesan>"}` untuk kesuksesan. Perbaikan besar: **sendokkan
  `jsonify({'message': ...}, 200)` yang salah** di `analyze_quiz` (argumen `200`
  tadinya ikut diserialisasi menjadi key JSON `"200"`) diganti `return jsonify(...), 200`.
- Tidak ada data tiruan / angka fabrikasi di dashboard, analitik, maupun ML.
  Pipeline ML melaporkan `INSUFFICIENT_DATA` secara jujur ketika dataset tidak
  mencukupi.
  > **Status sudah berubah sejak laporan ini ditulis.** Saat audit awal
  > `ml_models` memang kosong karena sampel riil di bawah ambang. Sekarang
  > data aktivitas siswa sudah memadai dan model **sudah dilatih per kelas**
  > (lihat `docs/ML_DOCUMENTATION.md` §7). Baris di bawah adalah catatan
  > keadaan waktu audit, bukan keadaan sekarang.

---

## 2. Audit Basis Data (Bagian A)

Hasil pemeriksaan konsistensi:
- Users 79 (1 admin, 3 guru, 75 siswa); enrollments 98; tidak ada duplikat enrollment.
- Tidak ada `material_progress`, `StudentAnswer`, maupun `answers` duplikat/ber-orphan.
- 2 materi (published), 9 kuis (6 draft, 3 published), 1 profil pembelajaran,
  1 rekomendasi, 4 learning sessions, 1 students answer interaktif.
- `ml_models` kosong **pada waktu audit** (model artifact belum di-train) —
  konsisten dengan status INSUFFICIENT_DATA saat itu; tanpa fabrikasi.
  Sekarang sudah terisi: satu model per kelas guru.

> Catatan: tabel `student_learning_profiles` **tidak memiliki kolom `status`**;
> kolom aktual mengikuti model Tahap 5 (mis. `prediction_status`). Ini informasi
> kolom, bukan bug kode.

---

## 3. Otorisasi Backend (Bagian B–C, wajib diterapkan)

Matriks kontrol akses yang kini berlaku:

| Area | Endpoint | Role yang diizinkan |
|---|---|---|
| Users | `GET/POST/DELETE/PUT /api/users*` | **admin** saja (sebelumnya siapa pun login) |
| Users | `PUT /api/user/me` | pemilik akun |
| Course | `POST /api/courses` | guru/admin |
| Course | `GET /api/courses` | admin/guru |
| Course | `GET /api/courses/<id>` | owner + siswa ter-enroll |
| Course | `DELETE /api/courses/<id>` | owner/admin |
| Course | `enroll/out` | **siswa** saja |
| Course | `kick` | owner/admin |
| Material | create/update/delete/publish/sections/content | guru (owner) / admin |
| Material | `GET detail` | siswa ter-enroll (tanpa kunci jawaban) |
| Material | `submit answer` / tracking | siswa, materi milik kelasnya |
| Quiz (legacy) | create/toggle/edit/delete | guru owner / admin |
| Quiz (legacy) | `GET /api/quiz/<id>` | owner (guru) / siswa ter-enroll (kunci disembunyikan) |
| Quiz (legacy) | submit/remove submission | siswa (jawaban divalidasi milik kuis) |
| Quiz (student) | start/save/submit/result attempt | siswa ter-enroll/berhak |
| Analysis | `POST/GET /api/analysis/<quiz_id>` | guru owner / admin |
| Discussion | thread/reply CRUD | anggota kelas; hapus: penulis/guru/admin; pin: guru |
| Analytics | `/api/teacher/analytics*` | guru/admin (scoped per guru) |
| ML | train/predict/insights | guru/admin |

Poin penting:
- Ketika siswa melihat detail materi, `correct answer` **tidak lagi bocor**
  (`include_answers` hanya untuk admin/owner materi).
- Jawaban kuis dinilai **di server** (`_grade_submission`) dari opsi yang memang
  milik soal, sehingga klien tidak dapat menempel skor.
- Waktu belajar dihitung **di server** (mulai `started_at` s.d. `last_seen_at`
  dengan batas idle 5 menit) — bukan angka yang dikirim klien.

---

## 4. Perbaikan Bug yang Ditemukan & Diterapkan

1. `user_controller`
   - `get_all_users`, `create_user`, `delete_user`, `update_user` di-restrict ke admin.
   - `update_user_me`: `get_json(silent=True)`; kombinasi ubah nama + password didukung;
     ganti password akun ber-password **wajib** `current_password` yang benar;
     akun Google (tanpa password) diizinkan set password pertama.
   - Validasi email/name/role saat create/update (cegah KeyError/role custom).
2. `course_controller`
   - `create_course`/`get_courses` di-restrict (guru/admin).
   - `enroll`/`out` hanya untuk siswa.
   - `delete_course` — hilang `return` pada respons error (perilaku tak tentu) diperbaiki;
     ditambah status 500 + `except Exception`; ownership check.
   - `get_course_by_id` — `return` yang hilang pada 404 diperbaiki; siswa harus
     ter-enroll; guru harus owner/admin; data `quizes` siswa lain tidak dikirim ke siswa.
3. `material_controller`
   - `get_material_by_id` memakai variabel `include_analytics` yang **tidak terdefinisi**
     (NameError → 500): diperbaiki mengikuti `include_answers`.
   - `get_material_by_course` — kini access-controlled (siswa wajib enroll, guru owner).
   - `_create_material_form` — kini cek role guru + ownership kelas (sebelumnya kosong).
   - `submit_student_answer` — `int(...)` di-guard (bad input → 400, bukan 500).
   - Upload file: alur `_save_uploaded_file` **memverifikasi magic bytes**
     (`%PDF`, PNG/JPEG/WEBP/MP4) lalu `seek(0)` — ekstensi kanan tidak bisa
     disalahgunakan; kesesuaian isi vs ekstensi diuji.
4. `quiz_controller`
   - Legacy `create_quiz`, `toggle_open_quiz`, `edit_quiz_title`, `edit_question`,
     `edit_option`, `delete_quiz` kini guru owner/admin; ownership terhadap course.
   - `submit_quiz` — hanya siswa; opsi/soal divalidasi milik kuis (cegah skor tiruan);
     duplicate submission tetap ditolak.
   - `get_submission_by_quiz` — guru owner/admin saja.
   - `get_my_submission_by_id` — hanya submission milik sendiri.
   - `get_quizzes_by_course` — siswa wajib ter-enroll, guru owner.
   - `get_quiz_by_id` — siswa ter-enroll (kunci jawaban disembunyikan), guru owner.
   - `get_student_quizzes` / `save_student_answer` — `int()` di-guard.
5. `analysis_controller`
   - `analyze_quiz`: argumen `200` pada `jsonify` (bug respons JSON) dikoreksi;
     role/ownership teacher/admin ditambahkan.
   - `get_analyze`: guard role + respons halus saat belum ada data nilai.
   - `statistics`: `min/max` work-time tak crash saat `work_time` None.
6. `discussion_controller` — admin kini dapat melihat & menghapus thread/reply.
7. `learning_tracking_controller` — `int()`/`float()` di-guard; nilai negatif
   progress video ditolak 400; `content_id`/`section_id` asing → 404.
8. WhatsApp keamanan upload: `MAX_CONTENT_LENGTH` 50MB; ekstensi dibatasi
   `{pdf,jpg,jpeg,png,webp,mp4}` (40MB/file); CORS dibatasi ke `FRONTEND_URL`.

Semua perubahan bersifat **backward-compatible** dengan halaman frontend yang ada
(QizList memakai `/api/quiz/*` masih berfungsi untuk guru+siswa ter-enroll,
halaman analisis guru tetap memakai `POST|GET /api/analysis/<id>`).

---

## 5. Integrasi & Konsistensi UI

- `NavBar.vue` menampilkan menu sesuai role; halaman `forbidden.vue` untuk akses
  tak sah; middleware Nuxt menegakkan layout admin/landing.
- Semua halaman memanggil API dari `config.public.backend` dengan header Bearer.
- Tidak ditemukan rendering `v-html` pada konten buatan pengguna (aman dari XSS
  terkait konten postingan diskusi); satu-satunya `v-html` di `AdminTable.vue`
  adalah renderer sel internal untuk tabel admin.
- Tidak ada tombol/label yang memakai angka sink yang didistorsi; statistik di
  dashboard & teacher analytics dihitung ulang dari DB.

---

## 6. Pengujian

Dijalankan di lingkungan dev (server `http://127.0.0.1:5000`, MySQL `e_bio`):

| Suite | Cakupan | Hasil |
|---|---|---|
| `test_ml_unit.py` | Unit ML offline (DT, K-Means, rekomendasi, penyimpanan/versi model) | **32/32 PASS** |
| `test_ml_leakage.py` | Anti-leakage label, penjelasan, distribusi kelas | **45/45 PASS** |
| `test_ml_difficulty.py` | Metadata tingkat kesulitan, imputasi & normalisasi | **66/66 PASS** |
| `test_ml_rec_eval.py` | API evaluasi closed-loop rekomendasi (read-only, otorisasi) | **48/48 PASS** |
| `test_ml_scope.py` | Scoping model per kelas, versi, akses materi antar kelas | **95/95 PASS** |
| **Total komponen ML** | | **286/286 PASS** |
| `test_section_tagging.py` | Fase 1 — penandaan bagian pada soal (`questions.section_id`) | **24/24 PASS** |
| `test_section_mastery.py` | Fase 2, 4 & 5 — diagnosis penguasaan per bagian + saran prasyarat (advisory) + peta siswa × bagian (ambang minimum, fallback kuis-section, invarian sel grid, scoping) | **50/50 PASS** |
| `test_practice_drafts.py` | Fase 3a–3c — soal latihan per bagian (tautan bagian, draf AI, persetujuan guru, tanpa fallback karangan) | **80/80 PASS** |
| `test_student_practice.py` | Fase 3d — latihan siswa (hanya soal APPROVED, kunci tidak bocor, penilaian di server, sumber terpisah di diagnosis) | **73/73 PASS** |
| `scripts/tag_demo_quiz_sections.py` | Data demo — menautkan 26 soal kuis demo ke bagian materi (eksplisit, 4 soal ambigu dibiarkan `NULL`, idempoten) | **26 soal, 0 masalah** |
| `scripts/fix_demo_section_interactive.py` | Data demo — memindahkan soal interaktif + jawabannya ke bagian yang cocok (tanpa angka baru, invarian `is_correct` 590/590) | **590/590 konsisten** |
| `scripts/verify_ml_readiness.py` | Gate pra-demo: kelengkapan data, model per kelas, scoping guru, integritas klaim & soal kuis, atribusi jawaban kuis ke bagian | **60/60 PASS** |

`test_tahap4.py` dan `test_tahap5_ml.py` adalah suite API end-to-end yang
memerlukan server hidup; regresi Tahap 1–4 juga dicakup ulang oleh
`test_ml_scope.py` dan `test_ml_rec_eval.py` di atas.

Catatan `test_tahap4.py`: 1 pemeriksaan gagal pada data demo saat ini —
`student detail outside teacher course 403` — karena seluruh 76 siswa demo terdaftar di
kelas Guru 1, sehingga tidak ada siswa di luar cakupan guru itu untuk memicu 403 (probe
dinamis berakhir dengan 404 "siswa tidak ditemukan"). Ini kondisi data, bukan regresi kode:
endpoint `/api/teacher/analytics/students/<id>` tidak berubah di Fase 2.

Smoke khusus keamanan (live) juga dicek: siswa terhadap `/api/users` → 403,
siswa membuat course → 403, siswa enroll/out ke kelas → memerlukan role siswa,
guru non-owner terhadap materi/kuis/analisis → 403.

---

## 7. Keamanan (Ringkasan)

- JWT SECRET dari env; token access 3 jam (tanpa refresh endpoint; klien login ulang).
- Peran **dipaksa di backend** untuk seluruh modul (tabel 3). Middleware frontend
  hanya UI-hint; titik tegas ada di controller.
- Input selalu divalidasi tipe & kepemilikan (400/403/404, bukan 500).
- Upload: ekstensi whitelist + verifikasi signature; `secure_filename` untuk nama file.
- Tidak ada secret hardcoded; `.env` di-ignore.

---

## 8. Keterbatasan / Catatan Lanjutan

- Model ML **sudah dilatih per kelas** dari data aktivitas yang tersedia:
  Decision Tree (klasifikasi penguasaan) dan K-Means (pengelompokan) dilatih
  terpisah untuk tiap guru, dievaluasi dengan repeated stratified CV + baseline
  mayoritas (lihat `docs/ML_DOCUMENTATION.md`). Kelas yang datanya di bawah
  ambang tetap melaporkan `INSUFFICIENT_DATA` secara jujur (mis. guru tanpa
  siswa). Retrain kapan saja via `POST /api/ml/train` (guru/admin).
- Peringkat materi pada rekomendasi dihitung oleh aturan transparan
  (`REC_WEIGHTS`), **bukan** oleh model terlatih; karena itu rekamannya
  bertipe `rule` dan tidak distempel versi model. Decision Tree memberi label
  profil, K-Means memberi klaster — dua hal terpisah dari urutan rekomendasi.
- Evaluasi closed-loop rekomendasi (funnel/calibration/completion_yield) sudah
  tersedia sebagai endpoint tetapi **belum punya data klik/penyelesaian**,
  sehingga bucket-nya `INSUFFICIENT_DATA` sampai siswa benar-benar memakai
  rekomendasi; ini observasional, bukan bukti kausal.
- Color label klaster analisis kuis lama hardcoded di frontend (3 warna) — sesuai
  jumlah klaster default.
- Fitur "bagian materi" sudah sampai Fase 3d. Ambang minimum 3 jawaban per bagian
  sengaja tidak bisa dikarang, sehingga bagian dengan data sedikit tampil
  `INSUFFICIENT_DATA`, bukan angka. Latihan per bagian memakai soal bank yang ditautkan
  eksplisit ke bagian; draf AI **wajib** disetujui guru sebelum bisa dipakai, dan modul
  draf tidak punya fallback rule-based — tanpa `AI_API_KEY` atau saat penyedia AI sibuk
  (HTTP 503), sistem menolak dengan pesan jujur, bukan soal karangan. Pelajar latihan
  untuk siswa sudah ada dan hanya menyajikan soal `APPROVED`; kunci jawaban tidak pernah
  ikut pada respons pemuatan dan penilaiannya dilakukan di server. Jawaban latihan
  masuk ke diagnosis sebagai **sumber terpisah** (`practice_answered`/`practice_correct`,
  beserta `score_sources` yang terbuka), dihitung dari jawaban **terakhir** per soal
  supaya mengulang tidak menggelembungkan angka. Rekomendasi per bagian, gating adaptif,
  dan peta panas siswa × bagian untuk guru belum dikerjakan (lihat
  `docs/FEATURE_BAGIAN_MASTERY.md`).
  Konsekuensi yang perlu diketahui: karena bobot latihan ikut masuk, soal latihan yang
  jauh lebih mudah akan menaikkan skor penguasaan; rincian per sumber selalu ditampilkan
  supaya angka itu bisa dinilai.
- `SECRET_KEY` dev bernilai placeholder — ganti nilai produksi sebelum rilis.

---

## 9. Status Akhir

- Semua Tile Prompt 1–5 terverifikasi terintegrasi; Prompt 6 (audit, security,
  polish, testing) tuntas; seluruh suite hijau.
- Perubahan audit ter-commit dan ter-push (lihat log git).
- Sistem siap digunakan untuk demo, uji coba kelas, maupun pengumpulan data
  penelitian lanjutan (fitur ML siap dilatih dengan data baru).