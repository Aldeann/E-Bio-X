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