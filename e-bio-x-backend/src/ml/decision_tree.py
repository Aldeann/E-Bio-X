# ============================================================
# TAHAP 5 - Decision Tree for mastery classification.
#
# - Labels come from the transparent baseline rule (Tahap 4 thresholds),
#   stored in ml_config. These are metadata for building the initial
#   labeled dataset, NOT "ML-detected" labels.
# - A shallow tree (max_depth, min_samples_*) keeps the model
#   explainable and reduces overfit.
# - Evaluation is only reported when a held-out test set exists; we
#   never invent metrics.
# ============================================================
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from src.ml import ml_config as cfg


def baseline_mastery_score(row):
    """Composite 0..1 mastery score used ONLY for baseline labelling."""
    w = cfg.BASELINE_WEIGHTS
    quiz = row.get('quiz_average') or 0.0
    comp = row.get('material_completion_rate') or 0.0
    acc = row.get('interactive_accuracy') or 0.0
    return quiz * w['quiz_average'] + comp * w['material_completion_rate'] + acc * w['interactive_accuracy']


def baseline_label(row):
    score = baseline_mastery_score(row) * 100.0
    for key, min_score in cfg.MASTERY_TRUTH_ORDER:
        if score >= min_score:
            return key
    return cfg.MASTERY_TRUTH_ORDER[-1][0]


def build_labeled_dataset(rows):
    ids = [r[cfg.ID_COLUMN] for r in rows]
    X = [[r.get(f, 0.0) for f in cfg.FEATURES] for r in rows]
    y = [baseline_label(r) for r in rows]
    return ids, np.asarray(X, dtype=float), np.asarray(y)


def _metrics(clf, X_test, y_test):
    pred = clf.predict(X_test)
    return {
        'accuracy': round(float(accuracy_score(y_test, pred)), 4),
        'precision': round(float(precision_score(y_test, pred, average='macro', zero_division=0)), 4),
        'recall': round(float(recall_score(y_test, pred, average='macro', zero_division=0)), 4),
        'f1_score': round(float(f1_score(y_test, pred, average='macro', zero_division=0)), 4),
        'test_samples': int(len(y_test)),
    }


def fit_from_rows(rows):
    """Train a Decision Tree from prepared feature rows.

    Returns a save-ready payload, or {'status': INSUFFICIENT} when the
    dataset is too small to train.
    """
    if rows is None or len(rows) < cfg.MIN_SAMPLES_DT:
        return {'status': cfg.STATUS_INSUFFICIENT,
                'message': 'Dataset belum cukup untuk training Decision Tree.',
                'samples': len(rows) if rows else 0,
                'min_required': cfg.MIN_SAMPLES_DT}

    ids, X, y = build_labeled_dataset(rows)
    metrics = None
    evaluation_note = None

    from src.ml.preprocessing import Preprocessor
    prep = Preprocessor()

    if len(rows) >= cfg.MIN_SAMPLES_SPLIT:
        stratify = y if len(set(y)) >= 2 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=cfg.SPLIT_TEST_SIZE, stratify=stratify, random_state=42)
        prep.fit(X_train)
        clf = DecisionTreeClassifier(**cfg.DT_PARAMS)
        clf.fit(prep.transform(X_train), y_train)
        metrics = _metrics(clf, prep.transform(X_test), y_test)
        # Re-fit on ALL data for the deployed model so no training data is wasted.
        prep = Preprocessor()
        prep.fit(X)
        clf = DecisionTreeClassifier(**cfg.DT_PARAMS)
        clf.fit(prep.transform(X), y)
    else:
        evaluation_note = 'Dataset belum cukup untuk evaluasi model yang reliable.'
        prep.fit(X)
        clf = DecisionTreeClassifier(**cfg.DT_PARAMS)
        clf.fit(prep.transform(X), y)

    feature_importance = {f: round(float(v), 4) for f, v in zip(cfg.FEATURES, clf.feature_importances_)}

    stored_metrics = dict(metrics) if metrics else None
    if stored_metrics is None:
        stored_metrics = {'metrics_available': False}
    if evaluation_note:
        stored_metrics['evaluation_note'] = evaluation_note

    # Average feature value per class (from training data) - used ONLY for
    # explainability of a prediction against real class statistics.
    class_mean = {}
    X_scaled_for_stats = prep.transform(X)
    for cls in np.unique(y):
        mask = y == cls
        class_mean[cls] = {f: round(float(np.mean(X_scaled_for_stats[mask][:, i])), 4)
                           for i, f in enumerate(cfg.FEATURES)}

    return {
        'model': clf,
        'preprocessor': prep,
        'metrics': stored_metrics,
        'evaluation_note': evaluation_note,
        'feature_importance': feature_importance,
        'class_mean': class_mean,
        'baseline_weights': dict(cfg.BASELINE_WEIGHTS),
        'label_thresholds': list(cfg.MASTERY_TRUTH_ORDER),
        'sample_count': len(rows),
        'status': cfg.STATUS_READY,
    }


def predict_row(row, artifact):
    """Classify one feature row using a trained artifact."""
    if artifact is None or artifact.get('model') is None:
        return None, None
    prep = artifact['preprocessor']
    X = np.asarray([_vector(row, prep.feature_order)], dtype=float)
    Xs = prep.transform(X)
    clf = artifact['model']
    label = clf.predict(Xs)[0]
    return label, clf


def _vector(row, feature_order):
    return [float(row.get(f, 0.0) if row.get(f) is not None else 0.0) for f in feature_order]


def explain(row, artifact, label):
    """Data-backed factors that influenced the prediction.

    Uses feature importance (from the model) combined with the REAL
    per-class statistics stored at training time. Nothing here is guessed.
    """
    if artifact is None or not artifact.get('class_mean'):
        return []
    importance = artifact.get('feature_importance') or {}
    class_mean = artifact.get('class_mean') or {}
    high_class = 'VERY_GOOD'
    low_classes = ('FAIR', 'NEEDS_REINFORCEMENT')
    factors = []
    threshold = 0.05
    for f in cfg.FEATURES:
        w = importance.get(f, 0.0)
        if w < threshold:
            continue
        student_val = float(row.get(f) if row.get(f) is not None else 0.0)
        refs = {}
        for cls in class_mean:
            refs[cls] = class_mean[cls].get(f, 0.0)
        baseline = refs.get(label, 0.0)
        others = [v for k, v in refs.items() if k != label]
        cohort_diff = float(np.mean(others)) if others else 0.0
        if label in low_classes and student_val < cohort_diff:
            factors.append({
                'feature': f,
                'importance': round(w, 3),
                'value': round(student_val, 3),
                'cohort_average': round(cohort_diff, 3),
                'direction': 'below',
                'reason': f'{f} di bawah rata-rata',
            })
        elif label == high_class and student_val >= baseline:
            factors.append({
                'feature': f,
                'importance': round(w, 3),
                'value': round(student_val, 3),
                'cohort_average': round(baseline, 3),
                'direction': 'above',
                'reason': f'{f} di atas rata-rata',
            })
    factors.sort(key=lambda x: (-x['importance']))
    return factors[:5]