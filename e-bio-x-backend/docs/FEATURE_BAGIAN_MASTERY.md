# Fitur "Bagian Materi" — dari jawaban salah ke bagian materi, bukan hanya materi

Dokumen ini menjelaskan fitur yang sedang dibangun dalam lima fase. **Fase 1 dan Fase 2
sudah selesai.** Tiga fase berikutnya masih rencana.

**Tujuan akhir:** ketika seorang siswa salah menjawab soal tentang *Struktur Tubuh Virus*,
sistem harus bisa menunjuk bagian materi itu — bukan sekadar "materi VIRUS saja belum dikuasai" —
lalu memberi latihan-latihan dari bank soal pada bagian tersebut, dan akhirnya menampilkan
peta pemahaman siswa × bagian yang bisa dilihat guru.

Fase yang sudah selesai:

| Fase | Isi | Status |
|---|---|---|
| 1 | Penandaan bagian pada soal (`questions.section_id`) | Selesai |
| 2 | Diagnosis penguasaan per bagian (siswa & kelas) | Selesai |
| 3 | Rekomendasi per bagian + latihan bank soal | Rencana |
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

Dua sumber, keduanya benar-benar menyimpan bagian asal jawabannya:

| Sumber | Tabel | Penentu bagian |
|---|---|---|
| Jawaban kuis | `Answer` → `Question` → `Submission` → `Quiz` | `Question.section_id`; bila soal tidak bertag tapi kuis punya `Quiz.section_id`, jawaban itu memakai bagian kuis (aturan eksplisit, bukan tebakan) |
| Jawaban interaktif | `StudentAnswer` | `StudentAnswer.section_id` |

Aturan yang sengaja ditegakkan:

- Hanya `Submission.status = 'submitted'` yang dihitung. Jawaban kuis yang masih
  `in_progress` **tidak** masuk hitungan.
- `Answer.is_correct IS NULL` diabaikan.
- Soal **tanpa** tag bagian dan kuis **tanpa** `section_id` tidak dipetakan ke bagian mana pun
  — lebih baik tidak terhitung daripada dipetakan ke bagian yang tidak bisa dibuktikan.

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
      "score": 75.0, "status": "READY",
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
serta `sections[].{quiz_answered, quiz_correct, answered, correct, mastery_status,
mastery_score, mastery}` dan `mastery_rows[].status`. Kunci lama tidak dihapus.

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

## 4. Cara demo (alur yang bisa ditunjukkan)

1. Login sebagai guru, buka sebuah kuis, isi kolom "Bagian Materi" pada kuis, tekan
   **Terapkan bagian ke semua soal**. Lencana bagian langsung muncul di tiap soal.
2. Login sebagai siswa, kerjakan kuis itu sehingga tiap bagian punya jawaban
   (perLU minimal 3 jawaban per bagian agar skor muncul).
3. Buka **Riwayat Belajar → materi → detail**: tiap bagian menampilkan jumlah jawaban kuis,
   jumlah soal interaktif, dan lencana penguasaan. Bagian dengan < 3 jawaban tampil
   "belum cukup data" — itu disengaja, bukan bug.
4. Login sebagai guru, buka **Analytics → Per Materi**, klik baris materi: tabel
   "Penguasaan per Bagian" menampilkan akurasi per bagian dan berapa siswa yang menjawabnya.

---

## 5. Batasan yang perlu diketahui

- **Data demo belum bertag bagian.** Semua soal yang ada sekarang masih `section_id = NULL`,
  jadi di data demo diagnosis siswa akan didominasi `INSUFFICIENT_DATA` sampai guru menandai
  bagian (langkah 1 di atas). Ringkasan kelas sudah punya angka dari jawaban soal interaktif,
  karena `StudentAnswer.section_id` memang terisi.
- Ambang 3 jawaban dipilih agar angka tidak berubah-ubah karena satu soal. Ini konstanta kode,
  belum bisa diatur guru.
- Diagnosis baru untuk **materi**; belum ada agregasi lintas materi per bagian.
- Bobot gabungan kuis + interaktif dihitung pada tingkat jawaban (bukan rata-rata dua
  persentase), sehingga kuis dengan 10 soal memberi bobot lebih besar daripada 1 soal interaktif.
- Fase 3–5 belum ada: rekomendasi masih bersifat per-materi (`Recommendation.material_id`
  NOT NULL), belum ada gating, dan belum ada petaheatmap siswa × bagian.