# ============================================================
# TAHAP 5 - Tests that the training label is NOT leaked into the
# model's input, and that reported accuracy is honest.
#
# The label is produced by baseline_label(), a deterministic function of
# cfg.BASELINE_WEIGHTS. Feeding those same features to the tree let it
# read the answer off the question, which is why the pipeline once
# reported a perfect 100% accuracy. These tests pin the fix so a future
# edit cannot quietly reintroduce the leak.
# ============================================================
import random

from src.ml import ml_config as cfg
from src.ml import decision_tree as dt

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}", extra or "")


def make_rows(n, seed=1):
    """Rows where the label has real, but imperfect, correlation with
    features - the realistic case."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        a = rng.random()
        q = min(1.0, max(0.0, a + rng.gauss(0, 0.18)))
        m = min(1.0, max(0.0, a + rng.gauss(0, 0.22)))
        ia = min(1.0, max(0.0, a + rng.gauss(0, 0.20)))
        rows.append({
            'student_id': i,
            'material_completion_rate': round(m, 4),
            'section_completion_rate': round(m * 0.9, 4),
            'interactive_accuracy': round(ia, 4),
            'quiz_average': round(q, 4),
            'quiz_best_score': round(min(1.0, q + 0.12), 4),
            'easy_accuracy': round(min(1.0, ia + 0.10), 4),
            'medium_accuracy': round(ia, 4),
            'hard_accuracy': round(max(0.0, ia - 0.18), 4),
            'learning_minutes': round(10 + a * 120 + rng.gauss(0, 12), 2),
            'quiz_attempts': rng.randint(1, 12),
            'correct_rate': round((q + ia) / 2, 4),
            'forum_posts_count': rng.randint(0, 6),
            'forum_replies_count': rng.randint(0, 14),
            'forum_questions_asked': rng.randint(0, 4),
            'forum_answers_given': rng.randint(0, 5),
            'forum_reactions_received': rng.randint(0, 10),
            'ai_explanations_viewed': rng.randint(0, 6),
            'ai_explanations_helpful': rng.randint(0, 5),
        })
    return rows


print("===== LEBOCORAN LABEL: KONFIGURASI =====")
leak = [f for f in cfg.LABEL_DEFINING_FEATURES if f in cfg.DT_FEATURES]
check('tidak ada feature pembentuk label di DT_FEATURES',
      not leak, f' bocor: {leak}' if leak else '')
check('DT_FEATURES adalah bagian dari FEATURES',
      set(cfg.DT_FEATURES).issubset(set(cfg.FEATURES)))
check('DT_FEATURES tidak kosong', len(cfg.DT_FEATURES) > 0,
      f'n={len(cfg.DT_FEATURES)}')
check('FEATURES tetap utuh (dipakai display & dataset)',
      len(cfg.FEATURES) == 18, f'n={len(cfg.FEATURES)}')

# The critical guard: the label must not be reconstructible from the
# model's inputs alone.
check('label TIDAK bisa dihitung dari input model',
      not any(f in cfg.DT_FEATURES for f in cfg.BASELINE_WEIGHTS))
check('ketiga bobot baseline tetap ada di FEATURES (dokumentasi)',
      all(f in cfg.FEATURES for f in cfg.BASELINE_WEIGHTS))

print("\n===== LEBOCORAN LABEL: DATASET LATIH =====")
rows = make_rows(80)
ids, X, y = dt.build_labeled_dataset(rows)
check('X memiliki kolom = len(DT_FEATURES)',
      X.shape[1] == len(cfg.DT_FEATURES), f'X.shape={X.shape}')
check('X tidak memuat feature pembentuk label',
      X.shape[1] == len(cfg.DT_FEATURES))
check('y berisi label valid',
      set(y) <= {k for k, _ in cfg.MASTERY_TRUTH_ORDER},
      f'{sorted(set(y))}')

# Direct proof: given ONLY the model's input columns, the label cannot be
# derived. Rebuilding the label needs the excluded features.
feat_map = {f: i for i, f in enumerate(cfg.DT_FEATURES)}
first = rows[0]
from_dt_only = sum(first.get(f, 0.0) * w for f, w in cfg.BASELINE_WEIGHTS.items()
                   if f in feat_map)
full_label_score = dt.baseline_mastery_score(first) * 100
check('rekonstruksi label dari input model tidak identik dengan label asli',
      abs(from_dt_only - full_label_score) > 1e-9,
      f'dari-DT={from_dt_only:.4f} penuh={full_label_score:.4f}')

print("\n===== EVALUASI: BUKAN ANGKA PALSU =====")
p = dt.fit_from_rows(rows)
m = p['metrics']
check('model terlatih', p['status'] == cfg.STATUS_READY)
check('accuracy dilaporkan', m.get('accuracy') is not None, str(m.get('accuracy')))
check('accuracy BUKAN 1.0 sempurna (indikasi kebocoran)',
      m['accuracy'] < 1.0, f'accuracy={m["accuracy"]}')
check('metode = repeated stratified CV',
      m.get('method') == 'repeated_stratified_cv', str(m.get('method')))
check('CV menghitung lebih dari satu resample',
      (m.get('evaluations') or 0) > 1, str(m.get('evaluations')))
check('deviasi standar ikut dilaporkan', m.get('accuracy_std') is not None)

print("\n===== BASELINE KELAS MAYORITAS =====")
base = dt.majority_baseline(y)
check('baseline dihitung', base is not None, str(base))
expected = max(dt.class_distribution(y).values()) / len(y)
check('baseline = kelas terbanyak / total', abs(base - expected) < 1e-9,
      f'{base} vs {expected:.6f}')
check('baseline ikut disimpan di metrics',
      m.get('majority_baseline') == base)
check('lift dihitung terhadap baseline', m.get('lift_over_baseline') is not None,
      str(m.get('lift_over_baseline')))
check('akurasi harus mengalahkan baseline',
      m['accuracy'] > base, f'{m["accuracy"]} vs {base}')
check('lift konsisten dengan selisih accuracy',
      abs(m['lift_over_baseline'] - (m['accuracy'] - base)) < 1e-9)

print("\n===== CATATAN EVALUASI JUJUR =====")
note = p['evaluation_note'] or ''
check('catatan evaluasi ada', bool(note))
check('catatan menyebut angka baseline', str(base) in note, note[:120])
check('catatan menyebut metode', 'cross' in note.lower() or 'cv' in note.lower())

# A dataset where nothing can be learned must be reported as such, not
# dressed up with a flattering number.
rng2 = random.Random(99)
noise = []
for i in range(80):
    noise.append({f: rng2.random() for f in cfg.FEATURES})
noise[0]['student_id'] = 0
noise_rows = [{**{f: 0.0 for f in cfg.FEATURES}, **r} for r in noise]
for i, r in enumerate(noise_rows):
    r['student_id'] = i
pn = dt.fit_from_rows(noise_rows)
mn = pn['metrics']
check('data acak tetap dilatih (tidak crash)', pn['status'] == cfg.STATUS_READY)
check('data acak punya baseline dilaporkan', mn.get('majority_baseline') is not None)
check('data acak: accuracy tidak diklaim sempurna',
      mn.get('accuracy') is None or mn['accuracy'] < 1.0, str(mn.get('accuracy')))

print("\n===== DATA KECIL: METRIK DISEMBUNYIKAN =====")
tiny = make_rows(12, seed=3)
pt = dt.fit_from_rows(tiny)
check('dataset kecil ditolak (< MIN_SAMPLES_DT)',
      pt['status'] == cfg.STATUS_INSUFFICIENT, pt['status'])
check('pesan insufficient benar-benar menjelaskan',
      'cukup' in (pt.get('message') or '').lower())

small = make_rows(16, seed=4)
ps = dt.fit_from_rows(small)
ms = ps['metrics']
check('dataset 16_rows dilatih', ps['status'] == cfg.STATUS_READY)
if len(small) < cfg.MIN_SAMPLES_CV:
    check('metrik TIDAK ditampilkan (< MIN_SAMPLES_CV)',
          ms.get('metrics_available') is False, str(ms.get('accuracy')))
    check('catatan menjelaskan kenapa metrik kosong',
          bool(ps['evaluation_note']))
    check('baseline tetap dilaporkan walau metrik kosong',
          ms.get('majority_baseline') is not None)
else:
    check('CV jalan pada 16_rows', ms.get('accuracy') is not None)

print("\n===== SKEMA ARTEFAK =====")
check('artefak menyimpan feature_schema',
      p.get('feature_schema') == list(cfg.DT_FEATURES))
check('feature_importance selaras DT_FEATURES',
      set(p['feature_importance']) == set(cfg.DT_FEATURES))
check('class_mean selaras DT_FEATURES',
      all(set(v) == set(cfg.DT_FEATURES) for v in p['class_mean'].values()))
check('preprocessor memakai DT_FEATURES',
      p['preprocessor'].feature_order == list(cfg.DT_FEATURES))
check('metrics mencatat feature yang dikecualikan',
      m.get('excluded_to_prevent_leakage') == list(cfg.LABEL_DEFINING_FEATURES))

print("\n===== PREDIKSI KONSISTEN DENGAN SKEMA =====")
label, clf = dt.predict_row(rows[3], p)
check('prediksi berhasil', label in {k for k, _ in cfg.MASTERY_TRUTH_ORDER},
      str(label))
check('jumlah feature importance = jumlah kolom input',
      len(clf.feature_importances_) == len(cfg.DT_FEATURES))

print("\n===== EXPLAIN HANYA BILANGKAN FITUR MODEL =====")
factors = dt.explain(rows[3], p, label)
check('explain menghasilkan faktor', isinstance(factors, list))
check('explain tidak pernah menyebut feature pembentuk label',
      not any(f['feature'] in cfg.LABEL_DEFINING_FEATURES for f in factors),
      str([f['feature'] for f in factors]))

print("\n===== CLASS DISTRIBUTION =====")
dist = dt.class_distribution(y)
check('total distribusi = jumlah baris', sum(dist.values()) == len(y))
check('key distribusi adalah str biasa (aman untuk json)',
      all(type(k) is str for k in dist), str([type(k).__name__ for k in dist]))

print("\n===== SUMMARY =====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"TOTAL: {len(results)}  PASS: {passed}  FAIL: {len(results) - passed}")
for name, ok, extra in results:
    if not ok:
        print(f"  FAIL> {name} {extra}")
import sys
sys.exit(1 if passed != len(results) else 0)