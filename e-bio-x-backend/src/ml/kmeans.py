# ============================================================
# TAHAP 5 - K-Means on learning profiles.
#
# Purpose is grouping (NOT judging right/wrong). K is chosen with a
# supporting technique (Silhouette) over a sensible range K=2..5.
# If there are too few students, clustering is skipped entirely.
# ============================================================
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from src.ml import ml_config as cfg


def fit_from_rows(rows):
    if rows is None or len(rows) < cfg.MIN_SAMPLES_KMEANS:
        return {'status': cfg.STATUS_INSUFFICIENT,
                'message': 'Jumlah siswa terlalu sedikit untuk clustering.',
                'samples': len(rows) if rows else 0,
                'min_required': cfg.MIN_SAMPLES_KMEANS}

    from src.ml.preprocessing import Preprocessor, normalize_subset
    X = np.asarray([normalize_subset(r, cfg.KMEANS_FEATURES) for r in rows], dtype=float)
    n = len(rows)

    prep = Preprocessor()
    prep.fit(X)
    Xs = prep.transform(X)

    best_k = None
    best_score = -1.0
    silhouettes = {}
    for k in cfg.K_RANGE:
        if k >= n:
            continue
        km = KMeans(n_clusters=k, random_state=cfg.KMEANS_RANDOM_STATE, n_init=10)
        labels = km.fit_predict(Xs)
        try:
            score = float(silhouette_score(Xs, labels))
        except Exception:
            score = None
        silhouettes[k] = round(score, 4) if score is not None else None
        if score is not None and score > best_score:
            best_score = score
            best_k = k

    if best_k is None or best_score < 0:
        # Not decisive -> documented default.
        best_k = min(cfg.DEFAULT_KMEANS_K, n - 1) if n > 1 else 1

    kmeans = KMeans(n_clusters=best_k, random_state=cfg.KMEANS_RANDOM_STATE, n_init=10)
    labels = kmeans.fit_predict(Xs)

    cluster_means = []
    raw_means = {}
    for c in range(best_k):
        mask = labels == c
        if np.count_nonzero(mask) == 0:
            continue
        mean_row = {}
        for i, f in enumerate(cfg.KMEANS_FEATURES):
            mean_row[f] = round(float(np.mean(X[mask][:, i])), 4)
        cluster_means.append({'cluster_id': int(c), 'member_count': int(np.count_nonzero(mask)),
                              'means': mean_row})
        raw_means[int(c)] = mean_row

    global_means = {f: round(float(np.mean(X[:, i])), 4) for i, f in enumerate(cfg.KMEANS_FEATURES)}

    return {
        'model': kmeans,
        'preprocessor': prep,
        'feature_subset': list(cfg.KMEANS_FEATURES),
        'k': best_k,
        'silhouette': silhouettes.get(best_k),
        'silhouettes': silhouettes,
        'cluster_means': cluster_means,
        'global_means': global_means,
        'assignment': {str(rows[i][cfg.ID_COLUMN]): int(labels[i]) for i in range(n)},
        'sample_count': n,
        'status': cfg.STATUS_READY,
    }


def assign_cluster(row, artifact):
    if artifact is None or artifact.get('model') is None:
        return None
    from src.ml.preprocessing import normalize_subset
    subset = artifact.get('feature_subset') or cfg.KMEANS_FEATURES
    prep = artifact['preprocessor']
    x = prep.transform(np.asarray([normalize_subset(row, subset)], dtype=float))
    return int(artifact['model'].predict(x)[0])