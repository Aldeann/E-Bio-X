# ============================================================
# TAHAP 5 - Machine Learning configuration.
# All thresholds/weights live here so training, prediction and
# recommendation use ONE source of truth (reproducibility).
# ============================================================

import os

# --- Feature engineering (per-student aggregate) -------------
# Order MUST never change between training and prediction.
FEATURES = [
    'material_completion_rate',
    'section_completion_rate',
    'interactive_accuracy',
    'quiz_average',
    'quiz_best_score',
    'easy_accuracy',
    'medium_accuracy',
    'hard_accuracy',
    'learning_minutes',
    'quiz_attempts',
    'correct_rate',
    'forum_posts_count',
    'forum_replies_count',
    'forum_questions_asked',
    'forum_answers_given',
    'forum_reactions_received',
    'ai_explanations_viewed',
    'ai_explanations_helpful',
]

# Features used by K-Means clustering (subset of FEATURES).
KMEANS_FEATURES = [
    'material_completion_rate',
    'learning_minutes',
    'interactive_accuracy',
    'quiz_average',
    'quiz_best_score',
    'easy_accuracy',
    'medium_accuracy',
    'hard_accuracy',
]

# Static identifier (never a model feature).
ID_COLUMN = 'student_id'

# --- Preventing label leakage -----------------------------------
# The training label is produced by baseline_label(), which is a
# deterministic function of BASELINE_WEIGHTS below. Every feature used
# to build that label is therefore also an ANSWER to the question the
# model is asked. Feeding those features to the tree lets it read the
# label straight off the input, which is why the pipeline used to
# report a perfect 100% accuracy that meant nothing.
#
# The fix keeps the rule-based definition of "mastery" (it is the
# product requirement, not something ML should invent) and removes
# those three columns from the model's INPUT. The tree must then find
# INDEPENDENT evidence for the same judgement - from quiz_best_score,
# section_completion_rate, difficulty accuracies, forum activity and
# so on. The accuracy that results is finally a real number.
LABEL_DEFINING_FEATURES = (
    'quiz_average',
    'material_completion_rate',
    'interactive_accuracy',
)

# What the Decision Tree actually sees. Kept derived from FEATURES so
# adding a feature automatically routes it to the right place.
DT_FEATURES = [f for f in FEATURES if f not in LABEL_DEFINING_FEATURES]

# --- Baseline labeling (transparent, non-ML) -----------------
# Used ONLY to build the initial labelled dataset. These are the same
# academic thresholds that were introduced in Tahap 4, stored as config.
# TRUTH_ORDER: list of (key, min_score_from) sorted descending.
MASTERY_TRUTH_ORDER = [
    ('VERY_GOOD', 90),
    ('GOOD', 75),
    ('FAIR', 60),
    ('NEEDS_REINFORCEMENT', 0),
]

# UI mapping (Indonesian).
MASTERY_UI = {
    'VERY_GOOD': 'Sangat Baik',
    'GOOD': 'Baik',
    'FAIR': 'Cukup',
    'NEEDS_REINFORCEMENT': 'Perlu Penguatan',
}

# Baseline composite that produces a 0..100 mastery score used ONLY for
# labelling. Weights are documented, not learned from ML.
BASELINE_WEIGHTS = {
    'quiz_average': 0.40,
    'material_completion_rate': 0.30,
    'interactive_accuracy': 0.30,
}

# --- Data quality -------------------------------------------------
MIN_SIGNALS_FOR_STUDENT = 3     # unique signals: answered q + quiz attempts + completed sections
MIN_SAMPLES_DT = 15             # below this: cannot train Decision Tree -> INSUFFICIENT_DATA
MIN_SAMPLES_CV = 20             # below this: cannot evaluate reliably -> metrics withheld
SPLIT_TEST_SIZE = 0.25          # kept for backwards compatibility only
MIN_SAMPLES_KMEANS = 15         # below this: cannot cluster -> INSUFFICIENT_DATA
K_RANGE = [2, 3, 4, 5]
DEFAULT_KMEANS_K = 3            # documented default when silhouette is not decisive
KMEANS_RANDOM_STATE = 42

# --- Model evaluation (honest) ------------------------------------
# A single 75/25 split on a few dozen students is mostly luck: moving
# one student can swing accuracy by 20 points. Repeated stratified
# cross-validation is averaged over many resamples instead, and every
# fold sees every class.
CV_FOLDS = 5
CV_REPEATS = 3
CV_RANDOM_STATE = 42
MIN_CLASS_FOR_CV = 2            # a class thinner than this cannot be stratified

# --- Decision Tree hyper-parameters ------------------------------
# Kept shallow on purpose: explainable, low overfit risk.
DT_PARAMS = {
    'max_depth': 4,
    'min_samples_split': 5,
    'min_samples_leaf': 3,
    'random_state': 42,
    'class_weight': 'balanced',
}

# --- Recommendation engine (rule-based layer, transparent) -------
REC_WEIGHTS = {
    'mastery_gap': 0.35,
    'question_error': 0.25,
    'unfinished': 0.15,
    'relevance': 0.15,
    'difficulty_fit': 0.10,
}
REC_MAX_RESULTS = 5
REC_MIN_SCORE = 0.10
HIGH_MASTERY_CUTOFF = 90        # materials above this are considered mastered
FALLBACK_RESULTS = 5

# Ambang "cukup baik" untuk BAHASA alasan saja, bukan ambang peringkat.
REC_PASS_SCORE = 75

# --- Recommendation per SECTION (Fase 3e) --------------------------
# Same spirit as REC_WEIGHTS: hand-set, transparent, and NOT learned.
#
# Only sections whose mastery is genuinely READY (>= MIN_SECTION_SAMPLE
# answers) get ranked. A section below that threshold cannot be ordered
# honestly - we do not know the student's level there - so it is reported
# with its raw counts and score=None instead of being handed a made-up
# priority. `section_unstarted` is deliberately absent: every ranked
# section has answers by construction, so such a term would always be 0.
REC_SECTION_WEIGHTS = {
    'section_mastery_gap': 0.60,
    'section_error': 0.40,
}
REC_SECTION_MAX_RESULTS = 4      # ranked sections surfaced to the student
REC_SECTION_HINTS = 2            # unranked sections reported as "belum cukup bukti"

# --- Pengulangan terjadwal / recency (Tahap 3) ----------------------
# Mencegah menyuruh mengulang bagian yang BARU saja dilatih (cooldown), dan
# menaikkan prioritas bagian lemah yang sudah lama tidak disentuh (lupa).
# Faktor dipakai sebagai PENGALI skor di score_section; netral (1.0) bila
# tidak ada data latihan untuk bagian itu sama sekali - tidak mengarang.
REC_COOLDOWN_HOURS = 20          # < sekian jam sejak latihan terakhir -> "ulangi besok"
REC_STALE_DAYS = 7               # >= sekian hari tanpa latihan -> prioritas naik
REC_COOLDOWN_FACTOR = 0.80       # bagian baru dilarin dan masih lemah
REC_STALE_BOOST = 1.05           # bagian lemah lama tak disentuh

# --- Knowledge graph prasyarat (Fase 4e) --------------------------
# Bagian yang prasyaratnya sudah TERBUKTI belum tuntas diturunkan
# prioritasnya (faktor < 1) supaya bagian dasarnya lebih dulu muncul di
# daftar saran. Ini mengubah tampilan hanya ketika ada bukti pasti.
#
# Status `prerequisite_met is None` (prasyarat belum bisa dinilai - data
# kurang atau di luar akses) SENGAJA netral: menurunkan prioritas atas dasar
# ketidaktahuan sama saja dengan mengarang penilaian, prinsip yang sama
# dengan `score=None` di atas.
REC_SECTION_UNMET_PREREQ_FACTOR = 0.5

# --- Analisis tingkat soal otomatis dari performa (Fase 3f) ---------
# Tingkat kesulitan soal TIDAK ditebak dari teks dan tidak menunggu label
# guru: diukur dari p-value (fraksi benar) jawaban nyata. Aturannya:
#   - p >= DIFFICULTY_P_EASY                    -> mudah
#   - p <  DIFFICULTY_P_HARD                    -> sulit
#   - selain itu                                -> sedang
#   - butuh >= MIN_DIFFICULTY_SAMPLE siswa BERBEDA (dihitung sekali per
#     siswa, memakai jawaban pertama; setelah leave-one-out untuk tampilan
#     siswa) sebelum berani memberi label; di bawah ambang -> INSUFFICIENT_DATA,
#     tidak ada label yang diklaim.
#   - selisih margin (CI 95%, aproksimasi normal) selalu dilaporkan; bila
#     rentang p +/- margin memotong garis batas, label ditandai "dekat
#     batas", bukan dianggap pasti.
DIFFICULTY_P_EASY = 0.70
DIFFICULTY_P_HARD = 0.40
MIN_DIFFICULTY_SAMPLE = 20
DIFFICULTY_MARGIN_Z = 1.96

# --- Sesi latihan adaptif (Fase 3f) ---------------------------------
# Komposisi satu sesi latihan: 60% tingkat sasaran (terlemah siswa), 30%
# satu tingkat di bawah sasaran (fondasi), 10% satu tingkat di atas
# (tantangan). Sifatnya mengatur URUTAN soal yang SUDAH ADA di bagian itu
# (hanya status APPROVED); tidak ada soal baru yang dibuat di sini.
SESSION_MIX_TARGET = 0.60
SESSION_MIX_BELOW = 0.30
SESSION_MIX_ABOVE = 0.10
SESSION_LEVEL_ORDER = ['easy', 'medium', 'hard']

# --- Tujuan & status keluar sesi latihan (Fase 3 lanjutan) -----------
# Sebuah bagian dianggap "tuntas" bila siswa sudah menjawab minimal
# PRACTICE_MIN_SAMPLE soal latihan (jawaban terakhir per soal) dengan
# akurasi >= PRACTICE_PASS_SCORE. Nilai SENGAJA sama dengan
# REC_PASS_SCORE / MIN_SECTION_SAMPLE supaya rekomendasi dan sesi latihan
# berbicara dengan ambang yang sama. Di bawah ambang, statusnya hanya
# "sedang berlatih" - tidak ada klaim tuntas.
PRACTICE_PASS_SCORE = 75
PRACTICE_MIN_SAMPLE = 3

# --- Tujuan & aturan keluar sesi latihan (Fase 3 lanjutan) -----------
# Satu bagian dianggap TUNTAS bila siswa sudah menjawab minimal
# PRACTICE_PASS_MIN soal latihan bagian itu dengan akurasi >=
# PRACTICE_PASS_SCORE. Di bawah ambang, status hanya "sedang berlatih" -
# tidak ada klaim tuntas. Angka ini dipakai HANYA untuk bahasa status/next
# step di sesi latihan, bukan untuk mengarang skor penguasaan.
PRACTICE_PASS_SCORE = 75
PRACTICE_PASS_MIN = 3

# --- Fokus miskonsepsi (Tahap 2) ------------------------------------
# Label miskonsepsi terlemah siswa pada suatu bagian hanya mengubah URUTAN
# soal DI DALAM tiap tingkat sesi (komposisi 60/30/10 tetap). Label dipakai
# diam-diam oleh server untuk menyusun sesi; payload sesi TIDAK memuat teks
# label (bisa membocorkan konsep benar), hanya agregat angka.
FOCUS_MIN_SAMPLE = 2      # minimal soal terjawab pada satu label
FOCUS_LABEL_MAXLEN = 160  # pemotongan teks label untuk pencocokan/tampilan

# --- Next Best Action (Fase 5) --------------------------------------
# Satu "langkah berikutnya" yang diprioritaskan server, dihitung dari sinyal
# yang SUDAH ada (penguasaan bagian, progres baca, ketersediaan latihan,
# kuis, dan kebaruan latihan). Tidak ada model dan tidak ada ranker kedua:
# NBA hanya MEMILIH satu aksi dari kandidat, memakai bobot dasar di bawah.
# Bobot lebih besar = lebih didahulukan. Semua transparan dan bisa diaudit.
NBA_WEIGHTS = {
    'practice_weak': 1.00,        # bagian terbukti lemah & soal latihannya ada
    'practice_after_read': 0.90,  # bagian sudah dibaca tapi belum pernah dilatih
    'continue_reading': 0.70,     # lanjutkan bagian berikutnya pada materi aktif
    'take_quiz': 0.55,            # kuis tertunda untuk bagian/materi yang dibaca
    'start_next_material': 0.45,  # mulai materi berikutnya (materi aktif selesai)
    'review_mastered': 0.25,      # ulangi (spaced) bagian yang sudah tuntas
    'done': 0.00,                 # tidak ada aksi jujur yang bisa disarankan
}
# Dorongan kecil bila halaman yang meminta sedang menyorot satu materi/bagian,
# supaya saran "nyambung" dengan apa yang sedang dibuka siswa.
NBA_CONTEXT_MATERIAL_BOOST = 0.15
NBA_CONTEXT_SECTION_BOOST = 0.10
# Ambang kesegaran latihan untuk "ulangi bagian yang sudah tuntas".
NBA_REVIEW_STALE_DAYS = 14

# --- Recommendation closed-loop evaluation -----------------------
# The recommendation events (clicked_at / completed_at) are already
# recorded by recommendation.mark_clicked / mark_completed. These
# settings govern the OFFLINE evaluation that reads them back, so the
# hand-tuned REC_WEIGHTS above can be checked against real outcomes
# instead of being taken on faith.
#
# Everything here is OBSERVATIONAL. Nothing in this section claims
# causality: a material can be recommended *because* the student is
# struggling, so a high completion rate may reflect an easy material,
# not a good recommendation. Reports must state this.
EVAL_MIN_SAMPLES = 5            # per bucket; below -> bucket reported as insufficient
EVAL_MIN_STUDENTS = 3           # below -> within-student lift not reported

# recommendation_score range is 0..1 (sum of REC_WEIGHTS), so these
# bins cover the whole range. Used for calibration: does a higher score
# actually produce a higher click rate?
EVAL_SCORE_BINS = [
    (0.00, 0.30, 'rendah'),
    (0.30, 0.45, 'menengah'),
    (0.45, 0.60, 'tinggi'),
    (0.60, 1.01, 'sangat_tinggi'),
]

# Textual reasons are free-form; group them into interpretable buckets
# so a single wording change does not fragment the statistics.
EVAL_REASON_GROUPS = [
    ('tinggi_kepentingan',
     ['Penguasaan materi masih', 'perlu penguatan']),
    ('banyak_salah',
     ['salah', 'kesalahan']),
    ('belum_selesai',
     ['belum selesai']),
    ('tingkat_kesulitan',
     ['tingkat']),
    ('sudah_dikuasai',
     ['sudah dikuasai']),
    ('umum',
     ['Direkomendasikan berdasarkan', 'Mulai belajar untuk']),
]

STATUS_OBSERVATIONAL = 'OBSERVATIONAL'

# --- Auto-retrain -------------------------------------------------
AUTO_RETRAIN_THRESHOLD = 50   # new activities since last training to trigger auto-retrain

# --- Storage ------------------------------------------------------
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(_BACKEND_ROOT, 'models')

DEFAULT_FEATURE_VERSION = '1.0'

# How many past versions to keep per (model_type, teacher_id).
#
# Each retrain writes a new row AND a new file, and versions are on one
# global counter, so a class that retrains often grows without limit. The
# oldest beyond this window is deleted: a model nobody reads any more is
# not history worth keeping on disk, and the current one is always
# retained because pruning runs after the new row is committed.
KEEP_VERSIONS_PER_SCOPE = 5

STATUS_INSUFFICIENT = 'INSUFFICIENT_DATA'
STATUS_MODEL_UNAVAILABLE = 'MODEL_UNAVAILABLE'
STATUS_READY = 'READY'
STATUS_FALLBACK = 'FALLBACK'