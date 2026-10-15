# Rancangan: Penilaian **Level Materi** Berbasis **Set Diagnostik** (Bebas Pengaruh Mesin Adaptif)

- **Tanggal:** 15 October 2026
- **Status:** **SUDAH DIIMPLEMENTASIKAN (15 Oktober 2026).** Backend, migrasi DB,
  API guru/siswa, dan UI sudah dikerjakan serta diuji. Lihat **Bagian 16** untuk
  ringkasan bukti (tes otomatis + screenshot before/after).
- **Tujuan dokumen:** spesifikasi teknis fitur + catatan status implementasi.
- **Dokumen terkait:** `docs/laporan-demo-rekomendasi-virus.md`, `docs/screenshots/`
- **Konteks permintaan dosen:** "level pada materi" — tingkat kesulitan materi yang dinilai otomatis.

---

## 1. Masalah yang Diselesaikan

Saat ini `materials.difficulty` hanya diisi oleh skrip seed; form materi menyatakan
*"tingkat kesulitan dinilai otomatis"* tetapi **belum ada kode yang menghitungnya**.

Penilaian otomatis dari jawaban yang ada **tidak bisa** memakai jawaban latihan biasa,
karena **semua latihan bersifat adaptif** (`student_practice_service.session_for_section`,
selalu dipanggil oleh `get_student_practice_questions` di `practice_controller.py:359`).
Mesin adaptif sengaja menyajikan komposisi **60% tingkat terlemah siswa / 30% di bawah / 10% di atas**
(`SESSION_MIX_TARGET/BELOW/ABOVE`). Akibatnya sampel jawaban **bias** ke soal yang sulit bagi siswa,
sehingga `p` (fraksi benar) turun dan materi **terlihat lebih sulit daripada kenyataannya**.

**Solusi:** nilai level materi dari **set soal diagnostik** yang dikerjakan **tanpa adaptasi**,
sehingga sampelnya netral dan tidak dipengaruhi mesin adaptif.

---

## 2. Prinsip

1. **Diukur, bukan ditebak.** Level dihitung dari `p-value` (fraksi benar) jawaban nyata,
   memakai mesin yang sudah ada (`src/services/question_difficulty_service.py`).
2. **Tidak menimpa deklarasi.** Label guru/seed tetap ada; label terukur ditampilkan **berdampingan**.
3. **Tidak menebak saat data kurang.** Bila kurang → `INSUFFICIENT_DATA`, bukan "sedang".
4. **Terpisah dari mesin adaptif.** Soal diagnostik **tidak** ikut sesi latihan adaptif (dan sebaliknya),
   agar kedua sampel tidak saling mencemari.
5. **Transparan.** Selalu sebutkan basis: jumlah soal, jumlah siswa, `p`, margin.

---

## 3. Definisi Istilah

| Istilah | Arti |
|---|---|
| **Soal bank** | Baris pada tabel `question_bank` (`src/models/question_bank.py`). |
| **Latihan adaptif** | Soal bank `status='APPROVED'` ber-`section_id` yang disajikan sesi adaptif (komposisi 60/30/10). |
| **Set diagnostik** | Soal bank ber-`section_id` yang ditandai `purpose='diagnostic'`, disajikan **non-adaptif**. |
| **Level materi** | Tingkat kesulitan materi = agregat `p-value` dari jawaban ke set diagnostik materi itu. |

---

## 4. Ruang Lingkup Perhitungan

| Sumber jawaban | Masuk? | Alasan |
|---|:---:|---|
| Soal bank `purpose='diagnostic'`, `status='APPROVED'`, ber-`section_id`, dikerjakan mode diagnostik | **Ya** | sampel terkontrol & netral |
| Soal bank latihan (dipakai sesi adaptif) | **Tidak** | komposisi 60/30/10 → bias |
| Soal bank tanpa `section_id` | **Tidak** | tidak tersambung ke materi |
| Soal interaktif tertanam (`StudentAnswer`) | **Tidak** | dikerjakan sambil membaca, bukan asesmen |
| Jawaban dari soal berstatus DRAFT/REJECTED | **Tidak** | tidak pernah disajikan ke siswa |

> Bila dosen ingin soal interaktif ikut: tambahkan sebagai **sumber kedua yang dilaporkan terpisah**.

---

## 5. Perubahan Model Data

### 5.1 Tabel `question_bank` — kolom baru `purpose`

| Kolom | Tipe | Default | Nilai |
|---|---|---|---|
| `purpose` | `VARCHAR(20)` | `'practice'` | `'practice'` \| `'diagnostic'` |

Migrasi idempoten ditambahkan ke `_COMPAT_COLUMNS` di `src/config/database.py`:
```python
('question_bank', 'purpose',
 "ALTER TABLE question_bank ADD COLUMN purpose VARCHAR(20) NOT NULL DEFAULT 'practice'"),
```

### 5.2 (Opsional) Tabel `practice_answer` — kolom `context`

| Kolom | Tipe | Default | Nilai |
|---|---|---|---|
| `context` | `VARCHAR(20)` | `'adaptive'` | `'adaptive'` \| `'diagnostic'` |

Opsional: karena set diagnostik **disjoint** dari set latihan, jawaban diagnostik sudah bisa
dikenali dari `bank_question_id`. Kolom ini hanya pengaman bila kelak satu soal dipakai di dua mode.

### 5.3 (Opsional) Tabel `material_difficulty_stats` — cache hasil

| Kolom | Tipe | Keterangan |
|---|---|---|
| `material_id` | `INT` | FK ke `materials.id` |
| `status` | `VARCHAR(20)` | `READY` \| `INSUFFICIENT_DATA` |
| `label` | `VARCHAR(10)` | `easy` \| `medium` \| `hard` |
| `p` | `DECIMAL(5,3)` | pooled p |
| `n_students` | `INT` | siswa berbeda |
| `n_items` | `INT` | soal diagnostik READY |
| `margin` | `DECIMAL(5,3)` | setengah lebar CI 95% |
| `near_boundary` | `BOOL` | p ± margin memotong ambang |
| `computed_at` | `DATETIME` | waktu hitung |

> `materials.difficulty` **tidak** diubah/ditimpa — label deklarasi tetap utuh.

---

## 6. Alur

### 6.1 Guru menyiapkan set diagnostik
1. Guru menandai soal bank sebagai **diagnostik** pada bagian tertentu
   (UI "Soal Latihan per Bagian" → toggle "Jadikan soal diagnostik").
2. Target minimal **K soal diagnostik** per materi (usul K = 3).

### 6.2 Siswa mengerjakan (mode diagnostik, non-adaptif)
1. Siswa memilih **"Asesmen Diagnostik"** pada bagian.
2. Sistem menyajikan **semua** soal `purpose='diagnostic'` bagian itu **dengan urutan tetap**
   (tanpa komposisi 60/30/10).

### 6.3 Perhitungan level materi
1. Ambil jawaban ke soal diagnostik materi tersebut (dari `PracticeAnswer`).
2. Ukur `p` tiap soal (`question_difficulty_service.classify`); hanya yang `READY` dipakai.
3. Agregasi pooled ke tingkat materi (lihat §7).
4. Simpan/ekspos hasil beserta basisnya.

---

## 7. Rumus & Ambang

### 7.1 Ambang (pakai ulang yang sudah ada)
Sumber: `src/ml/ml_config.py`
```
DIFFICULTY_P_EASY     = 0.70
DIFFICULTY_P_HARD     = 0.40
MIN_DIFFICULTY_SAMPLE = 20      # per soal, siswa berbeda
DIFFICULTY_MARGIN_Z   = 1.96
```

### 7.2 Agregasi & klasifikasi
```
p_materi = Σ benar (soal READY) / Σ n_siswa (soal READY)

p_materi >= 0.70  -> mudah
p_materi <  0.40  -> sulit
selainnya         -> sedang

margin = 1.96 * sqrt( p_materi * (1 - p_materi) / N )    # N = total jawaban pada soal READY
near_boundary = (p_materi - margin, p_materi + margin) memotong 0.70 atau 0.40
```

### 7.3 Syarat pelabelan materi
Materi diberi label **hanya jika**:
- jumlah soal diagnostik `READY` **≥ K** (usul **3**), dan
- jumlah **siswa berbeda** **≥ 20**.

Bila tidak → `status = INSUFFICIENT_DATA`, `label = null` (tidak mengarang).

---

## 8. Kontrak API

### 8.1 Guru — menandai soal
- `POST /api/teacher/question-bank` — terima field opsional `section_id` + `purpose`.
- `PUT  /api/teacher/question-bank/<bank_id>` — ubah `purpose` (`practice`/`diagnostic`).
- `GET  /api/teacher/practice/sections` — tambah `diagnostic_count` per bagian.

### 8.2 Guru — membaca level terukur
- `GET /api/teacher/analytics/materials/<material_id>` — tambah objek `difficulty_observed`:
```json
{
  "difficulty": "sedang",
  "difficulty_observed": {
    "status": "READY",
    "label": "mudah",
    "p": 0.573,
    "n_students": 25,
    "n_items": 3,
    "margin": 0.112,
    "near_boundary": false,
    "basis": "observed_diagnostic",
    "computed_at": "2026-10-15T10:00:00Z"
  }
}
```

### 8.3 Siswa — mode diagnostik (endpoint terpisah)
- `GET  /api/student/diagnostic/<material_id>/sections/<section_id>` — daftar soal diagnostik (tanpa kunci), urutan tetap.
- `POST /api/student/diagnostic/<material_id>/sections/<section_id>/answer` — kirim jawaban.

> Dipisah agar kontrak latihan adaptif yang ada tidak berubah. Alternatif `?mode=diagnostic`
> pada endpoint latihan lama **tidak** direkomendasikan.

---

## 9. UI

### 9.1 Guru
- **Soal Latihan per Bagian:** toggle "Diagnostik" per soal + indikator "belum cukup soal diagnostik".
- **Analitik Materi:** dua badge berdampingan — `Tingkat (deklarasi)` dan `Tingkat (terukur diagnostik)`,
  dengan keterangan sumber: "N soal, N siswa, p=…, dekat batas / data belum cukup".

### 9.2 Siswa
- Tombol **"Asesmen Diagnostik"** pada tiap bagian (non-adaptif), dengan penjelasan singkat tujuan.

---

## 10. Aturan Kejujuran (guardrail)

1. Ambang **≥ 20 siswa berbeda** dan **≥ K soal** sebelum melabeli.
2. **Jangan menimpa** label guru/seed; tampilkan berdampingan + tandai `basis`.
3. Selalu tampilkan **N, p, margin**.
4. `INSUFFICIENT_DATA` bila data kurang — bukan "sedang".
5. Satu siswa dihitung **sekali** per soal, memakai **jawaban pertama** (aturan sudah ada di
   `question_difficulty_service.aggregate_rows`).
6. Soal diagnostik **tidak** boleh ikut sesi latihan adaptif (dan sebaliknya).

---

## 11. Contoh Perhitungan

### 11.1 Contoh sintetis (1 materi, 3 soal diagnostik)
| Soal | Benar | N siswa | p |
|---|--:|--:|--:|
| Q1 | 14 | 25 | 0.56 |
| Q2 | 18 | 25 | 0.72 |
| Q3 | 11 | 25 | 0.44 |
| **Pooled** | **43** | **75** | **0.573** |

- `p_materi = 43/75 = 0.573` → **sedang** (0.40 ≤ 0.573 < 0.70)
- `margin = 1.96 * sqrt(0.573*0.427/75) ≈ 0.112` → rentang (0.461, 0.685), tidak memotong ambang → `near_boundary = false`
- `status = READY`

### 11.2 Kondisi data demo saat ini
Belum ada soal bertanda `purpose='diagnostic'` (semua soal bank ber-`section_id` dipakai sesi adaptif).
Maka dengan rancangan ini **semua materi berstatus `INSUFFICIENT_DATA`** sampai set diagnostik diisi.
(Sesuai prinsip kejujuran: tidak mengarang label.)

---

## 12. Dampak pada Data Demo

| Materi | Soal bank ber-`section_id` (saat ini) | Set diagnostik | Level terukur |
|---|--:|--:|---|
| 107 `[DEMO] VIRUS` | 38 APPROVED | 0 | `INSUFFICIENT_DATA` |
| 108 `keanekaragaman hayati` | 2 APPROVED | 0 | `INSUFFICIENT_DATA` |
| 110 `RUANG LINGKUP BIOLOGI` | 0 | 0 | `INSUFFICIENT_DATA` |
| 115 / 116 / 117 | 0 (pakai soal interaktif) | 0 | `INSUFFICIENT_DATA` |

> Untuk demo, perlu disiapkan **seed set diagnostik** (mis. 3–5 soal per bagian) agar fitur terlihat bekerja.

---

## 13. Rencana Implementasi Bertahap

| Milestone | Isi |
|---|---|
| **M1 — Backend inti** | kolom `purpose` + migrasi; `approved_for_section()` difilter ke `purpose='practice'`; fungsi `material_difficulty_observed()` + unit test |
| **M2 — Penyajian diagnostik** | endpoint siswa mode diagnostik + pencatatan jawaban |
| **M3 — API guru** | `diagnostic_count` + `difficulty_observed` pada analitik materi |
| **M4 — UI guru** | toggle diagnostik + badge level terukur |
| **M5 — UI siswa** | tombol Asesmen Diagnostik |
| **M6 — Seed demo** | set diagnostik materi demo (opsional) |

Unit test mengikuti pola yang sudah ada: `test_ml_difficulty.py`, `test_practice_drafts.py`,
`test_section_tagging.py`.

---

## 14. Keputusan yang Perlu Persetujuan Dosen

1. Definisi "level" = tingkat kesulitan (mudah/sedang/sulit), **bukan** level bertingkat 1/2/3?
2. Setuju memakai **set diagnostik per section**, terpisah dari latihan adaptif?
3. Ambang **K soal = 3** dan **≥ 20 siswa**?
4. Soal **interaktif tertanam** ikut dihitung atau tidak? (usul: **tidak**)
5. "Asesmen Diagnostik" **wajib** atau opsional bagi siswa?
6. Bila materi belum punya set diagnostik: cukup tampil `INSUFFICIENT_DATA` (tidak mengarang)?

---

## 15. Yang Tidak Dilakukan (agar tidak overclaim)

- Tidak mengklaim level materi dari jawaban latihan adaptif.
- Tidak mengarang label saat data kurang.
- Tidak menimpa label deklarasi guru.
- Tidak mengubah perilaku latihan adaptif yang berjalan (selain menyaring keluar soal diagnostik).
- **Dokumen ini belum mengubah apa pun di aplikasi.**

---

## 16. Status Implementasi & Bukti (ditambahkan 15 Okt 2026)

Semua milestone **M1–M5 sudah dikerjakan**; M6 (seed) **tidak diperlukan** karena
soal demo yang ada ditandai ulang sebagai diagnostik (lihat di bawah).

### Perubahan kode
- **Model & migrasi:** kolom `question_bank.purpose` (default `'practice'`),
  migrasi otomatis lewat `_COMPAT_COLUMNS` di `src/config/database.py`.
- **Service:** `question_difficulty_service.material_level_observed()`,
  `diagnostic_questions_for_material()`, gerbang `items`/`students`;
  `student_practice_service` (pool `approved_*` difilter `purpose='practice'`,
  `diagnostic_*` baru).
- **API siswa:** `GET/POST /api/student/diagnostic/<material_id>/sections/<section_id>[/answer]`
  (urutan tetap, non-adaptif, kunci jawaban tidak pernah dikirim).
- **API guru:** filter & CRUD `purpose`; `diagnostic_count` per section;
  `difficulty_declared` + `difficulty_observed` + `section_diagnostics` pada analitik.
- **UI:** pemilih "Jenis Soal", filter/badge bank soal, badge diagnostik + indikator
  kelayakan di Latihan per Bagian, panel "Tingkat Materi" (deklarasi vs terukur),
  tombol "Asesmen Diagnostik" + modal pengerjaan untuk siswa.

### Bukti otomatis
- `test_material_level_diagnostic.py` — **72/72 lulus**: pemisahan dua pool,
  penolakan lintas-jalur, urutan tetap, tidak ada kebocoran kunci, alasan
  `INSUFFICIENT_DATA` (`no_questions`/`items`/`students`), contoh pooled
  Bagian 11.1 (3 soal × 25 siswa, 43/75 → `p≈0.573`, `medium`, margin≈0.112).
- Suite regresi tetap hijau: `test_question_difficulty`, `test_student_practice`,
  `test_section_mastery`, `test_section_recommendations`, `test_ml_difficulty`.

### Bukti visual
- `docs/screenshots/*-sebelum.png` (15) dan `*-sesudah.png` (15), lebar 1410 px.
- `docs/laporan-before-level-materi.docx` dan `docs/laporan-after-level-materi.docx`.
- Skrip pembuat: `docs/tools/shot_*.cjs`, `docs/tools/build_docx.py`,
  `docs/tools/verify_docx.py`.

### Data demo
- Materi 107: bagian "MENGENAL VIRUS DALAM KEHIDUPAN" dan "SEJARAH, CIRI-CIRI, DAN
  STRUKTUR VIRUS" masing-masing kini punya **3 soal diagnostik** (ditandai lewat
  alur guru asli; pool latihan berkurang sesuai).
- Karena belum ada ≥ 20 siswa yang mengerjakan, level terukur material demo masih
  jujur menampilkan `INSUFFICIENT_DATA` ("Belum cukup data"), bukan label karangan.

### Perbaikan bug terkait
- `student/progress/[material_id].vue` memakai `route.params.id` (selalu
  `undefined`) sehingga halaman kosong. Diperbaiki ke `route.params.material_id`;
  perbandingan before/after halaman ini menjadi bukti nyata (805 px → 2449 px).

