# ============================================================
# TAHAP 5 - Decision Tree for mastery classification.
#
# - Labels come from the transparent baseline rule (Tahap 4 thresholds),
#   stored in ml_config. These are metadata for building the initial
#   labeled dataset, NOT "ML-detected" labels.
# - A shallow tree (max_depth, min_samples_*) keeps the model
#   explainable and reduces overfit.
# - LABEL LEAKAGE IS PREVENTED: the label is a deterministic function of
#   BASELINE_WEIGHTS, so the features that build the label
#   (cfg.LABEL_DEFINING_FEATURES) are excluded from the model's input.
#   The tree learns from cfg.DT_FEATURES only. See ml_config for the
#   full reasoning - without this the reported accuracy was meaningless.
# - Evaluation uses REPEATED STRATIFIED CROSS-VALIDATION, not a single
#   train/test split, and is reported alongside a majority-class baseline
#   so the number can be judged. We never invent metrics.
# ============================================================
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix)

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
    """Build (ids, X, y) for training.

    X uses cfg.DT_FEATURES - deliberately NOT cfg.FEATURES. The label is
    derived from cfg.LABEL_DEFINING_FEATURES, so including those columns
    would let the model read its own answer.
    """
    ids = [r[cfg.ID_COLUMN] for r in rows]
    X = [[r.get(f, 0.0) for f in cfg.DT_FEATURES] for r in rows]
    y = [baseline_label(r) for r in rows]
    return ids, np.asarray(X, dtype=float), np.asarray(y)


def class_distribution(y):
    """{label: count} across the labelled dataset.

    Keys are forced to plain str: numpy string subclasses serialise
    inconsistently through Flask's jsonify.
    """
    dist = {}
    for v in y:
        dist[str(v)] = dist.get(str(v), 0) + 1
    return dist


def majority_baseline(y):
    """Accuracy of the trivial 'always predict the most common class'.

    This is the number a model must beat to be worth anything. Without
    it, 60% accuracy can look impressive while a coin-flipping script
    gets 55%.
    """
    dist = class_distribution(y)
    if not dist:
        return None
    return round(max(dist.values()) / len(y), 4)


def _cv_folds(y):
    """How many stratified folds this dataset can actually support.

    Stratification needs at least one sample per class in every fold, so
    the fold count is capped by the smallest class. Classes that are too
    thin to be stratified at all make the evaluation unreliable, so they
    disqualify it entirely rather than being quietly dropped.
    """
    classes, counts = np.unique(y, return_counts=True)
    if len(classes) < 2:
        return 0
    big_enough = int((counts >= cfg.MIN_CLASS_FOR_CV).sum())
    if big_enough < 2:
        return 0
    return max(2, min(cfg.CV_FOLDS, int(counts.min())))


def cross_validate(X, y):
    """Repeated stratified cross-validation.

    Returns a metrics dict, or None when the dataset cannot support a
    trustworthy evaluation. The reported figures are averaged over
    CV_REPEATS x folds resamples, and the standard deviation is kept so
    an unstable result cannot be presented as a firm number.
    """
    folds = _cv_folds(y)
    if folds < 2 or len(y) < cfg.MIN_SAMPLES_CV:
        return None

    classes = np.unique(y)
    accs, precs, recs, f1s = [], [], [], []
    cm = np.zeros((len(classes), len(classes)), dtype=int)

    for rep in range(cfg.CV_REPEATS):
        skf = StratifiedKFold(n_splits=folds, shuffle=True,
                              random_state=cfg.CV_RANDOM_STATE + rep)
        for tr, te in skf.split(X, y):
            prep = _new_preprocessor()
            prep.fit(X[tr])
            clf = DecisionTreeClassifier(**cfg.DT_PARAMS)
            clf.fit(prep.transform(X[tr]), y[tr])
            pred = clf.predict(prep.transform(X[te]))
            accs.append(accuracy_score(y[te], pred))
            precs.append(precision_score(y[te], pred, average='macro', zero_division=0))
            recs.append(recall_score(y[te], pred, average='macro', zero_division=0))
            f1s.append(f1_score(y[te], pred, average='macro', zero_division=0))
            cm += confusion_matrix(y[te], pred, labels=classes)

    def _m(v):
        return round(float(np.mean(v)), 4)

    return {
        'accuracy': _m(accs),
        'accuracy_std': round(float(np.std(accs)), 4),
        'precision': _m(precs),
        'recall': _m(recs),
        'f1_score': _m(f1s),
        'method': 'repeated_stratified_cv',
        'folds': folds,
        'repeats': cfg.CV_REPEATS,
        'evaluations': len(accs),
        'test_samples': int(len(y)),
        'confusion_matrix': cm.tolist(),
        'confusion_labels': [str(c) for c in classes],
    }


def _new_preprocessor():
    from src.ml.preprocessing import Preprocessor
    return Preprocessor(feature_order=list(cfg.DT_FEATURES))


def _evaluation_note(cv, n):
    """Plain-language honesty about what the metrics can support."""
    if cv is None:
        return ('Dataset belum cukup untuk evaluasi yang reliable '
                f'(butuh minimal {cfg.MIN_SAMPLES_CV} siswa, dan setiap '
                'kelas mastery minimal 2 anggota agar bisa disusun menjadi fold). '
                'Model tetap dilatih, tetapi '
                'akurasi sengaja tidak ditampilkan agar tidak disalahartikan.')
    base = cv['majority_baseline']
    lift = cv.get('lift_over_baseline')
    if lift is None:
        return (f'Evaluasi dengan {cv["method"]} '
                f'({cv["folds"]} fold x {cv["repeats"]} ulangan). '
                'Baseline kelas mayoritas tidak dapat dihitung.')
    if lift <= 0:
        return ('PERINGATAN: akurasi model tidak lebih baik daripada '
                'baseline tebakan "selalu pilih kelas yang paling banyak" '
                f'({base}). Dengan kondisi ini model belum menambah '
                'informasi apa pun dan sebaiknya tidak dipakai untuk '
                'keputusan.')
    if cv.get('accuracy_std', 0) > 0.10:
        return ('Evaluasi dengan ' + cv['method'] +
                f' ({cv["folds"]} fold x {cv["repeats"]} ulangan). '
                f'Deviasi standar {cv["accuracy_std"]} cukup besar, '
                'jadi angkanya belum stabil - perlakukan sebagai '
                'indikasi, bukan kesimpulan.')
    return (f'Evaluasi dengan {cv["method"]} '
            f'({cv["folds"]} fold x {cv["repeats"]} ulangan). '
            f'Accuracy {cv["accuracy"]} vs baseline kelas mayoritas '
            f'{base} (lift {lift}).')


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
    dist = class_distribution(y)

    # Honest evaluation. The fold count and the class balance decide
    # whether this dataset supports one at all - we never fall back to a
    # flattering single split just to have a number to show.
    cv = cross_validate(X, y)
    if cv is not None:
        base = majority_baseline(y)
        cv['majority_baseline'] = base
        cv['lift_over_baseline'] = (
            round(cv['accuracy'] - base, 4) if base is not None else None)
        cv['class_distribution'] = dist
        cv['label_defined_by'] = 'Aturan baseline (bukan ML): ' + ', '.join(
            sorted(cfg.LABEL_DEFINING_FEATURES))
        cv['excluded_from_input'] = list(cfg.LABEL_DEFINING_FEATURES)
    evaluation_note = _evaluation_note(cv, len(rows))

    # Final model for deployment: fitted on ALL available rows so no
    # student data is wasted. Evaluation above used resampling so the
    # reported score is never the model's score on its own training data.
    prep = _new_preprocessor()
    prep.fit(X)
    clf = DecisionTreeClassifier(**cfg.DT_PARAMS)
    clf.fit(prep.transform(X), y)

    feature_importance = {f: round(float(v), 4)
                          for f, v in zip(cfg.DT_FEATURES, clf.feature_importances_)}

    stored_metrics = dict(cv) if cv else {'metrics_available': False}
    stored_metrics['evaluation_note'] = evaluation_note
    stored_metrics['majority_baseline'] = majority_baseline(y)
    stored_metrics['model_input_features'] = list(cfg.DT_FEATURES)
    stored_metrics['excluded_to_prevent_leakage'] = list(cfg.LABEL_DEFINING_FEATURES)

    # Average feature value per class (from training data) - used ONLY for
    # explainability of a prediction against real class statistics.
    # Aligned to DT_FEATURES, matching the model's actual input.
    class_mean = {}
    X_scaled_for_stats = prep.transform(X)
    for cls in np.unique(y):
        mask = y == cls
        class_mean[cls] = {f: round(float(np.mean(X_scaled_for_stats[mask][:, i])), 4)
                           for i, f in enumerate(cfg.DT_FEATURES)}

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
        'class_distribution': dist,
        'feature_schema': list(cfg.DT_FEATURES),
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
    # Iterate the model's OWN input order (stored in the artifact), not
    # cfg.FEATURES: the tree never saw the label-defining features, so
    # they cannot be a reason for its prediction.
    for f in (artifact.get('feature_schema')
              or list(importance.keys())
              or list(class_mean[next(iter(class_mean))].keys())):
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