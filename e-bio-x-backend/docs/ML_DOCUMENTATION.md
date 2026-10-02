# Tahap 5 — Machine Learning & Rekomendasi Belajar

Dokumentasi singkat sistem ML pada E-Bio X.

## 1. Data input ML

Data berasal dari hasil belajar siswa yang sudah direkam (Tahap 4):

- `MaterialStudentState` / `MaterialProgress` → progres materi & section
- `StudentAnswer` → jawaban soal interaktif (beserta kesulitan konten)
- `Submission` → hasil kuis (percentage, correct/wrong)
- `LearningSession` / `total_learning_seconds` → waktu belajar

Tiap siswa direpresentasikan menjadi **satu baris feature agregat** oleh
`src/ml/feature_service.py::aggregate_student_features`.

## 2. Feature engineering

Mapping DB → ML feature → fungsi:

| Feature | Fungsi |
| --- | --- |
| `material_completion_rate` | rata-rata progres materi yang dimulai (0–1) |
| `section_completion_rate` | section selesai / total section (0–1) |
| `interactive_accuracy` | jawaban interaktif benar / total |
| `quiz_average` | rata-rata persentase semua kuis |
| `quiz_best_score` | nilai terbaik kuis |
| `easy/medium/hard_accuracy` | akurasi per tingkat kesulitan soal |
| `learning_minutes` | total waktu belajar (menit) |
| `quiz_attempts` | jumlah percobaan kuis |
| `correct_rate` | benar/total (interaktif + kuis) |
| `easy/medium/hard_attempted` | **metadata, bukan feature** — jumlah soal yang benar-benar dijawab per tingkat (lihat catatan di bawah) |

`student_id` **tidak pernah** menjadi feature model — hanya identifier.
Urutan feature dijamin konsisten antar training dan prediction
(`src/ml/ml_config.py::FEATURES`, `preprocessing.Preprocessor`).

### 2.1 Normalisasi tingkat kesulitan

Kesulitan disimpan dengan dua kosakata berbeda, jadi harus dinormalkan
lebih dulu — `learning_analytics_service.normalize_difficulty()`:

| Sumber | Nilai yang disimpan | Setelah normalisasi |
| --- | --- | --- |
| `Material.difficulty` | `mudah` / `sedang` / `sulit` | `easy` / `medium` / `hard` |
| `MaterialContent.data.difficulty` | `easy` / `medium` / `hard` | apa adanya |
| `MaterialContent.data.difficulty` (lama) | `1` / `2` / `3` | `easy` / `medium` / `hard` |
| tidak dikenal / kosong | — | `None` (tidak menebak) |

Nilai yang tidak dikenali menghasilkan `None`, dan komponen yang
memerlukannya memakai nilai netral — bukan asal cocok.

Dua jebakan yang dulu membuat dimensi ini mati sepenuhnya:

- `Material.difficulty` berbahasa Indonesia, sedangkan
  `recommendation.score_material` membandingkannya dengan
  `('easy','medium','hard')`. Akibatnya `difficulty_fit` **selalu 0.5**,
  yaitu komponen bobot 0.10 yang tidak pernah berefek. Sekarang
  dinormalkan, dan nilainya benar-benar berubah (0.575 → 0.625 pada
  kasus uji).
- `analytics._difficulty_accuracy_material` pernah membaca
  `heading.level` sebagai proxy kesulitan. `level` adalah level heading
  HTML (1–6), bukan kesulitan, sehingga heading terbaca sebagai
  "kesulitan 2"/"kesulitan 3". Sekarang hanya field `difficulty` eksplisit
  yang dipakai; konten tanpa keterangan turun ke `medium`.

### 2.2 Metadata `*_attempted`

Akurasi saja tidak bisa menyatakan "belum mencoba" — akurasi 0.0 sama
untuk "tidak menjawab satu pun" dan "menjawab semuanya tetapi salah".
`_student_weak_difficulty` dulu memakai `accuracy > 0` sebagai proxy
"sudah mencoba", sehingga siswa yang menjawab seluruh soal mudah dengan
salah dianggap belum pernah mencoba tingkat mudah — persis level yang
paling perlu bantuan.

Sekarang `aggregate_student_features()` juga mengembalikan
`<level>_attempted`, dan level terklemah dicari **hanya di antara level
yang benar-benar dijawab**. Seri dipecah ke level termudah. Bila row tidak
memiliki metadata ini (mis. cache lama), fungsi mengembalikan `None`
alasan tingkat difficulties tidak diklaim sama sekali, daripada menebak
dan mengarahkan siswa ke level yang salah.

`*_attempted` sengaja **tidak** masuk `cfg.FEATURES` maupun
`cfg.KMEANS_FEATURES`, sehingga artefak model yang sudah tersimpan tetap
cocok dengan feature list. `preprocessing.impute_row()` memproyeksikan row
ke tepat `cfg.FEATURES`, jadi metadata ini otomatis diabaikan model.

## 3. Decision Tree

`src/ml/decision_tree.py`

- Model: `DecisionTreeClassifier` (shallow: `max_depth=4`,
  `min_samples_split=5`, `min_samples_leaf=3`, `class_weight=balanced`).
- Target `mastery_level`: `VERY_GOOD` / `GOOD` / `FAIR` / `NEEDS_REINFORCEMENT`
  (UI: Sangat Baik / Baik / Cukup / Perlu Penguatan).
- **Baseline labeling (transparan, bukan hasil ML):** label dihitung dari
  threshold akademik Tahap 4 yang disimpan di config
  (`MASTERY_TRUTH_ORDER`) terhadap skor komposit
  (`BASELINE_WEIGHTS`: quiz 40%, completion 30%, akurasi 30%).
- **Pencegahan label leakage:** karena label adalah fungsi deterministik
  dari `BASELINE_WEIGHTS`, ketiga feature itu **tidak boleh** jadi input
  model — kalau tidak, model bisa membaca jawaban langsung dari
  pertanyaan dan akurasi 100% tidak berarti apa pun. Definisi
  `LABEL_DEFINING_FEATURES` dan `DT_FEATURES` (15 dari 18 feature)
  mengunci aturan ini. `test_ml_leakage.py` menjaganya.
- **Evaluasi: repeated stratified cross-validation**, bukan satu split
  75/25. Pada beberapa puluh siswa, satu split bergerak liar hanya karena
  satu siswa berpindah; CV dirata-ratakan atas 5 fold × 3 ulangan.
  Dilaporkan bersama `accuracy_std`, confusion matrix, dan
  `majority_baseline` — akurasi yang tidak melampaui baseline tebakan
  "selalu pilih kelas terbanyak" ditandai eksplisit sebagai
  `PERINGATAN`, bukan disembunyikan.
- Metrik hanya dihitung bila dataset cukup (`MIN_SAMPLES_CV`); kalau tidak,
  model tetap dilatih tetapi akurasinya sengaja tidak ditampilkan agar
  tidak disalahartikan.

## 4. K-Means

`src/ml/kmeans.py` + `cluster_interpreter.py`

- Feature subset khusus clustering (`KMEANS_FEATURES`), di-`StandardScaler`.
- `K` dipilih dari rentang 2–5 menggunakan **Silhouette Score**; bila tidak
  tegas, dipakai default `K=3` yang didokumentasikan.
- Jumlah siswa terlalu sedikit → `INSUFFICIENT_DATA`.
- Nama cluster dihasilkan dari karakteristik centroid (bukan nomor
  cluster): `High Achievement`, `Active Learner`, `Moderate Learner`,
  `Needs Support`, `Low Activity`.

## 5. Recommendation engine

`src/ml/recommendation.py` — lapisan **rule-based** (bobot tidak diklaim
sebagai hasil ML):

```
score = mastery_gap(0.35) + question_error(0.25) + unfinished(0.15)
      + relevance(0.15) + difficulty_fit(0.10)
```

Prioritas: materi mastery rendah → banyak salah soal → belum selesai →
kesesuaian topik → kesesuaian tingkat kesulitan. Filter: hanya materi
`published`, dapat diakses siswa, dan bukan materi yang sudah dikuasai
sangat tinggi (≥90). Alasan selalu berasal dari data nyata siswa.

## 6. Fallback / cold-start

- Siswa baru / data belum cukup → `INSUFFICIENT_DATA`, pesan
  "Belum cukup data untuk menentukan profil belajar."
- Rekomendasi **fallback**: materi belum dimulai / sesuai kelas-fase,
  diurutkan berdasarkan perkiraan durasi, bertipe `fallback` dan
  terlabel jelas (bukan klaim personalisasi ML).
- Jika service ML gagal → fallback serupa, tidak membuat website crash.

## 7. Training — per kelas, bukan global

- Endpoint `POST /api/ml/train` dan `POST /api/ml/retrain`
  (**teacher/admin hanya**; siswa dilarang).
- Pipeline: collect data → validate dataset → prepare features → train
  DT & K-Means → evaluate → save (per-version) → prediction.
- Model **tidak** retrain saat request dashboard.

**Cakupan training mengikuti kelas yang diajar.**

||latihan|Cakupan|Disimpan sebagai|
| --- | --- | --- |
| Guru | siswa kelas guru tersebut saja | `ml_models.teacher_id = <id guru>` |
| Admin | seluruh sistem (model cadangan) | `ml_models.teacher_id = NULL` |
| Admin | tambahan: satu model per guru | `ml_models.teacher_id = <id guru>` |

Melatih secara global membuat angka kelas seorang guru dibentuk oleh
siswa yang tidak pernah diajarinya — persis hal yang pemisahan per kelas
maksudkan untuk cegah. Guru yang menekan satu tombol hanya dilatihkan
kelasnya sendiri; admin satu tombol mengisi model gabungan plus model
tiap kelas.

Kelas yang siswanya di bawah ambang **tidak** menghasilkan model, dan
hal itu dilaporkan apa adanya — bukan diisi dengan model global yang
disamarkan.

Auto-retrain (`_maybe_auto_retrain`) juga mengikuti kelas: aktivitas
seorang siswa memicu retrain model gurunya saja, tidak model guru lain.
Ia dikunci `threading.Lock` supaya lonjakan klik tidak spawning puluhan
training bersamaan, dan kegagalan di logged — bukan ditelan diam-diam
seperti sebelumnya, yang membuat kelas bisa tertinggal di model basi tanpa
ada tanda apa pun.

## 8. Prediction

- `POST /api/ml/predict/<student_id>` (teacher/admin, ownership).
- `GET /api/student/learning-profile` dan `GET /api/student/recommendations`
  (siswa, hanya data sendiri).
- Prediction memakai preprocessor + feature order yang sama persis dengan
  training (`model_manager.load_artifact`, cache).

### 8.1 Model kelas mana yang dipakai untuk seorang siswa

Seorang siswa bisa ikut lebih dari satu kelas, jadi pertanyaannya bukan
"model mana" melainkan "model siapa". Aturannya (`_load_for_student`):

1. Cari model kelas milik semua gurunya yang sudah dilatih.
2. Pilih yang **paling baru dilatih**; jika seri, ambil id guru terkecil
   supaya hasilnya sama setiap kali.
3. Kalau tidak ada satu pun model kelas, pakai model gabungan — dan
   sebutkan terus terang bahwa angkanya belum spesifik untuk kelasnya.

Setiap respons siswa membawa **dua** scope terpisah — satu untuk label
penguasaan, satu untuk nama klaster:

```json
{ "model_scope":   { "scope": "class", "teacher_id": 71,
                     "model_type": "decision_tree",
                     "note": "Model penguasaan (Decision Tree) ini dilatih dari siswa kelas Guru 1 saja." },
  "cluster_scope": { "scope": "class", "teacher_id": 71,
                     "model_type": "kmeans",
                     "note": "Model pengelompokan (K-Means) ini dilatih dari siswa kelas Guru 1 saja." },
  "model_version": 71.0, "cluster_model_version": 71.0 }
```

Decision Tree dan K-Means **dipilih secara terpisah** (masing-masing
`_newest_class_record(...)`), bukan menumpang scope DT. Kalau keduanya
diikat, sebuah klaster gabungan (atau milik kelas lain) bisa muncul di
bawah catatan scope kelas — persis fallback senyap yang ingin dicegah.

`scope: "pooled"` berarti angka itu belum menggambarkan kelas siswa
tersebut, dan UI menyatakannya begitu. Menyembunyikan asal-usul angka
justru membuat seluruh pemisahan per kelas tidak berarti.

### 8.2 Konsekuensi yang disengaja: satu siswa, dua kelas, dua jawaban

Aturan di atas bukan detail teknis tanpa dampak. Ada konsekuensi yang
sengaja diterima, dan sebaiknya diketahui sebelum demo ke pembimbing.

Dua guru yang kelasnya tumpang-tindih akan punya model berbeda, karena
masing-masing dilatih dari daftar siswanya sendiri yang **tidak sama
persis**. Siswa yang ada di keduanya bisa mendapat label sedikit berbeda
dari dua model itu.

**Kondisi nyata saat ini (76 siswa, 6 course, 2 guru ber-student):**

- 66 siswa ikut **kedua** kelas Pak Ali (course 1, 2, 4, 5) dan Guru 1
  (course 6, 9). 10 siswa hanya di Guru 1.
- Di antara 66 siswa itu:
  - **3 siswa** (Pranawa Putra, Jamal Budiyanto, Karya Mustofa) mendapat
    **label penguasaan berbeda** dari dua model — semuanya siswa yang
    nilainya pas di batas percabangan pohon.
  - **0 siswa** mendapat nama profil berbeda.
  - Nomor klaster mentah berbeda untuk semuanya, tapi **nomor itu
    arbitrer** per model dan tidak pernah ditampilkan ke pengguna, jadi
    tidak bermakna.

Jadi sekitar 4,5% siswa bisa melihat badge yang berbeda tergantung kelas
yang dipakai. Ini pertukaran yang diterima dengan sengaja, bukan bug:

| Kalau satu model untuk semua | Kalau per kelas (sekarang) |
| --- | --- |
| semua melihat label sama | 3 siswa bisa melihat label berbeda |
| angka setiap guru dipengaruhi siswa yang tidak diajarinya | angka kelas benar-benar dari kelas itu |

**Yang tidak berubah:** halaman guru selalu memakai model guru tersebut.
Guru tidak pernah melihat angka kelas guru lain, dan guru tidak bisa
memprediksi siswa luar kelasnya (403).

Kalau nanti perlu, opsi yang tersedia adalah menampilkan hasil kedua
model berdampingan, atau membiarkan guru memilih model kelas yang dipakai.
Keduanya menambah beban UI, jadi belum dilakukan.

### 8.3 Interpretasi K-Means dihitung per kelas, bukan lintas kelas

Nama klaster (`High Achievement`, `Active Learner`, ...) diturunkan dari
**centroid model itu sendiri** (`cluster_interpreter.interpret_clusters`),
bukan dari nomor klaster dan bukan dari centroid kelas lain. Karena
penilaian "aktif" atau "menguasai" dibandingkan dengan rata-rata kelas
yang sedang dilihat, nama yang sama di dua kelas **tidak dimaksudkan
untuk dibandingkan langsung**: "Active Learner" di kelas A bisa punya
rata-rata menit belajar yang berbeda dari "Active Learner" di kelas B.

Panel klaster guru membawa `training_scope`, `training_scope_note`, dan
`interpretation_note` yang menyatakan hal ini, supaya nama klaster tidak
dibaca sebagai skala global. `test_ml_scope.py` §7c mengunci aturan
resolusi terpisah ini: ia memindahkan `trained_at` satu model K-Means
kelas (tanpa menyentuh pohon), lalu memastikan label klaster mengikuti
model K-Means itu sementara label penguasaan tetap mengikuti model
Decision Tree-nya.

## 9. Model versioning & penyimpanan per kelas

- Artifact disimpan ke disk `backend/models/*.joblib` (std: joblib,
  scikit-learn). Nama file memuat scope-nya, jadi dua kelas tidak mungkin
  saling menimpa:
  - gabungan → `decision_tree_v13.0.joblib`
  - kelas guru 2 → `decision_tree_class2_v15.0.joblib`
- Metadata di tabel `ml_models`:
  model_type, model_version, feature_version, trained_at,
  training_sample_count, metrics_json, model_path, **teacher_id**.
- `teacher_id` nullable: `NULL` = model gabungan, terisi = model kelas itu.
- Nomor versi memakai **satu penghitung global**, bukan per kelas. Dua model
  dengan versi sama akan membuat "angka ini dari model mana?" ambigu,
  dan penghitung terpisah akan membuat seorang guru terlihat di v1.0
  sementara sistem sudah di v13.0.
- `metrics` hanya diisi bila evaluasi valid.
- Kolom `teacher_id` ditambahkan lewat ALTER idempotent
  (`ensure_schema_compat` di `src/config/database.py`), karena
  `create_all()` tidak pernah menyentuh tabel yang sudah ada.
- **Retensi:** setiap training menulis baris + file baru. Versi di luar
  `KEEP_VERSIONS_PER_SCOPE` (default 5) per scope dihapus —
  `prune_old_versions()`. Pruning dilakukan per scope, jadi kelas yang
  sering retrain tidak bisa menghapus model kelas lain. File dihapus
  setelah barisnya, supaya kegagalan hapus file tidak pernah meninggalkan
  baris yang menunjuk ke file yang tidak ada.
- `metrics` hanya diisi bila evaluasi valid.

## 10. Closed-loop evaluasi rekomendasi

`src/ml/recommendation_evaluation.py` + endpoint
`GET /api/ml/evaluation/recommendations` (guru/admin).

Rekomendasi menulis `clicked_at` (`mark_clicked`) dan `completed_at`
(`mark_completed`). Sebelum tahap ini, kedua kolom itu tidak pernah
dibaca — jadi bobot `REC_WEIGHTS` (§5) hanya taken on faith. Modul ini
menutup loop tersebut dengan mengukur apa yang benar-benar terjadi:

| Metrik | Isi | Kegunaan |
| --- | --- | --- |
| `funnel` | recommended → clicked → completed (CTR, completion rate) | memastikan rekomendasi memang diklik/dituntaskan |
| `calibration` | CTR per bin skor (0–0.30 / 0.30–0.45 / 0.45–0.60 / 0.60–1.00) | **menguji apakah `REC_WEIGHTS` memang berkorelasi dengan perilaku siswa** |
| `reasons` | CTR per kelompok alasan (`tinggi_kepentingan`, `banyak_salah`, `belum_selesai`, `tingkat_kesulitan`, `sudah_dikuasai`, `umum`, `lainnya`) | alasan mana yang benar-benar memengaruhi siswa |
| `completion_yield` | rerata progres materi rekomendasi vs non-rekomendasi **per siswa** | pembanding dalam-siswa (mengurangi bias "siswa yang memang lebih rajin") |
| `per_material` | CTR per materi | bahan tindak lanjut guru |

`calibration.verdict` berbunyi:

- `TERDUKUNG` — CTR naik seiring skor → bobot konsisten dengan perilaku
- `TERBALIK` — CTR turun saat skor naik → ada bobot terlalu dominan
- `TIDAK_BERATURAN` — CTR zig-zag → bobot belum terbukti
- `TIDAK_BERBEDA` — CTR nyaris sama di semua bin → **skor tidak punya daya
  pembeda sama sekali** (selisih < 0.05)

Aturan kejujuran yang dijaga modul ini:

- Semua angka **observasional, bukan kausal**. Materi direkomendasikan
  justru karena siswa kesulitan pada materi itu, sehingga penyelesaian
  tinggi belum tentu berarti rekomendasi berhasil. `note` selalu dikirim
  bersama respons.
- Bucket di bawah `EVAL_MIN_SAMPLES` (5) dilaporkan `INSUFFICIENT_DATA`
  **tanpa** menyertakan rate — tidak ada angka kecil yang menyesatkan.
- Verdict hanya dihitung bila minimal 2 bin punya sampel memadai;
  selain itu `null`, bukan tebakan.
- Reason yang tidak cocok pola mana pun masuk `lainnya`, tidak diabaikan.
- Reason yang sama tertulis dua kali dalam satu rekomendasi dihitung satu
  kali.

Scoping: guru hanya melihat siswa yang ia ajar; admin melihat sistem
penuh. Siswa tidak punya akses (403).

## 11. Privacy

| Aktor | Akses |
| --- | --- |
| Siswa | profil & rekomendasi miliknya sendiri saja |
| Guru | ML analytics scoped ke siswa di kelasnya, predict hanya siswa kelasnya, evaluasi rekomendasi hanya siswa di kelasnya, dan model yang dipakai adalah model kelasnya sendiri |
| Admin | semua |
| Cross-student | dilarang (Student A tidak bisa melihat profil Student B) |
| Cross-class | dilarang (Guru A tidak bisa memprediksi siswa kelas Guru B) |

Feature mentah tidak diekspos lewat endpoint public selain dataset
analitik yang memang diperuntukkan analisis.

Batasan kelas juga berlaku pada materi, bukan hanya pada model.
`student_accessible_materials()` adalah satu sumber kebenaran untuk daftar
materi siswa, dashboard, progres, rekomendasi, dan fitur ML. Aturannya
(`student_can_access_material`): materi yang tertaut ke course hanya untuk
siswa yang terdaftar di course itu; materi **tanpa** course link bukan
materi publik — ia milik guru pembuatnya, jadi hanya siswa kelas guru itu
yang melihatnya. Sebelumnya "tanpa course link" diperlakukan sebagai
"terlihat semua siswa", sehingga materi satu kelas muncul di dashboard,
rekomendasi, dan fitur ML kelas lain. Materi tanpa pemilik dan tanpa
course tidak terlihat siapa pun.

Materi demo yang dulu dibiarkan tanpa course link kini ditautkan ke
seluruh course gurunya lewat `link_demo_materials()` di
`scripts/seed_ml_activity.py` (idempoten), supaya tidak ada materi yang
mengambang di luar kelas. Course 6 (kelas non-demo guru yang sama) juga
ditautkan karena ada satu siswa yang terdaftar di course 6, bukan di
course demo, tetapi sudah punya state pada materi demo itu; menautkannya
ke kedua course guru membuat cakupan siswa persis sama seperti
sebelumnya, tanpa mengubah satu pun baris fitur. `verify_ml_readiness.py`
§8 menolak materi published yang masih tanpa kelas.

Model per kelas juga membatasi kebocoran secara tidak langsung: model
kelas Guru A dilatih hanya dari siswa A, jadi bobot dan batas keputusannya
tidak pernah melihat data kelas Guru B. Yang perlu dijaga adalah hal
sebaliknya — supaya Guru A tidak diberi angka yang sebenarnya berasal
dari model gabungan tanpa diberi tahu. Karena itu setiap readout
menyertakan scope-nya (§7, §8.1), dan `test_ml_scope.py` menjaganya.

Submission kuis demo pun tidak boleh menjadi angka tanpa isi. Setiap kuis
demo punya 10 soal pilihan ganda (10 poin per soal) dan setiap submission
punya satu `Answer` per soal, sehingga `percentage` = `correct_count` × 10
dapat diturunkan dari jawaban, bukan disimpan terpisah tanpa soal.
`ensure_quiz_questions()` dan `backfill_demo_quiz_content()` di
`scripts/seed_ml_activity.py` membuatnya (idempoten), mempertahankan
`correct_count` agar `correct_rate` tidak bergeser; hanya `quiz_average`
dan `quiz_best_score` yang menyesuaikan ke kelipatan 10. Karena itu model
perlu dilatih ulang setelah backfill (kasus ini menggeser label 3 dari 76
siswa).

---
File utama: `src/ml/` (feature_service, preprocessing, decision_tree,
kmeans, cluster_interpreter, profile, recommendation,
recommendation_evaluation, model_manager, ml_config),
`src/models/{ml_model,student_learning_profile,recommendation}.py`,
`src/controllers/ml_controller.py`.

## 12. Test

| File | Jumlah | Cakupan |
| --- | --- | --- |
| `test_ml_unit.py` | 32 | feature, model, versioning |
| `test_ml_rec_eval.py` | 48 | closed-loop evaluasi + auth & privacy |
| `test_ml_difficulty.py` | 66 | normalisasi kesulitan + metadata `*_attempted` |
| `test_ml_leakage.py` | 45 | pencegahan label leakage |
| `test_ml_scope.py` | 95 | training & pembacaan per kelas, aturan siswa multi-kelas, scope K-Means independen dari DT, akses materi per kelas, retensi versi, auto-retrain per kelas, cross-class privacy |

Total 286. Plus `test_tahap5_ml.py` (e2e, butuh server hidup).

Sebelum demo, jalankan `scripts/verify_ml_readiness.py` — gerbang
siap-tayang yang memeriksa data, skema artefak, kejujuran metrik, privasi
endpoint, scoping per kelas, akses materi per kelas (termasuk menolak
materi published yang mengambang tanpa kelas), integritas soal/jawaban
kuis (skor harus dapat diturunkan dari jawaban), dan integritas klaim
(rekomendasi berbasis aturan tidak boleh berlabel `ml` maupun distempel
versi model) sekaligus. Saat ini 59 pemeriksaan.