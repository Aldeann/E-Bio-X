# Spesifikasi Kriteria Tingkat Pemahaman Murid (Kriteria Murid)

> Dokumen ini menjelaskan **apa yang dimaksud "tingkat pemahaman murid/kriteria murid"** dalam sistem E-Bio-X berdasarkan implementasi yang sebenarnya. Ditulis secara faktual (apa yang ada, bukan apa yang diimajinasikan). Dua lapisan penilaian pemahaman dibedakan dengan jelas: **penguasaan per-bagian (section mastery)** dan **profil belajar berbasis ML (learning profile)**.

## 1. Ringkasan

Sistem memiliki dua cara untuk mengukur "tingkat pemahaman murid":

1. **Diagnosis penguasaan per-bagian (rule-based, transparan)** — dihitung dari jawaban nyata (kuis, interaktif, latihan) per `section` materi. Ini yang muncul di halaman progres siswa, analitik guru per materi, dan daftar bagian. Label-nya: **Kurang / Cukup / Baik / Baik Sekali** (skala 0–100). Sumber kebenaran: `learning_analytics_service.mastery_info()`, `section_mastery_for_student()`.
2. **Profil belajar (ML)** — klasifikasi penguasaan siswa secara agregat (Decision Tree) + pengelompokan perilaku belajar (K-Means). Label penguasaan ML: **Perlu Penguatan / Cukup / Baik / Sangat Baik** (UI). Label kelompok (cluster): **Pencapaian Tinggi / Pembelajar Aktif / Pembelajar Sedang / Perlu Pendampingan / Aktivitas Rendah**. Sumber: `src/ml/profile.py`, `ml_controller.get_student_learning_profile()`, UI dashboard siswa & halaman ML Insights guru.

Kedua lapisan ini **tidak selalu memberikan label yang persis sama untuk siswa yang nilainya di ambang** (sengaja, karena scope/cakupan berbeda). Hal ini didokumentasikan dan dijaga oleh pengujian.

## 2. Kriteria Penguasaan Per-Bagian (Section Mastery) — Rule-Based

### 2.1 Definisi
Tingkat pemahaman suatu **bagian (section)** materi diukur dari rasio jawaban benar vs total jawaban **nyata** yang bisa dibuktikan asal-usulnya (per section).

### 2.2 Sumber Jawaban (tidak mengarang)
Tiga sumber dihitung terpisah, hanya bila ter-tag ke section:

| Sumber | Tabel | Penentu `section_id` |
|---|---|---|
| Kuis | `Answer` → `Question` → `Submission` → `Quiz` | `Question.section_id`. Jika soal tidak bertag tapi kuis punya `Quiz.section_id`, jawaban dialokasikan ke section kuis (aturan eksplisit, bukan tebakan). |
| Interaktif | `StudentAnswer` | `StudentAnswer.section_id` |
| Latihan | `PracticeAnswer` | `PracticeAnswer.section_id` (jawaban **terakhir per soal**, bukan semua percobaan) |

Aturan kejujuran:
- Hanya `Submission.status = 'submitted'` yang dihitung (kuis in-progress diabaikan).
- `Answer.is_correct IS NULL` diabaikan.
- Soal tanpa tag section **dan** kuis tanpa `section_id` **tidak** dipetakan (lebih baik tidak dihitung daripada menebak).
- Latihan memakai jawaban terakhir per soal (`latest_attempts`).

### 2.3 Ambang Minimum (Jujur, Tidak Mengarang)
`MIN_SECTION_SAMPLE = 3` (konfigurasi terpusat).

| Kondisi | `status` | `score` | `mastery` (label) | `note` |
|---|---|---|---|---|
| `answered >= 3` | `READY` | `correct/answered*100` (bulat 1 desimal) | dihitung oleh `mastery_info(score)` | `null` |
| `answered < 3` | `INSUFFICIENT_DATA` | `null` | `null` | `"Butuh minimal 3 jawaban; baru N."` |

**Prinsip:** bila belum cukup bukti (data kurang), sistem **tidak mengarang skor**. Hitungan mentah (`answered`, `correct`, `wrong`, breakdown per sumber) tetap ditampilkan.

### 2.4 Label Mastery (Per-Bagian & Ringkasan Materi)
`mastery_info(score)` (backend `learning_analytics_service.py`):

| Rentang Skor | Label (ID/Indonesia) |
|---|---|
| 90 – 100 | **Baik Sekali** |
| 75 – 89 | **Baik** |
| 60 – 74 | **Cukup** |
| 0 – 59 | **Kurang** |

Ringkasan penguasaan materi (`mastery_score` di halaman progres siswa) dihitung sebagai **rata-rata dari bagian yang `READY` saja**. Jika **tidak ada** bagian yang cukup data, `mastery_status = 'INSUFFICIENT_DATA'` dan nilai `null` (UI menampilkan "Data belum cukup", bukan angka).

### 2.5 Endpoint Terkait
- Siswa: `GET /api/student/sections/<material_id>` → diagnosis per-bagian (termasuk status READY/INSUFFICIENT_DATA dan breakdown sumber).
- Progres siswa: `GET /api/student/progress/<material_id>` → ringkasan mastery materi (hanya rata-rata bagian READY).

## 3. Profil Belajar (Learning Profile) — ML (Decision Tree + K-Means)

Lapisan ini memberikan **profil belajar teragregasi per siswa** (bukan per-bagian). Digunakan untuk rekomendasi personal dan ditampilkan di dashboard siswa serta ML Insights guru.

### 3.1 Decision Tree — Klasifikasi Tingkat Penguasaan (Agregat)

- Model: `DecisionTreeClassifier`, shallow (`max_depth=4`, `min_samples_split=5`, `min_samples_leaf=3`, `class_weight='balanced'`).
- Label target (baseline labeling, **transparan, bukan hasil ML yang diimprovisasi**): dihitung dari aturan akademik Tahap 4 berdasarkan skor komposit 0–100 dengan bobot:
  - `quiz_average` 40%
  - `material_completion_rate` 30%
  - `interactive_accuracy` 30%

Label target (internal): `VERY_GOOD / GOOD / FAIR / NEEDS_REINFORCEMENT`. Mapping ke UI:

| Kunci Internal | Label UI (Indonesia) |
|---|---|
| `VERY_GOOD` | **Sangat Baik** |
| `GOOD` | **Baik** |
| `FAIR` | **Cukup** |
| `NEEDS_REINFORCEMENT` | **Perlu Penguatan** |

**Pencegahan label leakage (sengaja keras):** ketiga fitur pembentuk label (`quiz_average`, `material_completion_rate`, `interactive_accuracy`) **dikeluarkan** dari input Decision Tree (`cfg.DT_FEATURES` = semua `FEATURES` minus `LABEL_DEFINING_FEATURES`). Artinya model belajar dari bukti independen (mis. akurasi per tingkat kesulitan, aktivitas forum, waktu belajar, dll.), bukan membaca label-nya sendiri.

**Evaluasi jujur:** menggunakan _repeated stratified cross-validation_ (5 fold × 3 ulangan), melaporkan `accuracy_std`, confusion matrix, dan `majority_baseline`. Jika model tidak mengalahkan baseline kelas mayoritas, hasilnya dicatat sebagai peringatan (tidak disembunyikan). Metrik hanya dihitung bila dataset cukup (`MIN_SAMPLES_CV`); model tetap dilatih tapi akurasi sengaja tidak ditampilkan bila evaluasi tidak reliable.

**Status hasil profile siswa:**
- `READY` — cukup data + model tersedia; label mastery ML bisa ditampilkan.
- `INSUFFICIENT_DATA` — belum cukup sinyal agregat untuk membentuk baris feature (lihat §3.3).
- `MODEL_UNAVAILABLE` — model penguasaan belum tersedia/dilatih untuk scope yang relevan.

### 3.2 K-Means — Pengelompokan (Learning Profile Groups)

Clustering bertujuan mengelompokkan pola belajar (bukan menilai benar/salah). Fitur subset `KMEANS_FEATURES` (subset terpilih dari FEATURES), dinormalisasi dengan StandardScaler.

Pemilihan K: `K in {2,3,4,5}` dengan **Silhouette Score**; jika tidak tegas, default `K=3` (didokumentasikan). Jika < `MIN_SAMPLES_KMEANS` siswa → status `INSUFFICIENT_DATA`.

**Nama cluster diturunkan dari centroid, bukan nomor cluster.** Karena nomor cluster bisa berubah antar-run, nama **selalu** dihitung dari data aktual centroid (komposit penguasaan + aktivitas belajar). Label cluster (UI Indonesia):

| Label Internal | Label UI (Indonesia) | Deskripsi ringkas |
|---|---|---|
| `High Achievement` | **Pencapaian Tinggi** | Penguasaan materi dan hasil kuis tinggi. |
| `Active Learner` | **Pembelajar Aktif** | Sangat aktif belajar (waktu/intensitas tinggi), penguasaan masih bisa ditingkatkan. |
| `Moderate Learner` | **Pembelajar Sedang** | Performa belajar pada tingkat menengah. |
| `Needs Support` | **Perlu Pendampingan** | Membutuhkan pendampingan dan penguatan materi. |
| `Low Activity` | **Aktivitas Rendah** | Aktivitas belajar masih rendah. |

**Penting (catatan interpretasi):** Nama cluster dibandingkan terhadap **rata-rata kelas model tersebut** (per scope training). Jadi "Pembelajar Aktif" di satu kelas tidak dimaksudkan untuk dibandingkan langsung dengan kelas lain. Selain itu, karena penamaan cluster menggunakan yardstick komposit yang sama dengan baseline labeling DT (tiga fitur yang sama), **label cluster dan label mastery DT bukan bukti independen** — keduanya bisa berkorelasi dan tidak boleh dibaca sebagai saling menguatkan tanpa menyebutkan korelasi itu.

### 3.3 Kriteria "Cukup Data" untuk Profil ML

`aggregate_student_features(student)` (`feature_service.py`) hanya menghasilkan baris feature jika **jumlah sinyal minimum** terpenuhi:

`signals = (jumlah jawaban interaktif) + (jumlah kuis ter-submit yang punya percentage) + (jumlah section yang completed) >= MIN_SIGNALS_FOR_STUDENT`

(default konfigurasi `MIN_SIGNALS_FOR_STUDENT = 3`). Jika < ambang → `aggregate_student_features` mengembalikan `None` → `generate_profile` mengembalikan `{'status':'INSUFFICIENT_DATA', 'message':'Belum cukup data untuk menentukan profil belajar.'}`. Sistem **tidak mengarang** baris feature dalam kondisi ini.

### 3.4 Scope Model (Kelas vs Pooled) — Transparan ke Pengguna

Model dilatih **per kelas (per guru)**, bukan global. Seorang siswa bisa terdaftar di beberapa kelas; aturan pemilihan model untuk endpoint siswa (`_load_for_student`):

1. Cari model kelas milik semua guru yang mengajar siswa tersebut (DT dan K-Means terpilih terpisah).
2. Pilih yang **paling baru dilatih** (jika seri, ambil teacher_id terkecil untuk konsistensi).
3. Jika tidak ada model kelas → pakai **model gabungan (pooled)** dan status scope dinyatakan dengan jelas.

**Setiap respons profil siswa menyertakan scope secara eksplisit:**

```json
{
  "model_scope":   { "scope": "class" | "pooled", "teacher_id": <id>|null, "model_type":"decision_tree", "note":"..." },
  "cluster_scope": { "scope": "class" | "pooled", "teacher_id": <id>|null, "model_type":"kmeans", "note":"..." },
  "model_version": <ver>, "cluster_model_version": <ver>
}
```

UI (dashboard siswa) menampilkan:
- Badge `Penguasaan: <mastery_label>` (DT)
- Badge `Cluster: <cluster_label>` (K-Means) — jika berbeda scope dari DT, UI menampilkan catatan terpisah (`cluster_scope.note`) agar asal-usulnya tidak disamarkan.
- Faktor-faktor utama yang mempengaruhi prediksi DT (`profile.factors`) — berasal dari feature importance model + rata-rata kelas saat training (data-backed, bukan tebakan).

**Catatan implikasi (sengaja diterima):** karena model berbeda per kelas, siswa yang berada di kelas tumpang-tindih bisa mendapatkan label mastery ML sedikit berbeda tergantung kelas/model yang terpilih saat itu. Ini adalah trade-off yang disengaja untuk menjaga bahwa angka kelas benar-benar berasal dari kelas itu (bukan tercampur siswa kelas lain). Asal-usul model selalu dinyatakan secara transparan.

## 4. Perbedaan Kunci antara Kedua Lapisan

| Aspek | Section Mastery (Rule-based) | Learning Profile (ML) |
|---|---|---|
| **Granularitas** | Per **bagian (section)** materi | Per **siswa** (agregat lintas-materi/aktivitas) |
| **Sumber data** | Jawaban ter-tag per section (kuis/interaktif/latihan). Hanya data terverifikasi bisa dipetakan ke section. | Agregat seluruh aktivitas belajar siswa (progres materi/section, kuis, interaktif, waktu belajar, forum, penjelasan AI, dll.) |
| **Ambang bukti** | `answered >= 3` per section → READY, else `INSUFFICIENT_DATA` (tanpa mengarang). | Butuh sinyal agregat minimum (`MIN_SIGNALS_FOR_STUDENT >= 3`) → `INSUFFICIENT_DATA` jika kurang. |
| **Label mastery** | **Kurang / Cukup / Baik / Baik Sekali** (0–100) | **Perlu Penguatan / Cukup / Baik / Sangat Baik** (DT) |
| **Penentuan** | Aturan deterministik (transparan, bisa diaudit). | Decision Tree (dilatih dengan baseline transparan + pencegahan leakage). |
| **Kelompok belajar** | Tidak ada | Ada (K-Means) dengan 5 label terinterpretasi dari centroid. |
| **Kegunaan utama** | Diagnosis presisi "bagian mana yang sudah cukup terkuasai siswa?" (untuk belajar terarah per-bagian). | Gambaran profil belajar teragregat + rekomendasi personal; juga digunakan untuk insight kelas (ML Insights). |

## 5. UI yang Menampilkan Kriteria Ini

| Tempat | Apa yang ditampilkan | Sumber Lapisan |
|---|---|---|
| **Dashboard Siswa** (`/student/dashboard`) | Badge "Penguasaan: <mastery_label>" + badge cluster + faktor utama DT + catatan scope model (jika scope berbeda). | Learning Profile (DT + K-Means) + `get_student_learning_profile()` |
| **Progres Materi Siswa** (`/student/progress/[material_id]`) | Ringkasan mastery materi (hanya rata-rata bagian READY) + tabel mastery per-bagian (label Kurang/Cukup/Baik/Baik Sekali, status READY/INSUFFICIENT_DATA). | Section Mastery (`section_mastery_for_student`, `mastery_info`) |
| **Halaman Siswa per Materi** (detail materi) | Mastery per-bagian saat siswa melihat bagian tertentu (berdasarkan section mastery). | Section Mastery |
| **Analytics Guru — Per Materi** (`/teacher/analytics/index`) | Tabel "Mastery per Bagian" per materi (label + skor jika READY, else "Data belum cukup"). | Section Mastery (class-level) |
| **Analytics Guru — ML Insights** (`/teacher/analytics/ml`) | Distribusi mastery (DT: Sangat Baik/Baik/Cukup/Perlu Penguatan), distribusi cluster, karakteristik cluster, dan scope training. | Learning Profile (DT + K-Means) terlatih per-kelas |
| **Detail Siswa (Guru)** (`/teacher/analytics/students/[id]`) | Mastery per-bagian/material untuk siswa tersebut (label Kurang/Cukup/Baik/Baik Sekali). | Section Mastery |

## 6. Catatan Kejujuran (Anti-Overclaim)

- **Tidak ada angka yang dikarang.** Jika bukti < ambang → `INSUFFICIENT_DATA`, skor `null`, UI menyatakan "Data belum cukup"/catatan ambang.
- **Label leakage dicegah secara eksplisit.** DT tidak melihat fitur pembentuk label; ini dijaga oleh konfigurasi dan test (`test_ml_leakage.py`).
- **Scope model dinyatakan terbuka.** Dashboard siswa menampilkan `model_scope.note` dan `cluster_scope.note` terpisah bila scope berbeda (bukan disamarkan).
- **Cluster name ≠ bukti independen.** Nama cluster dan label mastery DT berbagi yardstick komposit yang sama; keduanya tidak boleh dipresentasikan sebagai konfirmasi independen.
- **Per-kelas vs pooled diumumkan.** Jika model yang dipakai adalah pooled (gabungan) karena kelas belum punya model terlatih, hal itu dinyatakan eksplisit di UI.

## 7. Kesimpulan

**"Tingkat pemahaman murid/kriteria murid"** dalam sistem ini terdiri dari:

1. **Kriteria berbasis bukti terverifikasi per-bagian** (deterministik): **Kurang (0–59), Cukup (60–74), Baik (75–89), Baik Sekali (90–100)**, dengan syarat minimum 3 jawaban ter-tag per section. Ini adalah ukuran pemahaman yang paling presisi dan transparan untuk tindak lanjut belajar per-bagian.
2. **Kriteria berbasis profil belajar teragregat (ML)**: **Perlu Penguatan, Cukup, Baik, Sangat Baik** (DT) ditambah **5 tipe kelompok belajar** (K-Means). Ini adalah ringkasan profil untuk personalisasi rekomendasi, dengan scope model diumumkan secara transparan.

Keduanya adalah "kriteria murid" yang sah, tetapi berbeda cakupan dan tujuan. Yang ditampilkan tergantung konteks tampilan (per-bagian vs profil teragregat).