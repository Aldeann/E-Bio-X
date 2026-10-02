# ============================================================
# TAHAP 5 - Recommendation closed-loop evaluation.
#
# WHY THIS EXISTS
# The recommendation layer writes `clicked_at` and `completed_at`
# (see recommendation.mark_clicked / mark_completed), but nothing in the
# pipeline read them back. That means the hand-tuned REC_WEIGHTS were
# taken entirely on faith. This module closes the loop by measuring
# what actually happened after a material was recommended.
#
# HONESTY RULES (these are deliberate, do not remove):
#   1. Every number here is OBSERVATIONAL, never causal. A material is
#      recommended BECAUSE the student is struggling, so a good
#      completion rate may reflect an easy material rather than a good
#      recommendation. Reports state this explicitly.
#   2. No fabricated data. Small samples are reported as
#      INSUFFICIENT_DATA instead of a misleading percentage.
#   3. Buckets below EVAL_MIN_SAMPLES are reported as insufficient
#      rather than shown with a rate that would swing wildly.
#
# Main entry point: evaluate_recommendations(teacher=None)
# ============================================================
from src.models.recommendation import Recommendation
from src.models.user import User
from src.ml import ml_config as cfg
from src.services import learning_analytics_service as analytics


# ------------------------------------------------------------
# Scoping
# ------------------------------------------------------------
def _scoped_rows(teacher):
    """Recommendation rows visible to `teacher`.

    teacher=None means system-wide (admin). Otherwise only students the
    teacher actually teaches, so one teacher never sees another's data.
    """
    if teacher is None:
        return Recommendation.query.all()
    student_ids = analytics.teacher_student_ids(teacher.id)
    if not student_ids:
        return []
    return Recommendation.query.filter(
        Recommendation.student_id.in_(student_ids)).all()


def _students(rows):
    return {r.student_id for r in rows}


# ------------------------------------------------------------
# 1. Funnel: recommended -> clicked -> completed
# ------------------------------------------------------------
def _funnel(rows):
    total = len(rows)
    clicked = [r for r in rows if r.clicked_at is not None]
    completed = [r for r in rows if r.completed_at is not None]
    clicked_not_completed = [r for r in clicked if r.completed_at is None]

    if total < cfg.EVAL_MIN_SAMPLES:
        return {
            'status': cfg.STATUS_INSUFFICIENT,
            'recommended': total,
            'min_required': cfg.EVAL_MIN_SAMPLES,
            'message': 'Belum cukup rekomendasi tercatat untuk mengukur efektivitas.',
        }

    return {
        'status': cfg.STATUS_READY,
        'recommended': total,
        'clicked': len(clicked),
        'completed': len(completed),
        'clicked_not_completed': len(clicked_not_completed),
        'click_through_rate': round(len(clicked) / total, 4),
        'completion_rate': round(len(completed) / total, 4),
        'completion_of_clicked': round(
            len(completed) / len(clicked), 4) if clicked else None,
    }


# ------------------------------------------------------------
# 2. Calibration: does a higher score actually yield more clicks?
#
# This is the metric that puts REC_WEIGHTS on trial. If the CTR is
# flat or non-monotonic across score bins, the weights are arbitrary
# and should be re-tuned - not defended.
# ------------------------------------------------------------
def _bin_label(score):
    if score is None:
        return None
    for lo, hi, label in cfg.EVAL_SCORE_BINS:
        if lo <= score < hi:
            return label
    return None


def _calibration(rows):
    buckets = {}
    for lo, hi, label in cfg.EVAL_SCORE_BINS:
        buckets[label] = {'score_min': lo, 'score_max': hi, 'rows': []}

    unbinable = 0
    for r in rows:
        label = _bin_label(r.recommendation_score)
        if label is None:
            unbinable += 1
            continue
        buckets[label]['rows'].append(r)

    out = []
    usable = []
    for label, b in buckets.items():
        rs = b['rows']
        entry = {
            'bin': label,
            'score_range': f"{b['score_min']:.2f}-{_bin_upper(label):.2f}",
            'recommended': len(rs),
        }
        if len(rs) < cfg.EVAL_MIN_SAMPLES:
            entry['status'] = cfg.STATUS_INSUFFICIENT
            entry['min_required'] = cfg.EVAL_MIN_SAMPLES
        else:
            clicked = sum(1 for r in rs if r.clicked_at is not None)
            completed = sum(1 for r in rs if r.completed_at is not None)
            entry['status'] = cfg.STATUS_READY
            entry['clicked'] = clicked
            entry['completed'] = completed
            entry['click_through_rate'] = round(clicked / len(rs), 4)
            entry['completion_rate'] = round(completed / len(rs), 4)
            usable.append(entry)
        out.append(entry)

    verdict = None
    if len(usable) >= 2:
        ctrs = [e['click_through_rate'] for e in usable]
        spread = max(ctrs) - min(ctrs)
        if spread < 0.05:
            # Every bin clicks at the same rate -> the score does not
            # discriminate at all. Reporting this as "monotonic" would
            # wrongly read as support for the weights.
            verdict = 'TIDAK_BERBEDA'
        elif all(a <= b for a, b in zip(ctrs, ctrs[1:])):
            verdict = 'TERDUKUNG'
        elif all(a >= b for a, b in zip(ctrs, ctrs[1:])):
            verdict = 'TERBALIK'
        else:
            verdict = 'TIDAK_BERATURAN'

    return {
        'status': cfg.STATUS_READY if usable else cfg.STATUS_INSUFFICIENT,
        'bins': out,
        'unbinable': unbinable,
        'verdict': verdict,
        'interpretation': _calibration_note(verdict),
    }


def _bin_upper(label):
    for lo, hi, lbl in cfg.EVAL_SCORE_BINS:
        if lbl == label:
            return min(hi, 1.0)
    return 1.0


def _calibration_note(verdict):
    if verdict == 'TERDUKUNG':
        return ('Click rate meningkat seiring naiknya skor rekomendasi. '
                'Bobot REC_WEIGHTS konsisten dengan perilaku siswa.')
    if verdict == 'TERBALIK':
        return ('Click rate justru MENURUN saat skor naik. Ada bobot yang '
                'terlalu dominan dan perlu ditinjau ulang.')
    if verdict == 'TIDAK_BERATURAN':
        return ('Click rate tidak naik monotonik terhadap skor. Bobot '
                'REC_WEIGHTS belum terbukti sesuai dengan perilaku siswa.')
    if verdict == 'TIDAK_BERBEDA':
        return ('Click rate hampir sama di semua tingkat skor. Artinya skor '
                'rekomendasi saat ini tidak membedakan mana yang lebih '
                'menarik diklik siswa.')
    return ('Belum cukup bin dengan sampel memadai untuk menilai apakah '
            'skor berkorelasi dengan klik.')


# ------------------------------------------------------------
# 3. Reason effectiveness: which argument actually works?
# ------------------------------------------------------------
def _reason_group(reason):
    text = (reason or '').lower()
    for group, needles in cfg.EVAL_REASON_GROUPS:
        for needle in needles:
            if needle.lower() in text:
                return group
    return 'lainnya'


def _reason_effectiveness(rows):
    groups = {}
    for r in rows:
        seen = set()
        for reason in (r.reason_json or []):
            g = _reason_group(reason)
            if g in seen:
                continue
            seen.add(g)
            g_entry = groups.setdefault(g, {'shown': 0, 'clicked': 0, 'completed': 0})
            g_entry['shown'] += 1
            if r.clicked_at is not None:
                g_entry['clicked'] += 1
            if r.completed_at is not None:
                g_entry['completed'] += 1

    if not groups:
        return {'status': cfg.STATUS_INSUFFICIENT, 'groups': []}

    out = []
    for g, d in groups.items():
        entry = {'group': g, 'shown': d['shown']}
        if d['shown'] < cfg.EVAL_MIN_SAMPLES:
            entry['status'] = cfg.STATUS_INSUFFICIENT
        else:
            entry['status'] = cfg.STATUS_READY
            entry['clicked'] = d['clicked']
            entry['completed'] = d['completed']
            entry['click_through_rate'] = round(d['clicked'] / d['shown'], 4)
            entry['completion_rate'] = round(d['completed'] / d['shown'], 4)
        out.append(entry)

    out.sort(key=lambda e: (-e['shown'], e['group']))
    return {
        'status': cfg.STATUS_READY if any(
            e['status'] == cfg.STATUS_READY for e in out) else cfg.STATUS_INSUFFICIENT,
        'groups': out,
    }


# ------------------------------------------------------------
# 4. Within-student yield: did the recommended material get finished
#    more often than the materials that were NOT recommended?
#
# Within-student avoids the worst confound (some students simply study
# more). It is still observational.
# ------------------------------------------------------------
def _completion_yield(rows):
    by_student = {}
    for r in rows:
        by_student.setdefault(r.student_id, set()).add(r.material_id)

    per_student = []
    for student_id, rec_ids in by_student.items():
        student = User.query.get(student_id)
        if student is None:
            continue

        all_materials = analytics.student_accessible_materials(student)
        rec_progress = [analytics.progress_percentage(m.id, student_id)
                        for m in all_materials if m.id in rec_ids]
        other_progress = [analytics.progress_percentage(m.id, student_id)
                          for m in all_materials if m.id not in rec_ids]
        if not rec_progress or not other_progress:
            continue

        rec_mean = sum(rec_progress) / len(rec_progress)
        other_mean = sum(other_progress) / len(other_progress)
        per_student.append({
            'student_id': student_id,
            'recommended_count': len(rec_progress),
            'other_count': len(other_progress),
            'recommended_progress': round(rec_mean, 1),
            'other_progress': round(other_mean, 1),
            'delta': round(rec_mean - other_mean, 1),
        })

    if len(per_student) < cfg.EVAL_MIN_STUDENTS:
        return {
            'status': cfg.STATUS_INSUFFICIENT,
            'students_evaluated': len(per_student),
            'min_required': cfg.EVAL_MIN_STUDENTS,
            'message': ('Butuh minimal %d siswa dengan materi rekomendasi dan '
                        'non-rekomendasi untuk membandingkan progres.' %
                        cfg.EVAL_MIN_STUDENTS),
        }

    deltas = [p['delta'] for p in per_student]
    better = sum(1 for d in deltas if d > 0)
    return {
        'status': cfg.STATUS_READY,
        'students_evaluated': len(per_student),
        'mean_recommended_progress': round(
            sum(p['recommended_progress'] for p in per_student) / len(per_student), 1),
        'mean_other_progress': round(
            sum(p['other_progress'] for p in per_student) / len(per_student), 1),
        'mean_delta': round(sum(deltas) / len(deltas), 1),
        'students_with_higher_recommended': better,
        'per_student': per_student[:20],
    }


# ------------------------------------------------------------
# 5. Per-material effectiveness (for teacher follow-up)
# ------------------------------------------------------------
def _per_material(rows, limit=10):
    by_material = {}
    for r in rows:
        m = by_material.setdefault(r.material_id, {
            'material_id': r.material_id,
            'title': r.material.title if r.material else None,
            'topic': r.material.topic if r.material else None,
            'recommended': 0, 'clicked': 0, 'completed': 0,
        })
        m['recommended'] += 1
        if r.clicked_at is not None:
            m['clicked'] += 1
        if r.completed_at is not None:
            m['completed'] += 1

    out = []
    for m in by_material.values():
        if m['recommended'] < cfg.EVAL_MIN_SAMPLES:
            m['status'] = cfg.STATUS_INSUFFICIENT
            m.pop('recommended', None)
            m.pop('clicked', None)
            m.pop('completed', None)
        else:
            m['status'] = cfg.STATUS_READY
            m['click_through_rate'] = round(m['clicked'] / m['recommended'], 4)
            m['completion_rate'] = round(m['completed'] / m['recommended'], 4)
        out.append(m)

    out.sort(key=lambda x: (-(x.get('recommended') or 0), x['material_id']))
    return out[:limit]


# ------------------------------------------------------------
# Public entry point
# ------------------------------------------------------------
OBSERVATION_NOTE = (
    'Semua angka bersifat OBSERVASIONAL, bukan kausal. Materi '
    'direkomendasikan justru karena siswa kesulitan pada materi itu, '
    'sehingga tingkat penyelesaian tinggi belum tentu berarti '
    'rekomendasi berhasil.'
)


def evaluate_recommendations(teacher=None):
    """Evaluate how the recommendation layer actually performed."""
    rows = _scoped_rows(teacher)
    rows = [r for r in rows if r is not None]

    if not rows:
        return {
            'status': cfg.STATUS_INSUFFICIENT,
            'scope': 'system' if teacher is None else 'teacher',
            'students_with_recommendations': 0,
            'funnel': {'status': cfg.STATUS_INSUFFICIENT, 'recommended': 0},
            'calibration': {'status': cfg.STATUS_INSUFFICIENT, 'bins': []},
            'reasons': {'status': cfg.STATUS_INSUFFICIENT, 'groups': []},
            'completion_yield': {'status': cfg.STATUS_INSUFFICIENT},
            'per_material': [],
            'note': OBSERVATION_NOTE,
            'message': ('Belum ada data rekomendasi yang tercatat. '
                        'Rekomendasi dihitung saat siswa membuka dashboard.'),
        }

    return {
        'status': cfg.STATUS_READY,
        'scope': 'system' if teacher is None else 'teacher',
        'students_with_recommendations': len(_students(rows)),
        'funnel': _funnel(rows),
        'calibration': _calibration(rows),
        'reasons': _reason_effectiveness(rows),
        'completion_yield': _completion_yield(rows),
        'per_material': _per_material(rows),
        'note': OBSERVATION_NOTE,
    }
