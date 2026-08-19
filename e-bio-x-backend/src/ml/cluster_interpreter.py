# ============================================================
# TAHAP 5 - Cluster interpretation.
#
# K-Means cluster numbers are arbitrary and change across runs, so
# profile names are ALWAYS derived from the centroid's actual data
# (composite mastery + activity level), never from the cluster number.
# ============================================================
from src.ml import ml_config as cfg

LABEL_HIGH_ACHIEVEMENT = 'High Achievement'
LABEL_ACTIVE_LEARNER = 'Active Learner'
LABEL_MODERATE_LEARNER = 'Moderate Learner'
LABEL_NEEDS_SUPPORT = 'Needs Support'
LABEL_LOW_ACTIVITY = 'Low Activity'

ALL_LABELS = [LABEL_HIGH_ACHIEVEMENT, LABEL_ACTIVE_LEARNER, LABEL_MODERATE_LEARNER, LABEL_NEEDS_SUPPORT, LABEL_LOW_ACTIVITY]

DESCRIPTIONS = {
    LABEL_HIGH_ACHIEVEMENT: 'Kelompok dengan penguasaan materi dan hasil kuis tinggi.',
    LABEL_ACTIVE_LEARNER: 'Aktif belajar dengan intensitas tinggi, namun penguasaan masih dapat ditingkatkan.',
    LABEL_MODERATE_LEARNER: 'Kelompok dengan performa belajar pada tingkat menengah.',
    LABEL_NEEDS_SUPPORT: 'Kelompok yang membutuhkan pendampingan dan penguatan materi.',
    LABEL_LOW_ACTIVITY: 'Kelompok dengan aktivitas belajar yang masih rendah.',
}


def _composite(means):
    parts = [means.get(f, 0.0) for f in ('material_completion_rate', 'quiz_average', 'interactive_accuracy')]
    return float(sum(parts) / len(parts)) if parts else 0.0


def interpret_clusters(artifact):
    """Build profile description for every cluster using real centroid data."""
    cluster_means = artifact.get('cluster_means') or []
    global_means = artifact.get('global_means') or {}
    global_activity = global_means.get('learning_minutes') or 0.0

    scored = []
    for cm in cluster_means:
        mean_row = cm.get('means') or {}
        composite = _composite(mean_row)
        activity = mean_row.get('learning_minutes') or 0.0
        scored.append({'cluster_id': cm['cluster_id'], 'member_count': cm['member_count'],
                       'means': mean_row, 'composite': composite,
                       'activity': activity})

    if not scored:
        return []
    scored.sort(key=lambda x: (-x['composite']))

    labels = {}
    descriptions = {}
    characteristics = {}
    n = len(scored)
    for idx, item in enumerate(scored):
        cid = item['cluster_id']
        high = idx == 0 and n > 1 and item['composite'] > 0.5
        low = idx == n - 1 and n > 1 and item['composite'] < 0.5
        mid = not high and not low

        if high:
            label = LABEL_HIGH_ACHIEVEMENT
        elif low:
            label = LABEL_ACTIVE_LEARNER if item['activity'] > global_activity else LABEL_NEEDS_SUPPORT
        elif mid:
            label = LABEL_ACTIVE_LEARNER if item['activity'] > global_activity else LABEL_MODERATE_LEARNER
        else:
            label = LABEL_MODERATE_LEARNER

        labels[cid] = label
        descriptions[cid] = DESCRIPTIONS.get(label, '')
        characteristics[cid] = _characteristics(item['means'], label)

    return [{
        'cluster_id': cid,
        'label': labels[cid],
        'description': descriptions[cid],
        'member_count': next((s['member_count'] for s in scored if s['cluster_id'] == cid), 0),
        'characteristics': characteristics[cid],
        'means': next((s['means'] for s in scored if s['cluster_id'] == cid), {}),
    } for cid in labels]


def _characteristics(means, label):
    comp_pct = round(_composite(means) * 100, 1)
    quiz_pct = round((means.get('quiz_average') or 0.0) * 100, 1)
    acc_pct = round((means.get('interactive_accuracy') or 0.0) * 100, 1)
    learning_minutes = round(means.get('learning_minutes') or 0.0, 1)
    return [
        f'Penguasaan komposit: {comp_pct}%',
        f'Rata-rata kuis: {quiz_pct}%',
        f'Akurasi soal: {acc_pct}%',
        f'Waktu belajar: {learning_minutes} menit',
    ]