# Fitur "Bagian Materi" — dari jawaban salah ke bagian materi, bukan hanya materi

Dokumen ini menjelaskan fitur yang sedang dibangun dalam lima fase. **Fase 1, Fase 2, dan
Fase 3a–3c sudah selesai.** Sisa Fase 3 (pelajar berjalan), Fase 4, dan Fase 5 masih rencana.

**Tujuan akhir:** ketika seorang siswa salah menjawab soal tentang *Struktur Tubuh Virus*,
sistem harus bisa menunjuk bagian materi itu — bukan sekadar "materi VIRUS saja belum dikuasai" —
lalu memberi latihan-latihan dari bank soal pada bagian tersebut, dan akhirnya menampilkan
peta pemahaman siswa × bagian yang bisa dilihat guru.

Fase yang sudah selesai:

| Fase | Isi | Status |
|---|---|---|
| 1 | Penandaan bagian pada soal (`questions.section_id`) | Selesai |
| 2 | Diagnosis penguasaan per bagian (siswa & kelas) | Selesai |
| 3 | Latihan per bagian: soal bank bertag + draf AI + persetujuan guru | 3a–3c selesai |
| 4 | Gating adaptif (kunci/khint bagian berikutnya) | Rencana |
| 5 | Peta pemahaman siswa × bagian untuk guru | Rencana |

---

## 1. Unit "bagian"

Bagian = tabel `material_sections` (sudah ada sebelumnya; satu materi punya beberapa bagian
berurutan lewat `position`). Istilah "bagian" di UI = `MaterialSection`.

Tidak ada tabel baru. Fase 1 hanya menambah satu kolom yang boleh kosong.

---

## 2. Fase 1 — penandaan bagian pada soal

### 2.1 Skema

`questions.section_id` (FK ke `material_sections.id`, **nullable**). `NULL` = belum ditandai.

Migrasi dijalankan otomatis oleh `ensure_schema_compat()` saat `create_app()` (lihat
`_COMPAT_COLUMNS` di `src/config/database.py`), jadi instalasi lama tidak perlu migrasi manual.

### 2.2 Aturan penandaan (tidak menebak)

1. Soal baru di kuis yang punya `section_id` **mewarisi** bagian kuis tersebut.
2. Guru bisa menimpa per soal lewat form "Bagian Materi (opsional)".
3. Bagian dari materi lain **ditolak** (400) — tidak boleh salah tag.
4. `PUT` soal tanpa `section_id` di payload **mempertahankan** tag lama; `section_id: null`
   menghapus tag.
5. Duplikat soal menyalin `section_id`.
6. Aksi massal guru: `PUT /api/teacher/quizzes/<quiz_id>/questions/section`
   → "Terapkan bagian ke semua soal".
7. Soal dari bank soal dipetakan ke bagian **hanya bila** `bank_question.topic` **persis sama**
   dengan judul bagian (normalisasi spasi/kapitalisasi). Selain itu dibiarkan `NULL`.
8. Backfill `scripts/backfill_question_sections.py` konservatif dan idempoten
   (default dry-run, perlu `--apply`): urutan prioritas bagian kuis → topik bank yang persis
   sama → materi dengan tepat satu bagian. Kalau ambigu, **tidak ditebak**
   (alasan dilaporkan: `tidak ada padanan pasti`).

Prinsipnya: kalau tidak ada padanan yang pasti, `section_id` dibiarkan kosong. Data kosong
jujur dan bisa diperbaiki guru; data salah menipu guru dan siswa.

### 2.3 UI Fase 1

- `QuizQuestionForm.vue`: pemilih "Bagian Materi (opsional)" per soal.
- `QuizBuilder.vue`: lencana bagian pada tiap soal, lencana bagian kuis, dan tombol
  "Terapkan bagian ke semua soal".

### 2.4 Test

`test_section_tagging.py` — **24/24 PASS**.

---

## 3. Fase 2 — diagnosis penguasaan per bagian

### 3.1 Sumber jawaban

Tiga sumber, semuanya benar-benar menyimpan bagian asal jawabannya:

| Sumber | Tabel | Penentu bagian |
|---|---|---|
| Jawaban kuis | `Answer` → `Question` → `Submission` → `Quiz` | `Question.section_id`; bila soal tidak bertag tapi kuis punya `Quiz.section_id`, jawaban itu memakai bagian kuis (aturan eksplisit, bukan tebakan) |
| Jawaban interaktif | `StudentAnswer` | `StudentAnswer.section_id` |
| Jawaban latihan | `PracticeAnswer` | `PracticeAnswer.section_id` (lihat §5) |

Aturan yang sengaja ditegakkan:

- Hanya `Submission.status = 'submitted'` yang dihitung. Jawaban kuis yang masih
  `in_progress` **tidak** masuk hitungan.
- `Answer.is_correct IS NULL` diabaikan.
- Soal **tanpa** tag bagian dan kuis **tanpa** `section_id` tidak dipetakan ke bagian mana pun
  — lebih baik tidak terhitung daripada dipetakan ke bagian yang tidak bisa dibuktikan.
- Latihan memakai **jawaban terakhir per soal**, bukan jumlah percobaan (§5.4).

### 3.2 Ambang minimum & kejujuran angka

`MIN_SECTION_SAMPLE = 3` (di `learning_analytics_service.py`).

- `answered >= 3` → `score = correct / answered * 100`, `status = 'READY'`,
  `mastery` = label dari `mastery_info()` (Baik Sekali / Baik / Cukup / Kurang).
- `answered < 3` → **`score = None`, `mastery = None`, `status = 'INSUFFICIENT_DATA'`**,
  hitungan mentah (`answered`, `correct`, `wrong`) tetap dilaporkan, plus `note`
  yang menyebut ambangnya.

Tidak ada skor yang dikarang dari penyelesaian bagian. Sebelumnya halaman progres memakai
fallback `100.0` bila bagian selesai dibaca tanpa jawaban; fallback itu **dihapus** karena
"selesai membaca" bukan bukti penguasaan.

Ringkasan mastery materi (`mastery_score` di halaman progres siswa) sekarang hanya dirata-rata
dari bagian yang `READY`. Bila tidak ada satu pun bagian yang cukup data, nilainya `None`
dan `mastery_status = 'INSUFFICIENT_DATA'` — UI menampilkan "Data belum cukup", bukan angka.

### 3.3 Endpoint

**Siswa** — `GET /api/student/sections/<material_id>`

```json
{
  "material_id": 107,
  "material_title": "[DEMO] VIRUS",
  "min_sample": 3,
  "sections_with_data": 2,
  "sections_insufficient": 4,
  "sections": [
    {
      "section_id": 41, "title": "Struktur Tubuh Virus", "position": 0,
      "answered": 4, "correct": 3, "wrong": 1,
      "quiz_answered": 3, "quiz_correct": 2,
      "interactive_total": 1, "interactive_correct": 1,
      "practice_answered": 2, "practice_correct": 1, "practice_attempts": 3,
      "score_sources": ["kuis", "interaktif", "latihan"],
      "score": 71.4, "status": "READY",
      "mastery": {"label": "Baik", "min_score": 75, "max_score": 89, "score": 75.0},
      "note": null
    },
    { "section_id": 42, "title": "Replikasi Virus", "answered": 1, "correct": 1,
      "score": null, "status": "INSUFFICIENT_DATA", "mastery": null,
      "note": "Butuh minimal 3 jawaban; baru 1." }
  ]
}
```

Seluruh bagian materi dikembalikan, termasuk yang belum punya jawaban, supaya peta pemahaman
tidak menyembunyikan bagian kosong.

`answered`/`correct` adalah gabungan tiga sumber, dan `score_sources` menyebutkan sumber mana
saja yang benar-benar menyumbang angka pada baris itu. Rinciannya (`quiz_*`, `interactive_*`,
`practice_*`) selalu ikut, jadi gabungan tidak pernah menutupi asal-usulnya.

Aturan akses identik dengan `/api/student/progress/<material_id>`: materi harus `published`
dan siswa harus berhak atas materi tersebut (403 kalau tidak).

**Guru** — `GET /api/teacher/analytics/materials/<material_id>` kini memuat `section_mastery`:

```json
{
  "section_mastery": {
    "material_id": 115, "min_sample": 3, "total_students": 76,
    "sections_with_data": 2, "sections_insufficient": 0,
    "sections": [ { "section_id": 88, "title": "Struktur Tubuh Virus",
                    "answered": 96, "correct": 71, "wrong": 25,
                    "score": 74.0, "status": "READY", "mastery": { "label": "Cukup", ... },
                    "students_answered": 40, "total_students": 76, "note": null } ]
  }
}
```

`students_answered` = berapa siswa yang benar-benar menjawab pada bagian itu — pemisahan
"siswa belum menjawab" dari "siswa menjawab dan semuanya salah".

`section_mastery` hanya dihitung untuk siswa kelas guru tersebut, jadi tidak ada kebocoran
antar kelas. Ringkasan kelas memakai ambang minimum yang sama; bagian di bawah ambang tetap
`INSUFFICIENT_DATA`.

**Siswa — halaman progres** `GET /api/student/progress/<material_id>` kini menambah:
`section_mastery` (payload lengkap di atas), `mastery_status`, `mastery_min_sample`,
serta `sections[].{quiz_answered, quiz_correct, practice_answered, practice_correct,
practice_total, score_sources, answered, correct, mastery_status, mastery_score,
mastery}` dan `mastery_rows[].status`. Kunci lama tidak dihapus.

`practice_total` = berapa soal latihan yang **sudah disetujui guru** untuk bagian itu; dipakai
UI untuk menyalakan tombol Latihan dan mematikan tombol dengan alasan bila belum ada soalnya.

### 3.4 UI Fase 2

- `student/progress/[material_id].vue`
  - kartu "Penguasaan" materi menampilkan "Data belum cukup" bila `mastery` null;
  - daftar "Bagian Materi" per bagian: jumlah jawaban kuis + soal interaktif, dan lencana
    penguasaan, atau lencana abu-abu "belum cukup data";
  - panel "Penguasaan Materi" menampilkan "—" dan keterangan "data belum cukup" untuk baris
    yang insufficient.
- `teacher/analytics/index.vue`
  - pada baris materi yang diklik, tabel baru "Penguasaan per Bagian": bagian, dijawab, benar,
    penguasaan, cakupan siswa, dengan catatan ambang minimum.

### 3.5 Test

`test_section_mastery.py` — **34/34 PASS**, antara lain memverifikasi:
ambang minimum tidak dikarang; jawaban tanpa tag tidak dipetakan; fallback
`Quiz.section_id` bekerja; submission `in_progress` tidak dihitung; bagian tanpa data tetap
muncul; ringkasan kelas jujur pada ambang yang sama; siswa/guru di luar cakupan mendapat 403.

---

## 4. Fase 3 (3a–3c) — soal latihan per bagian

Bagian materi sekarang bisa punya soal latihan sendiri. Latihan diambil dari
`question_bank` yang **ditautkan eksplisit ke bagian**, bukan dari soal yang
topiknya kebetulan mirip.

### 4.1 Kenapa harus ada bagian dan review guru

Bank soal yang ada sekarang hanya 16 soal dengan topik bebas (`Virus`, `VIRUS`, `KH`,
`NULL`), dan **tidak satu pun** persis sama dengan salah satu dari 23 judul bagian materi.
Artinya latihan per bagian tidak mungkin diisi dari bank soal yang sudah ada — harus ada
jalan untuk menambahkannya.

Jalannya: **guru menulis sendiri** (dengan tautan ke bagian), atau **AI membuat draf** yang
kemudian **guru periksa**. AI tidak pernah melayani siswa langsung dan tidak pernah
disetujui otomatis. Hanya soal berstatus `APPROVED` yang boleh dipakai sebagai latihan;
draf `DRAFT` dan yang ditolak `REJECTED` tidak terlihat oleh siswa.

### 4.2 Skema (3a)

`question_bank` dapat 9 kolom baru, semua nullable kecuali dua yang punya default:

| Kolom | Arti |
|---|---|
| `section_id` | FK `material_sections.id`, `NULL` = belum ditautkan |
| `source` | `teacher` (default) atau `ai` |
| `status` | `APPROVED` (default), `DRAFT`, `REJECTED` |
| `generated_by`, `model_name`, `prompt_version` | jejak draf AI |
| `reviewed_by`, `reviewed_at` | siapa & kapan guru memutuskan |
| `misconception` | miskonsepsi yang diuji soal ini |

Ditambah `question_bank_options.feedback` — alasan tiap opsi benar/salah, dipakai guru
saat menilai pengecoh.

Migrasi idempoten lewat `_COMPAT_COLUMNS`, jadi 16 soal bank lama otomatis menjadi
`source='teacher'`, `status='APPROVED'` (tidak berubah jadi draf, tidak hilang).

Siklus hidup ini sengaja meniru `quiz_explanations` yang sudah terbukti dipakai di
pembahasan AI: status, sumber, model, peninjau, waktu.

### 4.3 Aturan yang dijaga (tidak menebak)

1. `section_id` hanya diisi dari bagian yang **guru pilih**. String topik tidak pernah
   dicocokkan ke judul bagian (aturan konservatif Fase 1 tetap berlaku).
2. Untuk draf AI, `section_id` **dan** `topic` diambil dari record bagian, bukan dari
   keluaran model. Model tidak pernah menentukan soal ini milik bagian mana.
3. Kalau `section_id` terisi, `topic` mengikuti judul bagian dan tidak bisa dilencengkan
   (`update` mengabaikan `topic` selama masih tertaut). Melepas tautan mengembalikan topik
   bebas.
4. Bagian milik guru lain ditolak 400/403. Bagian tanpa teks ditolak 400 dengan pesan jelas.
5. Cakupan per bagian melaporkan **jumlah apa adanya** (disetujui / draf / ditolak). Tidak
   ada rasio atau skor turunan, jadi bagian kosong tampil "belum ada soal latihan".

### 4.4 Endpoint (3b–3c)

| Method | Path | Fungsi |
|---|---|---|
| GET | `/api/teacher/practice/sections` | Semua bagian milik guru + jumlah soal per status + `ai_available` |
| POST | `/api/teacher/practice/sections/<sid>/drafts` | Minta AI membuat draf untuk satu bagian (`count` 1–10, `difficulty`) |
| GET | `/api/teacher/practice/drafts?status=DRAFT` | Antrean review guru |
| POST | `/api/teacher/practice/drafts/<bank_id>/approve` | Setujui (satu-satunya jalan DRAFT → APPROVED) |
| POST | `/api/teacher/practice/drafts/<bank_id>/reject` | Tolak (baris tetap disimpan untuk audit) |

`GET /api/teacher/question-bank` kini menerima filter `status`, `source`, `section_id`;
`POST`/`PUT` menerima `section_id` dan `misconception`.

### 4.5 Cara kerja draf AI

- Konteks = **hanya** bagian yang dipilih guru (judul, isi, tujuan pembelajaran materi).
  Tidak ada pencarian keyword antar bagian seperti di mesin pembahasan, karena guru sudah
  memilih bagiannya.
- Prompt mewajibkan: hanya fakta dari teks bagian, tepat satu opsi benar, semua pengecoh
  menyatukan satu miskonsepsi yang sama, dan **tidak boleh** bertanya tentang bagian
  itu sendiri ("apa isi bagian ini").
- Hasil draf yang tetap berupa pertanyaan meta ("apa materi yang disajikan di sini?")
  **dibuang dan dihitung** dalam `skipped_count`, bukan disimpan sebagai bahan review.
- Keluaran draf divalidasi ulang dengan validator yang sama seperti soal tulisannya guru
  (minimal 2 opsi, tepat 1 benar, opsi unik). Yang gagal validasi tidak disimpan.
- Model, versi prompt, dan miskonsepsi tersimpan bersama soal, jadi jejak auditnya jelas.

### 4.6 Tidak ada fallback karangan

Tidak seperti mesin penjelasan (yang punya fallback-aturan karena selalu ada kunci
jawaban otoritatif), modul ini **tidak punya** fallback. Kalau `AI_API_KEY` belum di-set,
jawabannya 503 dengan pesan jujur, bukan soal racikan:

> AI belum dikonfigurasi (AI_API_KEY). Set di server lalu coba lagi, atau tulis soal sendiri
> dan tautkan ke bagian ini.

Gagal penyedia (HTTP 503/429 = sedang sibuk) dicoba 3 kali dengan jeda pendek, lalu
dilaporkan apa adanya: "Layanan AI tidak bisa dipakai (HTTP 503, penyedia AI sedang
sibuk — coba lagi beberapa saat lagi)". Tidak ada soal yang tetap dibuat dari kegagalan.

### 4.7 UI (3a–3c)

- `teacher/practice.vue` (baru, menu **Latihan Bagian**)
  - Tab "Bagian Materi": tiap bagian menampilkan jumlah soal disetujui / menunggu review /
    ditolak, dengan catatan "Bagian ini belum punya soal latihan yang disetujui";
    kontrol jumlah + tingkat kesulitan + tombol **Buat draf**.
  - Tab "Antrean Review": daftar draf lengkap dengan opsi, feedback tiap pengecoh,
    pembahasan, miskonsepsi, dan nama model. Aksi: **Sunting**, **Setujui**, **Tolak**.
  - Banner kuning jujur kalau `AI_API_KEY` belum ada, dengan jalan keluar (tulis sendiri).
- `quiz/QuestionBankForm.vue` — dropdown "Bagian Materi" (dikelompokkan per materi), field
  miskonsepsi, dan kolom feedback per opsi. Saat bagian dipilih, kolom topik terkunci dan
  terisi otomatis.
- `teacher/question-bank.vue` — lencana status + lencana "Draf AI" + baris "Latihan untuk
  bagian: …" + filter status.

### 4.8 Test

`test_practice_drafts.py` — **80/80 PASS**, antara lain memverifikasi: kolom baru ada; soal
bank lama tetap `teacher`/`APPROVED`; bagian tanpa soal dilaporkan 0 (bukan rasio karangan);
tanpa AI → 503 dan **tidak ada baris baru**; draf disimpan sebagai `DRAFT` dengan
`section_id`/`topic` dari bagian; draf rusak (dua jawaban benar / tanpa opsi) tidak
disimpan dan jumlahnya dilaporkan; hanya persetujuan guru yang membuat `APPROVED`; peninjau
dan waktu tercatat; guru lain mendapat 403; bagian tanpa teks ditolak; guru bisa menautkan
soal tulisannya sendiri dan topiknya tidak melenceng; filter status/bagian bekerja; konteks
prompt tidak memuat bagian sebelah.

---

## 5. Fase 3d — latihan siswa dari soal yang sudah disetujui

3a–3c menyiapkan soal latihannya, tapi belum ada yang memakainya. 3d menutup
loop itu: guru menyetujui soal → siswa bisa mengerjakannya dari halaman progres.

### 5.1 Tabel jawaban yang terpisah

`practice_answers` (baru) dipakai untuk jawaban latihan, **bukan** `student_answers`.

Alasannya bukan sekadar Luhur kode: `student_answers.content_id` adalah `NOT NULL` dan menunjuk
`material_contents`, jadi maknanya "siswa menjawab blok interaktif milik materi ini". Jawaban
soal bank menunjuk `question_bank`, bukan blok materi. Memaksanya masuk ke sana berarti
mengarang relasi yang tidak ada, dan membuat hitungan kuis/interaktif ikut tercampur latihan
tanpa disadari. Tabel terpisah membuat sumber data tidak bisa tercampur diam-diam —
dan jadi tidak perlu kolom penanda pada tabel lama.

Kolom: `student_id`, `material_id`, `section_id`, `bank_question_id`, `selected_option`,
`is_correct`, `attempt_no`, `question_snapshot`, `answered_at`.

`question_snapshot` menyimpan teks soal seperti yang tampil saat dijawab. Kalau guru menyunting
soalnya belakangan, catatan lama tetap bisa dibaca apa adanya yang dinilai siswa.

### 5.2 Endpoint siswa

| Method | Path | Fungsi |
|---|---|---|
| GET | `/api/student/practice/<mid>/sections` | Bagian mana yang punya soal latihan + progress siswa |
| GET | `/api/student/practice/<mid>/sections/<sid>` | Soal `APPROVED` bagian itu, **tanpa** kunci |
| POST | `/api/student/practice/<mid>/sections/<sid>/answer` | Nilai satu jawaban + catat-legal |

Gerbang yang sama untuk ketiganya: role siswa, materi `published`, siswa berhak atas materi itu,
dan bagian benar-benar milik materi tersebut (bagian materi lain → 404).

### 5.3 Aturan yang dijaga

1. **Hanya `APPROVED`.** `DRAFT` dan `REJECTED` tidak muncul di daftar, tidak bisa diambil,
   dan menjawabnya ditolak 403. Status dicek **lagi** di endpoint jawaban, bukan hanya saat
   pemuatan — status bisa berubah di antara keduanya.
2. **Kunci jawaban tidak pernah ada di respons pemuatan.** `is_correct`, `explanation`,
   `misconception`, dan `feedback` per opsi baru muncul setelah jawaban terkirim. Diperiksa
   dengan menelusuri seluruh payload.
3. **Penilaian di server.** Klien mengirim `selected_option`, dan server mencocokkannya dengan
   `order_index` yang tersimpan di database. Mengirim `option_id` baris (yang menunjuk kunci)
   tidak dipercaya — kalau tidak cocok dengan `order_index`, jawabannya 400.
4. **Bagian kosong tidak dikaryakan.** Tanpa soal `APPROVED`, jawabannya 200 dengan daftar kosong
   dan alasan tertulis. Tidak ada fallback ke bagian lain, tidak ada soal racikan, bukan 404.
5. **Tidak ada kebocoran antar kelas.** Sama seperti halaman progres: materi harus dipublikasikan
   dan siswa harus mengikuti kelasnya. Id atau opsi yang tidak berbentuk angka dijawab 4xx
   yang jujur, bukan 500.

### 5.4 Mengulang tidak menggelembungkan angka

Soal boleh diulang sebagai latihan dan **semua percobaan disimpan** apa adanya
(`attempt_no` naik). Yang dihitung untuk diagnosis adalah **jawaban terakhir per soal**:
mengulang satu soal yang salah sampai benar tetap terhitung sebagai satu soal terjawab. Dengan
itu, angka `practice_answered` tidak bisa dibuat naik hanya dengan mengulang-ulang, dan
`practice_attempts` tetap melaporkan berapa kali sebenarnya siswa mencoba.

### 5.5 UI

- `student/progress/[material_id].vue`
  - tiap bagian punya tombol **Latihan (n)**; `n` = soal yang disetujui guru. Kalau `n = 0`,
    tombol mati dengan penjelasan "Belum ada soal latihan yang disetujui guru untuk bagian ini".
  - ringkasan jawaban tiap bagian mentions jumlah soal latihan yang sudah dikerjakan.
  - ada catatan bahwa angka penguasaan adalah gabungan kuis + interaktif + latihan.
- `student/SectionPracticeModal.vue` (baru) — satu soal pada satu waktu: pilih opsi →
  **Periksa Jawaban** → langsung tampil pembahasan, miskonsepsi yang diuji, dan alasan tiap
  opsi (bukan hanya opsi yang benar). Di akhir ada rekap jawaban latihan bagian itu.

### 5.6 Test

`test_student_practice.py` — **73/73 PASS**, antara lain memverifikasi: tabel terpisah ada dan
`student_answers` lama tidak berubah; hanya `APPROVED` yang terlihat dan bisa dijawab;
`is_correct`/`explanation`/`misconception`/`feedback` tidak bocor di respons muat; bagian kosong
200 + alasan; `option_id` ditolak; soal bagian lain dan status `DRAFT` ditolak; lima percobaan
tetap dihitung satu soal terjawab; diagnosis Fase 2 menerima latihan sebagai sumber terpisah,
`score_sources` terbuka, ambang minimum tetap berlaku, dan 3 soal latihan benar menghasilkan
`66.7` (2 benar dari 3, tidak dikarang); siswa luar kelas 403; id/opsi rusak jadi 4xx
yang jujur, bukan 500.

### 5.7 Data demo

`scripts/tag_demo_practice_sections.py` menautkan 6 soal bank lama ke bagian yang benar-benar
membahas isinya (eksplisit, tanpa pencocokan teks), dan
`scripts/seed_practice_feedback.py` mengisi pembahasan, miskonsepsi, dan feedback per opsi
untuk soal-soal itu. Keduanya idempoten, default dry-run, dan **tidak pernah menyetujui soal**
— itu tetap keputusan guru.

Hasil di data demo: bagian "Bagaimana Struktur Virus?" 4 soal, "Cara Virus Berkembang Biak" 1,
"Kekayaan Keanekaragaman Hayati Indonesia" 1, "Pemanfaatan dan Pelestarian Keanekaragaman
Hayati" 1. Dua draf AI lain sengaja dibiarkan `DRAFT` untuk peragaan persetujuan langsung.

---

## 6. Cara demo (alur yang bisa ditunjukkan)

1. Login sebagai guru, buka sebuah kuis, isi kolom "Bagian Materi" pada kuis, tekan
   **Terapkan bagian ke semua soal**. Lencana bagian langsung muncul di tiap soal.
2. Login sebagai siswa, kerjakan kuis itu sehingga tiap bagian punya jawaban
   (perlu minimal 3 jawaban per bagian agar skor muncul).
3. Buka **Riwayat Belajar → materi → detail**: tiap bagian menampilkan jumlah jawaban kuis,
   jumlah soal interaktif, jumlah soal latihan, dan lencana penguasaan. Bagian dengan < 3 jawaban
   tampil "belum cukup data" — itu disengaja, bukan bug.
4. Login sebagai guru, buka **Analytics → Per Materi**, klik baris materi: tabel
   "Penguasaan per Bagian" menampilkan akurasi per bagian dan berapa siswa yang menjawabnya.
5. (Fase 3a–3c) Login sebagai guru, buka menu **Latihan Bagian**:
   - di tab "Bagian Materi" tekan **Buat draf** pada sebuah bagian → masuk tab "Antrean
     Review" → periksa isi soalnya → **Setujui**. Bagian itu kini punya soal latihan yang
     benar-benar disetujui manusia.
   - buka **Bank Soal** untuk melihat lencana status yang sama, dan untuk menulis soal
     sendiri yang langsung tertaut ke bagian.
6. (Fase 3d) Di halaman progres siswa, tekan **Latihan** pada bagian yang sudah punya soal
   disetujui: satu soal muncul, siswa memilih opsi, lalu **Periksa Jawaban** langsung
   menampilkan pembahasan, miskonsepsi, dan alasan tiap opsi.
7. Muat ulang halaman progres: bagian itu kini menampilkan jumlah soal latihan yang dikerjakan,
   dan angkanya masuk ke lencana penguasaan sebagai sumber tersendiri.

Data demo sudah punya 2 draf AI yang menunggu review pada bagian "Bagaimana Struktur Virus?"
(materi `[DEMO] VIRUS`), jadi langkah review bisa langsung ditunjukkan tanpa memanggil AI.
Empat bagian lain sudah punya soal latihan yang disetujui, jadi langkah 6 bisa langsung
ditunjukkan juga.

---

## 7. Batasan yang perlu diketahui

- **Data demo belum bertag bagian.** Semua soal yang ada sekarang masih `section_id = NULL`,
  jadi di data demo diagnosis siswa akan didominasi `INSUFFICIENT_DATA` sampai guru menandai
  bagian (langkah 1 di atas). Ringkasan kelas sudah punya angka dari jawaban soal interaktif,
  karena `StudentAnswer.section_id` memang terisi.
- Ambang 3 jawaban dipilih agar angka tidak berubah-ubah karena satu soal. Ini konstanta kode,
  belum bisa diatur guru.
- Diagnosis baru untuk **materi**; belum ada agregasi lintas materi per bagian.
- Bobot gabungan kuis + interaktif + latihan dihitung pada tingkat jawaban (bukan rata-rata
  persentase), sehingga kuis dengan 10 soal memberi bobot lebih besar daripada 1 soal latihan.
  Karena bobot latihan ikut masuk, **soal latihan yang jauh lebih mudah akan menaikkan skor
  penguasaan** — ini konsekuensi dari memasukkan latihan sebagai sumber, dan_numbers sumbernya
  selalu ditampilkan per baris supaya bisa dinilai.
- **Bagian dengan isi tipis menghasilkan soal yang tidak berguna.** Contoh di data demo:
  bagian "Siklus Replikasi Virus" hanya berisi satu kalimat ringkasan, sehingga AI tidak
  punya facts untuk diuji. Pertanyaan meta otomatis dibuang dan dilaporkan di
  `skipped_count`, tapi jawaban terbaiknya tetap: guru yang menambah isi bagian.
- **Penyedia AI kadang sibuk (HTTP 503 "high demand").** Sudah ditangani 3 percobaan dengan
  jeda pendek, tapi kalau gagal tetap gagal dengan pesan jujur — tidak ada soal karangan.
  Untuk demo, siapkan draf lebih dulu (sudah tersedia 2 draf) daripada bergantung pada AI live.
- **Rekomendasi per bagian belum ada.** Yang ada baru latihan per bagian;/engine rekomendasi
  masih per-materi (`Recommendation.material_id` NOT NULL), belum ada gating, dan belum ada
  peta panas siswa × bagian.
- **Tidak ada batas percobaan latihan.** Siswa boleh mengerjakan berkali-kali (§5.4).
  Yang perlu diketahui guru: angka latihan bertumpu pada **jawaban terakhir**, bukan banyaknya
  percobaan, jadi mengulang-ulang tidak membuat angka terlihat naik.
- **Guru masih harus menandai bagian soal kuis sendiri** supaya diagnosis Fase 2 punya
  sumber jawaban; tidak ada tebakan otomatis.