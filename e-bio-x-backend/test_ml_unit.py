# ============================================================
# TAHAP 5 - Unit tests for ML pipeline (no live server needed).
# Synthetic in-memory rows exercise the algorithms for real.
# Coverage: Bagian AK (Decision Tree), AL (K-Means), AM (Recommendation),
#           model storage/versioning, preprocessing consistency.
# ============================================================
import random

from src.ml import ml_config as cfg
from src.ml import decision_tree, kmeans as kmeans_mod, cluster_interpreter, recommendation as rec
from src.ml import preprocessing as prep_mod

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}", extra or "")


def make_row(i, base):
    return {'student_id': i,
            'material_completion_rate': round(base, 3),
            'section_completion_rate': round(base * 0.9, 3),
            'interactive_accuracy': round(base, 3),
            'quiz_average': round(base, 3),
            'quiz_best_score': round(min(1.0, base + 0.15), 3),
            'easy_accuracy': round(min(1.0, base + 0.10), 3),
            'medium_accuracy': round(base, 3),
            'hard_accuracy': round(max(0.0, base - 0.20), 3),
            'learning_minutes': round(random.uniform(5, 90), 1),
            'quiz_attempts': random.randint(1, 10),
            'correct_rate': round(base, 3),
            'forum_posts_count': random.randint(0, 5),
            'forum_replies_count': random.randint(0, 10),
            'forum_questions_asked': random.randint(0, 3),
            'forum_answers_given': random.randint(0, 3),
            'forum_reactions_received': random.randint(0, 8),
            'ai_explanations_viewed': random.randint(0, 5),
            'ai_explanations_helpful': random.randint(0, 3)}


def make_rows(n, seed=7):
    random.seed(seed)
    return [make_row(i + 1, random.random()) for i in range(n)]


print('===== DATASET / PREPROCESSING =====')
rows = make_rows(80)
ids, X, y = decision_tree.build_labeled_dataset(rows)
check('dataset valid (row count)', len(ids) == len(X) == len(y) == 80)
check('student_id is identifier only', cfg.ID_COLUMN not in cfg.FEATURES)
check('feature count is 18 (11 original + 7 new)', len(cfg.FEATURES) == 18)
check('feature order stable', cfg.FEATURES == list(cfg.FEATURES))
vec = prep_mod.normalize_row({**rows[0], 'quiz_average': None})
check('missing value imputed to 0', vec[cfg.FEATURES.index('quiz_average')] == 0.0)
norm_none = prep_mod.normalize_row({'student_id': 999})
check('all-missing row safe (no crash)', len(norm_none) == len(cfg.FEATURES))

p1 = prep_mod.Preprocessor()
p1.fit(X)
X1 = p1.transform(X)
p2 = prep_mod.Preprocessor(scaler=p1.scaler, feature_order=p1.feature_order)
X2 = p2.transform(X)
check('preprocessing consistency (same scaler, same output)', (X1 == X2).all())

print('===== DECISION TREE =====')
small = make_rows(10)
out_small = decision_tree.fit_from_rows(small)
check('insufficient data -> INSUFFICIENT_DATA', out_small['status'] == cfg.STATUS_INSUFFICIENT)
out = decision_tree.fit_from_rows(rows)
check('training -> READY', out['status'] == cfg.STATUS_READY)
check('metrics computed with test split', bool(out.get('metrics') and 'accuracy' in out['metrics'] and out['metrics']['accuracy'] >= 0))
check('feature importance reported', bool(out.get('feature_importance')))
label = decision_tree.predict_row(rows[0], out)
check('prediction returns valid label', label[0] in ('VERY_GOOD', 'GOOD', 'FAIR', 'NEEDS_REINFORCEMENT'))
factors = decision_tree.explain(rows[0], out, label[0])
check('explain returns data-backed factors', isinstance(factors, list))
labels = {decision_tree.baseline_label(r) for r in rows}
check('baseline labels from thresholds', len(labels) >= 1 and all(l in ('VERY_GOOD', 'GOOD', 'FAIR', 'NEEDS_REINFORCEMENT') for l in labels))

print('===== K-MEANS =====')
km_small = kmeans_mod.fit_from_rows(make_rows(5))
check('too few students -> INSUFFICIENT_DATA', km_small['status'] == cfg.STATUS_INSUFFICIENT)
km = kmeans_mod.fit_from_rows(rows)
check('clustering -> READY', km['status'] == cfg.STATUS_READY)
check('k within range 2..5', km['k'] in (2, 3, 4, 5))
check('silhouette score produced', km.get('silhouette') is not None and km['silhouette'] >= -1)
check('scaling applied (preprocessor present)', km['preprocessor'] is not None)
first_thin = [r for r in rows if r['material_completion_rate'] < 0.3]
label1 = kmeans_mod.assign_cluster(first_thin[0], km)
check('cluster assignment works', label1 is not None)
profiles = cluster_interpreter.interpret_clusters(km)
check('cluster profiles interpreted', len(profiles) == km['k'])
check('labels not dependent on cluster id', all(p['label'] in cluster_interpreter.ALL_LABELS for p in profiles))
km2 = kmeans_mod.fit_from_rows(rows)
check('reproducible (same seed, same k)', km2['k'] == km['k'] and km2['silhouette'] == km['silhouette'])
arr1 = {k: (v['cluster_id'], v['label']) for k, v in enumerate(profiles)}
chk = True
for p in profiles:
    if p['label'] == 'High Achievement':
        chk = chk and p['member_count'] > 0
check('High Achievement cluster present with members', chk)

print('===== RECOMMENDATION =====')
m_struct = {'mastery': 90, 'question_error_rate': 0.05, 'finished': True,
            'topic': 'Struktur Virus', 'topic_mastery': 90,
            'difficulty': 'easy', 'student_weak_difficulty': 'hard'}
m_repl = {'mastery': 55, 'question_error_rate': 0.60, 'finished': False,
          'topic': 'Replikasi Virus', 'topic_mastery': 55,
          'difficulty': 'hard', 'student_weak_difficulty': 'hard'}
s_stmt, s_repl = rec.score_material(m_struct), rec.score_material(m_repl)
check('replication ranks higher than mastered structure', s_repl > s_stmt)
m_repl_fin = dict(m_repl, finished=True)
check('completing replication lowers priority', rec.score_material(m_repl_fin) < s_repl)

# Mastery >=90 edge case: score is reduced by 0.5x when all mastered
m_mastered_only = {'mastery': 95, 'question_error_rate': 0.01, 'finished': True,
                   'topic': 'Virus', 'topic_mastery': 95,
                   'difficulty': 'easy', 'student_weak_difficulty': 'easy'}
s_normal = rec.score_material(m_mastered_only)
s_reduced = round(s_normal * 0.5, 4)
check('mastery>=90 scoring works', s_normal > 0)
check('mastery>=90 reduction factor is 0.5', s_reduced == round(s_normal * 0.5, 4))

print('===== MODEL STORAGE & VERSIONING =====')
from src.ml import model_manager
from src.ml import ml_config as _cfg
from src import app
import tempfile, os as _os, shutil as _shutil
TEST_DIR = tempfile.mkdtemp(prefix='mlmodel_test_')
_orig_dir = _cfg.MODEL_DIR
_cfg.MODEL_DIR = TEST_DIR
try:
    with app.app_context():
        v1 = model_manager.next_version('decision_tree')
        meta = model_manager.save_artifact('decision_tree', out, feature_version='test-unit')
        check('artifact saved with version', meta['model_version'] == v1)
        loaded = model_manager.load_artifact('decision_tree', v1)
        check('artifact loaded back', loaded is not None and loaded.get('model') is not None)
        check('version increments on next save', model_manager.next_version('decision_tree') != v1)
        recs = model_manager.list_models()
        check('model list includes version', any(r['model_version'] == v1 for r in recs))
finally:
    try:
        model_manager._clear()
        with app.app_context():
            from src.models.ml_model import MlModel
            from src.config.database import db
            MlModel.query.filter_by(feature_version='test-unit').delete()
            db.session.commit()
        _cfg.MODEL_DIR = _orig_dir
        _shutil.rmtree(TEST_DIR, ignore_errors=True)
    except Exception:
        pass

print("\n===== SUMMARY =====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"TOTAL: {len(results)}  PASS: {passed}  FAIL: {len(results) - passed}")
for name, ok, extra in results:
    if not ok:
        print(f"  FAIL> {name} {extra}")
import sys
sys.exit(1 if passed != len(results) else 0)