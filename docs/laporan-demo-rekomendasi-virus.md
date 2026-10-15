# Laporan Demo: Rekomendasi Materi & Rekomendasi Soal — [DEMO] VIRUS

- **Tanggal:** 15 October 2026
- **Materi:** `[DEMO] VIRUS` (material_id **107**, status *published*)
- **Guru pemilik:** `Guru 1` (user_id 71, `guru1@ebiox.com`)
- **Akun murid:** `murid1` … `murid20` (`muridN@ebiox.com`, password `123123123`)
- **Backend:** `http://127.0.0.1:5000`

---

## 1. Ringkasan

- Login berhasil: **20/20**
- Profil ML `READY`: **3/20** (sisanya `INSUFFICIENT_DATA`)
- Rekomendasi **materi** memuat [DEMO] VIRUS: **2/20**
- Rekomendasi **soal** (bagian) untuk [DEMO] VIRUS tersedia: **20/20**

> Rekomendasi **soal** selalu muncul (rule-based, dari bank soal yang disetujui). Rekomendasi **materi** menampilkan [DEMO] VIRUS terutama untuk murid yang belum menyelesaikannya; murid yang sudah selesai tetap mendapat saran **meninjau ulang** lewat rekomendasi soal.

---

## 2. Langkah yang Dijalankan

1. Membuat akun **murid4–murid20** (murid1–3 sudah ada), password `123123123`, di-enroll ke course 6.
2. Login tiap murid via `POST /api/login`.
3. Simulasi latihan (jawab soal [DEMO] VIRUS) via `GET/POST /api/student/practice/107/sections/...`.
4. Latih model sebagai Guru 1 via `POST /api/ml/train` (Decision Tree akurasi **0.82**, lift 0.52).
5. Ambil rekomendasi: `GET /api/student/learning-profile` dan `GET /api/student/recommendations`.

---

## 3. Hasil per Murid

| # | Akun | Login | Profil ML | Rank materi | Rank soal | Latihan (benar/total) | Soal [DEMO] VIRUS | Materi 107 disarankan |
|---|------|:-----:|-----------|:-----------:|:---------:|:---------------------:|:-----------------:|:---------------------:|
| 1 | murid1@ebiox.com | OK | READY | rule | rule | 16/30 | 5 bagian | tidak |
| 2 | murid2@ebiox.com | OK | READY | rule | rule | 11/30 | 3 bagian | ya |
| 3 | murid3@ebiox.com | OK | READY | rule | rule | 16/30 | 2 bagian | ya |
| 4 | murid4@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 5 | murid5@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 6 | murid6@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 7 | murid7@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 8 | murid8@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 9 | murid9@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 10 | murid10@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 11 | murid11@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 12 | murid12@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 13 | murid13@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 14 | murid14@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 15 | murid15@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 16 | murid16@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 17 | murid17@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 18 | murid18@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |
| 19 | murid19@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 16/30 | 5 bagian | tidak |
| 20 | murid20@ebiox.com | OK | INSUFFICIENT_DATA | fallback | rule | 11/30 | 5 bagian | tidak |

---

## 4. Contoh Detail Rekomendasi Soal (murid5)

**1. MENGENAL VIRUS DALAM KEHIDUPAN** — penguasaan `0.0` (Kurang), benar 0/5
   - Baru kamu latih - ulangi besok agar lebih efektif
   - Penguasaan bagian ini baru 0%
   - Masih 5 jawaban salah dari 5
   - Bukti: latihan
   - *Prasyarat:* Struktur Virus (Bagian ini menyebut "Struktur Virus" secara langsung)

**2. BENTUK, PENGELOMPOKAN, DAN REPLIKASI VIRUS** — penguasaan `50.0` (Kurang), benar 3/6
   - Baru kamu latih - ulangi besok agar lebih efektif
   - Prasyarat belum tuntas: "SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS"
   - Penguasaan bagian ini baru 50%
   - Masih 3 jawaban salah dari 6
   - *Prasyarat:* SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS (Isi mirip dengan "SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS" (0.62) dan posisinya lebih dulu)
   - *Prasyarat:* MENGENAL VIRUS DALAM KEHIDUPAN (Isi mirip dengan "MENGENAL VIRUS DALAM KEHIDUPAN" (0.55) dan posisinya lebih dulu)

**3. SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS** — penguasaan `55.6` (Kurang), benar 5/9
   - Baru kamu latih - ulangi besok agar lebih efektif
   - Prasyarat belum tuntas: "MENGENAL VIRUS DALAM KEHIDUPAN"
   - Penguasaan bagian ini baru 56%
   - Masih 4 jawaban salah dari 9
   - *Prasyarat:* Struktur Virus (Bagian ini menyebut "Struktur Virus" secara langsung)
   - *Prasyarat:* MENGENAL VIRUS DALAM KEHIDUPAN (Isi mirip dengan "MENGENAL VIRUS DALAM KEHIDUPAN" (0.67) dan posisinya lebih dulu)

**4. PENYAKIT,PENULARAN,PENCEGAHAN** — penguasaan `60.0` (Cukup), benar 3/5
   - Baru kamu latih - ulangi besok agar lebih efektif
   - Prasyarat belum tuntas: "MENGENAL VIRUS DALAM KEHIDUPAN"
   - Penguasaan bagian ini baru 60%
   - Masih 2 jawaban salah dari 5
   - *Prasyarat:* MENGENAL VIRUS DALAM KEHIDUPAN (Isi mirip dengan "MENGENAL VIRUS DALAM KEHIDUPAN" (0.55) dan posisinya lebih dulu)
   - *Prasyarat:* SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS (Isi mirip dengan "SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS" (0.43) dan posisinya lebih dulu)

**5. Bahan Ajar Pembelajaran** — penguasaan `None` (None), benar 0/0
   - Belum ada jawaban di bagian ini
   - *Prasyarat:* SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS (Isi mirip dengan "SEJARAH, CIRI-CIRI, DAN STRUKTUR VIRUS" (0.38) dan posisinya lebih dulu)
   - *Prasyarat:* MENGENAL VIRUS DALAM KEHIDUPAN (Isi mirip dengan "MENGENAL VIRUS DALAM KEHIDUPAN" (0.35) dan posisinya lebih dulu)

---

## 5. Cara Kerja & Pemicu

**Rekomendasi materi** (materi berikutnya yang dipelajari)
- Endpoint: `GET /api/student/recommendations` → bagian `recommendations`.
- Pemicu: murid membuka **dashboard** (`app/pages/student/dashboard.vue` → `loadRecs`).
- Metode: rule-based (penguasaan, prasyarat, status selesai).

**Rekomendasi soal** (bagian yang perlu dilatih/ditinjau)
- Endpoint: `GET /api/student/recommendations` → bagian `section_recommendations`; soal disajikan via `GET /api/student/practice/<material_id>/sections/<section_id>`.
- Pemicu: dashboard + modal latihan (`app/components/student/SectionPracticeModal.vue`).
- Engine adaptif: `src/services/student_practice_service.py` (`session_for_section`, `_weakest_level`, fokus miskonsepsi). Hanya soal berstatus `APPROVED` yang disajikan.
- Tiap jawaban (`POST /api/student/practice/<material_id>/sections/<section_id>/answer`) langsung memperbarui penguasaan.

**Profil ML** (`decision_tree` + `kmeans`)
- Membentuk label/cluster penguasaan; **tidak** ikut meranking rekomendasi.
- Dilatih lewat `POST /api/ml/train` (atau otomatis pada ambang tertentu).

---

## 6. Catatan

- Data latihan murid1–20 pada [DEMO] VIRUS ditambahkan **untuk keperluan demo**; hasil rekomendasi akan ikut kaya karena data ini. Bisa direset bila ingin kondisi fresh.
- Profil ML `INSUFFICIENT_DATA` untuk murid4–20 karena model per-kelas membutuhkan fitur riwayat (kuis, durasi, aktivitas) tiap murid, bukan hanya latihan.

---

## 7. Ranker ML untuk Urutan Rekomendasi (Learning-to-Rank)

Selain rule dan profil ML, ada **satu model yang benar-benar belajar mengurutkan** rekomendasi materi: `src/ml/ranker.py`.

**Apa yang dipelajari**
- **Label:** siswa benar-benar **menyelesaikan** materi (`MaterialStudentState.completed`) — perilaku nyata yang terukur, bukan skor karangan.
- **Fitur (bebas bocor/anti-leakage):** kemampuan siswa (`quiz_average`, `interactive_accuracy`, `correct_rate`, `learning_minutes`), sifat materi (`item_difficulty`, `item_time_minutes`, `item_phase`, `item_sections`), dan popularitas materi (`item_completion_rate`).
- Penguasaan/error per-materi siswa sengaja **tidak** dipakai karena nilainya sudah tercermin dari status "selesai" (kebocoran label, lihat `LABEL_DEFINING_FEATURES`).

**Evaluasi jujur (offline, cross-validation per siswa)**
- Endpoint latih: `POST /api/ml/train-ranker` (guru/admin). Endpoint metrik: `GET /api/ml/evaluation/ranker`.
- Protokol: **cross-validation per siswa** (seorang siswa tidak pernah muncul di train dan test sekaligus), metrik **NDCG@k** dan Precision@k, dibandingkan baseline **acak** dan **popularitas**. Rule produksi ditampilkan hanya sebagai **reference** (ia mengoptimalkan *kebutuhan*, bukan prediksi penyelesaian).
- Hasil pada data demo saat ini:
  - **ROC-AUC held-out ≈ 0.92** (model memisahkan siswa yang menyelesaikan vs tidak).
  - **NDCG@5 ≈ 0.43** vs acak ≈ 0.44 dan popularitas ≈ 0.43 → **tidak terbukti lebih baik**.
  - Akar masalah: data demo hanya punya **3–6 materi per siswa** dan sifat materi antar-materi nyaris seragam, sehingga sinyal untuk *mengurutkan di dalam satu siswa* sangat tipis. Ini keterbatasan data, bukan bug.

**Kebijakan penerapan (anti-klaim berlebihan)**
- Model **hanya dipakai mengurutkan** bila NDCG@k-nya mengungguli baseline terkuat dengan margin ≥ `RANKER_MIN_NDCG_GAIN` (default `0.02`).
- Pada data demo, gate ini **tertutup**, sehingga `GET /api/student/recommendations` tetap mengembalikan `ranking_method: "rule"` — rekomendasi tidak dipaksa memakai model yang belum terbukti.
- Bila kelak data bertambah dan model lolos gate, `ranking_method` otomatis menjadi `"ml"` tanpa perubahan kode.
- Metrik, catatan, dan keterbatasan ditampilkan di halaman guru **Machine Learning Insights** (`app/pages/teacher/analytics/ml.vue`).
