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
MIN_SAMPLES_DT = 20             # below this: cannot train Decision Tree -> INSUFFICIENT_DATA
MIN_SAMPLES_SPLIT = 40          # below this: no train/test split (evaluation not reliable)
SPLIT_TEST_SIZE = 0.25
MIN_SAMPLES_KMEANS = 15         # below this: cannot cluster -> INSUFFICIENT_DATA
K_RANGE = [2, 3, 4, 5]
DEFAULT_KMEANS_K = 3            # documented default when silhouette is not decisive
KMEANS_RANDOM_STATE = 42

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

# --- Storage ------------------------------------------------------
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.path.join(_BACKEND_ROOT, 'models')

DEFAULT_FEATURE_VERSION = '1.0'

STATUS_INSUFFICIENT = 'INSUFFICIENT_DATA'
STATUS_MODEL_UNAVAILABLE = 'MODEL_UNAVAILABLE'
STATUS_READY = 'READY'
STATUS_FALLBACK = 'FALLBACK'