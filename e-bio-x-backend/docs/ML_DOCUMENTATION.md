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

`student_id` **tidak pernah** menjadi feature model — hanya identifier.
Urutan feature dijamin konsisten antar training dan prediction
(`src/ml/ml_config.py::FEATURES`, `preprocessing.Preprocessor`).

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
- Evaluasi hanya dihitung bila ada test set; jika dataset terlalu kecil
  dilaporkan `INSUFFICIENT_DATA`, bukan angka palsu.

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

## 7. Training

- Endpoint `POST /api/ml/train` dan `POST /api/ml/retrain`
  (**teacher/admin hanya**; siswa dilarang).
- Pipeline: collect data → validate dataset → prepare features → train
  DT & K-Means → evaluate → save (per-version) → prediction.
- Model **tidak** retrain saat request dashboard.

## 8. Prediction

- `POST /api/ml/predict/<student_id>` (teacher/admin, ownership).
- `GET /api/student/learning-profile` dan `GET /api/student/recommendations`
  (siswa, hanya data sendiri).
- Prediction memakai preprocessor + feature order yang sama persis dengan
  training (`model_manager.load_artifact`, cache).

## 9. Model versioning

- Artifact disimpan ke disk `backend/models/*.joblib` (std: joblib,
  scikit-learn).
- Metadata di tabel `ml_models`:
  model_type, model_version, feature_version, trained_at,
  training_sample_count, metrics_json, model_path.
- `metrics` hanya diisi bila evaluasi valid.

## 10. Privacy

| Aktor | Akses |
| --- | --- |
| Siswa | profil & rekomendasi miliknya sendiri saja |
| Guru | ML analytics scoped ke siswa di kelasnya, predict hanya siswa kelasnya |
| Admin | semua |
| Cross-student | dilarang (Student A tidak bisa melihat profil Student B) |

Feature mentah tidak diekspos lewat endpoint public selain dataset
analitik yang memang diperuntukkan analisis.

---
File utama: `src/ml/` (feature_service, preprocessing, decision_tree,
kmeans, cluster_interpreter, profile, recommendation, model_manager,
ml_config), `src/models/{ml_model,student_learning_profile,recommendation}.py`,
`src/controllers/ml_controller.py`.