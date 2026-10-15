# ============================================================
# TAHAP 5 - Learned ranker (pointwise / Learning-to-Rank).
#
# Tujuan: mengganti bobot TANGAN pada score_material dengan bobot
# yang DIPELAJARI dari data, lalu mengukur jujur: apakah model
# mengalahkan baseline. Ini komponen ML yang nyata, bukan label.
#
# DESAIN ANTI-BOCOR (leakage):
#   Label = "siswa menyelesaikan materi ini" (peristiwa perilaku nyata,
#   diukur dari material_student_state.completed). Label ini TIDAK
#   dihitung dari rumus penguasaan, jadi ia outcome yang independen.
#
#   Fitur SINTA = hal yang sudah diketahui SEBELUM hasil itu terjadi:
#     - kemampuan siswa (kuis, akurasi interaktif, effort) - agregat
#       lintas materi, bukan penguasaan siswa pada materi ini;
#     - sifat materi (kesulitan, estimasi waktu, jumlah bagian, fase);
#     - tingkat penyelesaian materi itu di antara siswa lain (kohort).
#   Yang SENGAJA TIDAK dipakai: mastery/error siswa PADA materi itu
#   sendiri. Nilai itu sudah tercermin dari status "selesai" sehingga
#   membuat model sekadar membaca jawaban (accuracy ~1.0 palsu).
#   Prinsip yang sama dipakai decision_tree (LABEL_DEFINING_FEATURES).
#
# Evaluasi: NDCG@k + Precision@k dengan cross-validation PER SISWA
# (siswa tidak pernah muncul di train dan test sekaligus), dibandingkan
# dengan baseline acak, baseline popularitas, dan rule produksi sebagai
# REFERENSI. Tidak ada metrik yang dikarang.
# ============================================================

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, roc_auc_score,
                             precision_score, recall_score)

from src.models.user import User
from src.models.material_student_state import MaterialStudentState
from src.ml import ml_config as cfg
from src.ml import feature_service, model_manager
from src.services import learning_analytics_service as analytics
from src.ml import recommendation as rec_service


# ------------------------------------------------------------
# Item-level features (available before exposure).
# ------------------------------------------------------------
def _difficulty_num(value):
    d = analytics.normalize_difficulty(value)
    return {'easy': 0.0, 'medium': 1.0, 'hard': 2.0}.get(d, 1.0)


def _phase_num(value):
    import re
    if not value:
        return 0.0
    m = re.search(r'(\d+)', str(value))
    return float(m.group(1)) if m else 0.0


def _time_minutes(value):
    import re
    if not value:
        return 30.0
    s = str(value).lower()
    m = re.search(r'(\d+(?:[.,]\d+)?)', s)
    if not m:
        return 30.0
    num = float(m.group(1).replace(',', '.'))
    if 'jam' in s or 'hour' in s:
        num *= 60.0
    elif 'menit' not in s and 'minute' not in s and num <= 4:
        # Bare small number is almost always a count of hours in this data.
        num *= 60.0
    return num


def _cohort_stats():
    """material_id -> popularity/completion prior over all students.

    Cheap aggregate from MaterialStudentState. It answers "of the students
    who touched this material, how many finished it" - a popularity/outcome
    prior a real recommender legitimately uses. With ~100 students the
    target student's own contribution is ~1%, so it does not leak the label.
    """
    states = MaterialStudentState.query.all()
    agg = {}
    for st in states:
        b = agg.setdefault(st.material_id, {'n': 0, 'done': 0})
        b['n'] += 1
        if st.completed:
            b['done'] += 1
    return {
        mid: {
            'item_completion_rate': (b['done'] / b['n']) if b['n'] else 0.0,
            'item_students': float(b['n']),
        }
        for mid, b in agg.items()
    }


def _vectorize_row(student_row, material, cohort):
    r = student_row or {}
    cs = cohort.get(material.id, {})
    vec = {
        # student ability (independent, student-level)
        'quiz_average': float(r.get('quiz_average') or 0.0),
        'interactive_accuracy': float(r.get('interactive_accuracy') or 0.0),
        'correct_rate': float(r.get('correct_rate') or 0.0),
        'learning_minutes': float(r.get('learning_minutes') or 0.0),
        # item attributes (same for every student)
        'item_difficulty': _difficulty_num(material.difficulty),
        'item_time_minutes': _time_minutes(material.estimated_time),
        'item_phase': _phase_num(material.phase),
        'item_sections': float(len(material.sections or [])),
        # cohort signal
        'item_completion_rate': float(cs.get('item_completion_rate', 0.0)),
    }
    for f in cfg.RANKER_FEATURES:
        if f not in vec:
            vec[f] = 0.0
    return vec


def build_ranking_dataset(students=None, teacher_id=None):
    if students is None:
        if teacher_id is not None:
            students = analytics.teacher_student_users(teacher_id)
        else:
            students = User.query.filter_by(role='student').all()

    cohort = _cohort_stats()
    rows = []
    for s in students:
        try:
            srow = feature_service.aggregate_student_features(s) or {}
        except Exception:
            srow = {}
        try:
            mats = analytics.student_accessible_materials(s)
        except Exception:
            mats = []
        for m in mats:
            try:
                state = MaterialStudentState.query.filter_by(
                    student_id=s.id, material_id=m.id).first()
            except Exception:
                state = None
            completed = bool(state and state.completed)
            vec = _vectorize_row(srow, m, cohort)
            row = {
                'student_id': s.id,
                'material_id': m.id,
                'title': m.title,
                'label': 1 if completed else 0,
            }
            row.update(vec)
            rows.append(row)
    return rows


# ------------------------------------------------------------
# Ranking metrics
# ------------------------------------------------------------
def _dcg_at_k(y_true, y_score, k):
    if k <= 0:
        return 0.0
    order = np.argsort(-np.asarray(y_score))
    y_true_ord = np.take(np.asarray(y_true), order)[:k]
    gains = 2 ** y_true_ord - 1
    discounts = np.log2(np.arange(2, len(y_true_ord) + 2))
    return float(np.sum(gains / discounts))


def _ndcg_at_k(y_true, y_score, k):
    ideal = _dcg_at_k(y_true, y_true, k)
    if ideal == 0:
        return 0.0
    return float(_dcg_at_k(y_true, y_score, k) / ideal)


def _precision_at_k(y_true, y_score, k):
    if k <= 0:
        return 0.0
    order = np.argsort(-np.asarray(y_score))
    topk = np.take(np.asarray(y_true), order)[:k]
    return float(np.mean(topk)) if len(topk) else 0.0


def _group_by_student(rows):
    by = {}
    for r in rows:
        by.setdefault(r['student_id'], []).append(r)
    return list(by.values())


def _make_model():
    if cfg.RANKER_MODEL_TYPE == 'gbm':
        return HistGradientBoostingClassifier(random_state=42, max_depth=3)
    return LogisticRegression(max_iter=1000, class_weight='balanced', solver='lbfgs')


def _feature_coeffs(model):
    try:
        if hasattr(model, 'coef_'):
            return [{'feature': f, 'coef': round(float(c), 4)}
                    for f, c in zip(cfg.RANKER_FEATURES, model.coef_[0])]
    except Exception:
        pass
    return []


def _matrix(groups):
    X, y = [], []
    for g in groups:
        for row in g:
            X.append([float(row.get(f, 0.0)) for f in cfg.RANKER_FEATURES])
            y.append(int(row.get('label', 0)))
    return np.array(X, dtype=float), np.array(y, dtype=int)


def _mean_ndcg_by_group(groups, scores_by_student, k):
    """Average NDCG@k across students (per-student ranking)."""
    vals = []
    for g in groups:
        if not g:
            continue
        y = np.array([int(r.get('label', 0)) for r in g])
        s = np.array([scores_by_student.get(id(r), 0.0) for r in g])
        vals.append(_ndcg_at_k(y, s, k))
    return float(np.mean(vals)) if vals else 0.0


def _cv_evaluate(groups, k, cv_folds):
    """Cross-validation by student: metrics on the held-out students only."""
    rng = np.random.RandomState(42)
    if len(groups) >= 3:
        kf = KFold(n_splits=min(cv_folds, len(groups)), shuffle=True,
                   random_state=42)
        folds = list(kf.split(groups))
    else:
        folds = [(list(range(len(groups))), list(range(len(groups))))]

    model_ndcg, model_prec = [], []
    rand_ndcg, pop_ndcg, rule_ndcg = [], [], []
    pooled_y, pooled_model, pooled_rand, pooled_pop = [], [], [], []
    n_test = 0
    for train_idx, test_idx in folds:
        train_groups = [groups[i] for i in train_idx]
        test_groups = [groups[i] for i in test_idx]
        if not train_groups or not test_groups:
            continue
        Xtr, ytr = _matrix(train_groups)
        if len(np.unique(ytr)) < 2:
            continue
        model = _make_model()
        scaler = StandardScaler()
        Xtr_s = scaler.fit_transform(Xtr)
        model.fit(Xtr_s, ytr)

        model_scores, rand_scores, pop_scores, rule_scores = {}, {}, {}, {}
        for g in test_groups:
            for row in g:
                x = np.array([[float(row.get(f, 0.0)) for f in cfg.RANKER_FEATURES]],
                             dtype=float)
                try:
                    p = float(model.predict_proba(scaler.transform(x))[0, 1])
                except Exception:
                    p = 0.0
                model_scores[id(row)] = p
                rand_scores[id(row)] = float(rng.rand())
                pop_scores[id(row)] = float(row.get('item_completion_rate', 0.0))
                # Production rule as REFERENCE, reconstructed from the same
                # material state (finished) the rule would read.
                rule_scores[id(row)] = 1.0 - float(row.get('label', 0))

        n_test += sum(len(g) for g in test_groups)
        model_ndcg.append(_mean_ndcg_by_group(test_groups, model_scores, k))
        rand_ndcg.append(_mean_ndcg_by_group(test_groups, rand_scores, k))
        pop_ndcg.append(_mean_ndcg_by_group(test_groups, pop_scores, k))
        rule_ndcg.append(_mean_ndcg_by_group(test_groups, rule_scores, k))

        # Pooled held-out predictions (student never in its own training
        # fold) - used for a stable ranking-quality number: ROC-AUC.
        for g in test_groups:
            for row in g:
                pooled_y.append(int(row.get('label', 0)))
                pooled_model.append(model_scores[id(row)])
                pooled_rand.append(rand_scores[id(row)])
                pooled_pop.append(pop_scores[id(row)])

        # precision across every held-out row (pooled), k globally
        all_rows = [r for g in test_groups for r in g]
        model_prec.append(_precision_at_k(
            [int(r['label']) for r in all_rows],
            [model_scores[id(r)] for r in all_rows], k))

    if not model_ndcg:
        return None
    out = {
        'cv_folds': len(folds),
        'n_test_samples': int(n_test),
        'ndcg_model_mean': round(float(np.mean(model_ndcg)), 4),
        'ndcg_random_mean': round(float(np.mean(rand_ndcg)), 4),
        'ndcg_popularity_mean': round(float(np.mean(pop_ndcg)), 4),
        'ndcg_rule_reference_mean': round(float(np.mean(rule_ndcg)), 4),
        'precision_model_mean': round(float(np.mean(model_prec)), 4),
        'delta_vs_random': round(float(np.mean(model_ndcg) - np.mean(rand_ndcg)), 4),
        'delta_vs_popularity': round(float(np.mean(model_ndcg) - np.mean(pop_ndcg)), 4),
    }
    if len(set(pooled_y)) >= 2:
        out['roc_auc_model'] = round(float(roc_auc_score(pooled_y, pooled_model)), 4)
        out['roc_auc_popularity'] = round(float(roc_auc_score(pooled_y, pooled_pop)), 4)
        out['best_baseline_ndcg'] = round(
            max(out['ndcg_random_mean'], out['ndcg_popularity_mean']), 4)
        out['ndcg_gain_vs_best_baseline'] = round(
            out['ndcg_model_mean'] - max(out['ndcg_random_mean'],
                                         out['ndcg_popularity_mean']), 4)
        out['deployable'] = bool(
            out['ndcg_model_mean']
            >= max(out['ndcg_random_mean'], out['ndcg_popularity_mean'])
            + cfg.RANKER_MIN_NDCG_GAIN)
    else:
        out['deployable'] = False
    return out


# ------------------------------------------------------------
# Training
# ------------------------------------------------------------
def train_ranker(teacher_id=None, students=None):
    rows = build_ranking_dataset(students=students, teacher_id=teacher_id)
    total = len(rows)
    pos = sum(1 for r in rows if r['label'] == 1)
    neg = total - pos
    n_stu = len(set(r['student_id'] for r in rows))

    if (total < cfg.RANKER_MIN_SAMPLES or n_stu < cfg.RANKER_MIN_STUDENTS
            or pos < cfg.RANKER_MIN_POS or neg < cfg.RANKER_MIN_NEG):
        return {
            'status': cfg.STATUS_INSUFFICIENT,
            'message': ('Data belum cukup untuk melatih ranker. '
                        'Butuh lebih banyak pasangan (siswa x materi) berlabel.'),
            'samples': total, 'students': n_stu, 'pos': pos, 'neg': neg,
            'min_samples': cfg.RANKER_MIN_SAMPLES,
            'min_students': cfg.RANKER_MIN_STUDENTS,
            'min_pos': cfg.RANKER_MIN_POS, 'min_neg': cfg.RANKER_MIN_NEG,
        }

    X, y = _matrix([rows])
    model = _make_model()
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model.fit(Xs, y)

    if hasattr(model, 'predict_proba'):
        y_prob = model.predict_proba(Xs)[:, 1]
    else:
        y_prob = model.decision_function(Xs)
    y_prob = np.asarray(y_prob)

    groups = _group_by_student(rows)
    cv = _cv_evaluate(groups, cfg.RANKER_K, cfg.RANKER_CV_FOLDS)

    train_metrics = {
        'accuracy': round(float(accuracy_score(y, model.predict(Xs))), 4),
        'roc_auc': round(float(roc_auc_score(y, y_prob)), 4),
        'precision': round(float(precision_score(y, model.predict(Xs), zero_division=0)), 4),
        'recall': round(float(recall_score(y, model.predict(Xs), zero_division=0)), 4),
    }

    note = _evaluation_note(cv)
    deployable = bool(cv and cv.get('deployable'))
    metrics = {
        'label': 'completed',
        'label_note': ('Label = siswa benar-benar MENYELESAIKAN materi '
                       '(perilaku terukur), bukan skor karangan.'),
        'features': list(cfg.RANKER_FEATURES),
        'excluded_features_note': (
            'Penguasaan/error per-materi siswa TIDAK dipakai sebagai fitur '
            'karena nilainya sudah tercermin dari status selesai (kebocoran '
            'label). Model memakai kemampuan siswa + sifat materi + '
            'popularitas materi.'),
        'train': train_metrics,
        'cross_validation': cv,
        'evaluation_note': note,
        'deployable': deployable,
        'min_ndcg_gain': cfg.RANKER_MIN_NDCG_GAIN,
        'limitations': [
            'Jumlah materi pada data demo masih sedikit (3-6 materi per siswa), '
            'sehingga sinyal untuk MENGURUTKAN materi di dalam satu siswa lemah. '
            'Ini keterbatasan data, bukan bug model.',
            'Fitur kemampuan siswa (mis. waktu belajar, rata-rata kuis) dihitung '
            'dari SELURUH aktivitas siswa, termasuk aktivitas pada materi yang '
            'sedang diberi label. Karena itu ROC-AUC gabungan (antar-siswa) bisa '
            'terlalu optimistis. NDCG@k TIDAK terpengaruh hal ini karena '
            'kemampuan siswa bernilai sama untuk semua materi satu siswa.',
        ],
    }

    payload = {
        'status': cfg.STATUS_READY,
        'model': model,
        'scaler': scaler,
        'feature_order': list(cfg.RANKER_FEATURES),
        'metrics': metrics,
        'evaluation_note': note,
        'deployable': deployable,
        'sample_count': total,
        'student_count': n_stu,
        'pos': pos,
        'neg': neg,
        'feature_coefficients': _feature_coeffs(model),
    }
    return payload


def _evaluation_note(cv):
    if not cv:
        return ('Metrik cross-validation tidak tersedia (data kelas terlalu '
                'timpang). Angka training tidak boleh dibaca sebagai performa.')
    d_rand = cv.get('delta_vs_random', 0.0)
    d_pop = cv.get('delta_vs_popularity', 0.0)
    auc = cv.get('roc_auc_model')
    auc_txt = f' (ROC-AUC held-out {auc})' if auc is not None else ''
    if cv.get('deployable'):
        base = ('Model ML TERBUKTI mengungguli baseline (acak & popularitas) '
                f'pada NDCG@{cfg.RANKER_K} dengan margin >= '
                f'{cfg.RANKER_MIN_NDCG_GAIN}{auc_txt}, sehingga LAYAK dipakai '
                'untuk mengurutkan rekomendasi.')
    else:
        base = ('Model ML BELUM mengungguli baseline secara meyakinkan pada '
                f'NDCG@{cfg.RANKER_K} (delta acak {d_rand}, delta popularitas '
                f'{d_pop}){auc_txt}. Karena itu rekomendasi TETAP memakai rule '
                'transparan; model tidak dipakai untuk mengurutkan.')
    return base


# ------------------------------------------------------------
# Persistence + inference
# ------------------------------------------------------------
def save_ranker(artifact, teacher_id=None):
    payload = {
        'model': artifact['model'],
        'scaler': artifact['scaler'],
        'feature_order': artifact['feature_order'],
        'meta': {
            'status': artifact['status'],
            'metrics': artifact.get('metrics'),
            'evaluation_note': artifact.get('evaluation_note'),
            'sample_count': artifact.get('sample_count'),
            'student_count': artifact.get('student_count'),
            'pos': artifact.get('pos'),
            'neg': artifact.get('neg'),
            'feature_coefficients': artifact.get('feature_coefficients'),
            'deployable': artifact.get('deployable', False),
        },
    }
    return model_manager.save_artifact('ranker', payload, teacher_id=teacher_id)


def load_ranker(teacher_id=None, require_deployable=True):
    """Return a ranker artifact, or None.

    With `require_deployable` (the default for inference) the artifact is
    only returned when its offline evaluation passed the deployment gate -
    so the recommender can never silently switch to a model that has not
    proven itself against the baselines. Pass False to inspect the model
    (e.g. the evaluation endpoint).
    """
    candidates = []
    if teacher_id is not None:
        try:
            candidates.append(model_manager.load_artifact(
                'ranker', teacher_id=teacher_id, allow_pooled_fallback=False))
        except Exception:
            pass
    try:
        candidates.append(model_manager.load_artifact('ranker', teacher_id=None))
    except Exception:
        pass
    for art in candidates:
        if not artifact_ready(art):
            continue
        if require_deployable and not (art.get('meta') or {}).get('deployable'):
            continue
        return art
    return None


def predict_score(student_row, material, artifact, cohort=None):
    """Probability (0..1) that the student completes this material."""
    if not artifact:
        return None
    cohort = cohort if cohort is not None else _cohort_stats()
    vec = _vectorize_row(student_row, material, cohort)
    order = artifact.get('feature_order') or list(cfg.RANKER_FEATURES)
    x = np.array([[float(vec.get(f, 0.0)) for f in order]], dtype=float)
    scaler = artifact.get('scaler')
    try:
        Xs = scaler.transform(x) if scaler is not None else x
    except Exception:
        return None
    model = artifact.get('model')
    try:
        if hasattr(model, 'predict_proba'):
            p = float(model.predict_proba(Xs)[0, 1])
        else:
            z = float(model.decision_function(Xs)[0])
            p = 1.0 / (1.0 + np.exp(-z)) if np.isfinite(z) else 0.5
    except Exception:
        p = 0.0
    return round(max(0.0, min(1.0, p)), 4)


def predict_scores(student_row, materials, artifact):
    """{material_id: probability} for a list of Material objects."""
    out = {}
    if not artifact:
        return out
    try:
        cohort = _cohort_stats()
    except Exception:
        cohort = {}
    for mat in materials:
        try:
            out[mat.id] = predict_score(student_row, mat, artifact, cohort)
        except Exception:
            continue
    return out


def explain_ml(student_row, material, artifact, cohort=None):
    """Human-readable reason from the model's strongest features.

    Linear-model coefficients applied to this material's feature values, so
    the sentence is a real statement about THIS input, not a generic line.
    """
    coeffs = (artifact or {}).get('meta', {}).get('feature_coefficients') or []
    if not coeffs:
        return ['Direkomendasikan oleh model pembelajaran']
    cohort = cohort if cohort is not None else _cohort_stats()
    vec = _vectorize_row(student_row, material, cohort)
    contribs = []
    for c in coeffs:
        f = c.get('feature')
        if f in vec:
            contribs.append((f, float(c.get('coef', 0.0)) * float(vec[f])))
    contribs.sort(key=lambda t: -abs(t[1]))
    reasons = []
    for f, contrib in contribs[:cfg.RANKER_TOP_CONTRIB]:
        if abs(contrib) < 1e-9:
            continue
        reasons.append(f'{_feat_label(f)} '
                       f'{"mendukung" if contrib > 0 else "menurunkan"} '
                       f'prioritas (kontribusi {contrib:+.2f})')
    return reasons or ['Direkomendasikan oleh model pembelajaran']


_FEAT_LABEL = {
    'quiz_average': 'Rata-rata kuis',
    'interactive_accuracy': 'Akurasi interaktif',
    'correct_rate': 'Tingkat jawaban benar',
    'learning_minutes': 'Waktu belajar',
    'item_difficulty': 'Tingkat kesulitan materi',
    'item_time_minutes': 'Estimasi waktu materi',
    'item_phase': 'Fase materi',
    'item_sections': 'Jumlah bagian materi',
    'item_completion_rate': 'Tingkat penyelesaian materi oleh siswa lain',
}


def _feat_label(f):
    return _FEAT_LABEL.get(f, f)


def artifact_ready(artifact):
    return bool(artifact) and bool(artifact.get('model'))
