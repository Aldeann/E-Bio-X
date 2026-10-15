"""Dampak rekomendasi & alur belajar (Fase 4).

Menjawab satu pertanyaan: apakah saran sistem benar-benar dikerjakan siswa?

Semua angka diambil dari bukti yang SUDAH tercatat - tidak ada yang dikarang:

- tayang & klik rekomendasi dari ``learning_activities``: event
  ``recommendation_shown`` (dicatat saat saran disajikan, didedup per hari)
  dan ``recommendation_clicked``. Jejak aktivitas bersifat kumulatif, jadi
  CTR tidak bergantung pada tabel ``recommendations`` yang isinya berganti
  setiap kali saran dihitung ulang.
- funnel baca -> latihan -> kuis: ``material_student_state`` (dibuka &
  selesai), ``practice_answers`` (latihan), ``submissions`` + ``quizzes``
  (kuis).
- "latihan membaik": soal yang sama dijawab lebih dari sekali - benar di
  percobaan terakhir padahal salah di percobaan pertama.

Impresi hanya terhitung sejak event ``recommendation_shown`` mulai dicatat,
sehingga CTR selalu "dari saran yang benar-benar ditayangkan", bukan tebakan.
"""
from datetime import datetime, timedelta

from src.models.learning_activity import LearningActivity
from src.models.material_student_state import MaterialStudentState
from src.models.practice_answer import PracticeAnswer
from src.models.quiz import Quiz
from src.models.submission import Submission
from src.services import learning_analytics_service as analytics


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _bounds(filters):
    """(start, end) dari filter tanggal. `end` eksklusif (akhir hari + 1)."""
    start = _parse_date(filters.get('date_from'))
    end = _parse_date(filters.get('date_to'))
    if end:
        end = end + timedelta(days=1)
    return start, end


def _in_range(ts, start, end):
    if ts is None:
        return False
    if start and ts < start:
        return False
    if end and ts >= end:
        return False
    return True


def _pct(part, whole):
    return round(part / whole * 100, 1) if whole else None


def log_recommendation_impressions(student_id, material_ids):
    """Catat tayangan saran materi, maksimal sekali per (siswa, materi) per hari.

    Dipanggil saat endpoint rekomendasi menyajikan daftar ke siswa. Dedup
    harian menjaga tabel aktivitas tidak meledak saat dashboard dibuka
    berulang, tetapi tetap cukup untuk menghitung CTR per rentang tanggal.
    Mengembalikan jumlah event baru yang dicatat.
    """
    material_ids = sorted({int(m) for m in (material_ids or [])})
    if not material_ids:
        return 0
    now = datetime.utcnow()
    day_start = datetime(now.year, now.month, now.day)
    already = {r[0] for r in analytics.db.session.query(
        LearningActivity.material_id).filter(
        LearningActivity.student_id == student_id,
        LearningActivity.event_type == 'recommendation_shown',
        LearningActivity.created_at >= day_start).all()}
    logged = 0
    for mid in material_ids:
        if mid in already:
            continue
        analytics.log_activity(student_id, mid, 'recommendation_shown', silent=True)
        logged += 1
    return logged


def _empty(filters):
    return {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'filters': filters,
        'scope': {'materials': 0, 'students': 0,
                  'date_from': filters.get('date_from'),
                  'date_to': filters.get('date_to')},
        'funnel': {'opened': 0, 'read': 0, 'practiced': 0, 'quizzed': 0,
                   'read_rate': None, 'practice_rate': None, 'quiz_rate': None},
        'recommendation': {'impressions': 0, 'students_shown': 0, 'clicked': 0,
                           'ctr': None, 'students_clicked': 0, 'clicks_total': 0,
                           'clicks_without_impression': 0,
                           'followed_practice': 0, 'followed_quiz': 0,
                           'practice_after_click_rate': None,
                           'quiz_after_click_rate': None},
        'practice_lift': {'retried_questions': 0, 'improved': 0, 'regressed': 0,
                          'improve_rate': None, 'first_attempt_accuracy': None,
                          'last_attempt_accuracy': None},
        'by_material': [],
    }


def teacher_impact(teacher_id, filters=None):
    """Dampak rekomendasi & funnel belajar untuk materi milik satu guru.

    `filters` mengikuti _filters_from_args milik controller (course_id, phase,
    topic, material_id, date_from, date_to). Semua dihormati: cakupan materi
    lewat teacher_materials, cakupan waktu lewat rentang tanggal.
    """
    filters = filters or {}
    materials = analytics.teacher_materials(filters, teacher_id=teacher_id)
    material_ids = [m.id for m in materials]
    student_ids = analytics.teacher_student_ids(teacher_id)
    start, end = _bounds(filters)

    if not material_ids or not student_ids:
        return _empty(filters)

    # --- funnel (siswa unik) ---
    states = MaterialStudentState.query.filter(
        MaterialStudentState.material_id.in_(material_ids),
        MaterialStudentState.student_id.in_(student_ids)).all()

    opened, read_done = set(), set()
    for s in states:
        if _in_range(s.first_accessed_at, start, end):
            opened.add(s.student_id)
        if s.completed and _in_range(s.completed_at, start, end):
            read_done.add(s.student_id)

    practice_rows = PracticeAnswer.query.filter(
        PracticeAnswer.material_id.in_(material_ids),
        PracticeAnswer.student_id.in_(student_ids)).all()
    practiced = {r.student_id for r in practice_rows
                 if _in_range(r.answered_at, start, end)}

    quiz_ids = [q.id for q in Quiz.query.filter(
        Quiz.material_id.in_(material_ids)).all()]
    submissions = []
    quizzed = set()
    if quiz_ids:
        submissions = Submission.query.filter(
            Submission.quiz_id.in_(quiz_ids),
            Submission.student_id.in_(student_ids)).all()
        quizzed = {s.student_id for s in submissions
                   if _in_range(s.submitted_at, start, end)}

    # Basis konversi: siswa yang membuka materi. Bila belum ada yang membuka
    # tetapi ada aksi lain, pakai gabungan agar persentase tidak 0/0 palsu.
    base = len(opened) or len(read_done | practiced | quizzed)

    funnel = {
        'opened': len(opened),
        'read': len(read_done),
        'practiced': len(practiced),
        'quizzed': len(quizzed),
        'read_rate': _pct(len(read_done), base),
        'practice_rate': _pct(len(practiced), base),
        'quiz_rate': _pct(len(quizzed), base),
    }

    # --- rekomendasi: tayang & klik dari jejak aktivitas (kumulatif) ---
    rec_acts = LearningActivity.query.filter(
        LearningActivity.student_id.in_(student_ids),
        LearningActivity.material_id.in_(material_ids),
        LearningActivity.event_type.in_(
            ('recommendation_shown', 'recommendation_clicked'))).all()
    shown_acts = [a for a in rec_acts
                  if a.event_type == 'recommendation_shown'
                  and _in_range(a.created_at, start, end)]
    click_acts = [a for a in rec_acts
                  if a.event_type == 'recommendation_clicked'
                  and _in_range(a.created_at, start, end)]

    # Pasangkan klik dengan impresi: sebuah klik hanya dihitung bila ada
    # tayangan untuk (siswa, materi) yang sama SEBELUM atau pada saat klik.
    # Tanpa ini, klik lama (sebelum impresi mulai dicatat) membuat CTR > 100%.
    shown_pairs = {}
    for a in shown_acts:
        key = (a.student_id, a.material_id)
        if key not in shown_pairs or a.created_at < shown_pairs[key]:
            shown_pairs[key] = a.created_at
    matched_pairs = set()
    unmatched_clicks = 0
    for a in click_acts:
        key = (a.student_id, a.material_id)
        st = shown_pairs.get(key)
        if st is not None and a.created_at >= st:
            matched_pairs.add(key)
        else:
            unmatched_clicks += 1

    impressions = len(shown_pairs)
    clicked = len(matched_pairs)
    students_shown = {k[0] for k in shown_pairs}
    # Tindak lanjut dihitung dari SEMUA klik tercatat (termasuk yang tanpa
    # impresi), supaya dampaknya tidak hilang hanya karena impresi belum dicatat.
    students_clicked = {a.student_id for a in click_acts}

    # Tindak lanjut SETELAH klik: latihan/kuis sesudah klik terakhir yang
    # tercatat untuk siswa itu (bukan sekadar "pernah latihan").
    click_times = {}
    for a in click_acts:
        prev = click_times.get(a.student_id)
        if prev is None or a.created_at < prev:
            click_times[a.student_id] = a.created_at
    followed_practice = set()
    for r in practice_rows:
        ct = click_times.get(r.student_id)
        if ct and r.answered_at and r.answered_at >= ct and _in_range(r.answered_at, start, end):
            followed_practice.add(r.student_id)
    followed_quiz = set()
    for s in submissions:
        ct = click_times.get(s.student_id)
        if ct and s.submitted_at and s.submitted_at >= ct and _in_range(s.submitted_at, start, end):
            followed_quiz.add(s.student_id)

    recommendation = {
        'impressions': impressions,
        'students_shown': len(students_shown),
        'clicked': clicked,
        'ctr': _pct(clicked, impressions),
        'students_clicked': len(students_clicked),
        'clicks_total': len(click_acts),
        'clicks_without_impression': unmatched_clicks,
        'followed_practice': len(followed_practice),
        'followed_quiz': len(followed_quiz),
        'practice_after_click_rate': _pct(len(followed_practice), len(students_clicked)),
        'quiz_after_click_rate': _pct(len(followed_quiz), len(students_clicked)),
    }

    # --- latihan membaik (percobaan ulang soal yang sama) ---
    by_pair = {}
    for r in practice_rows:
        if not _in_range(r.answered_at, start, end):
            continue
        by_pair.setdefault((r.student_id, int(r.bank_question_id)), []).append(r)

    retried = improved = regressed = 0
    first_correct = last_correct = 0
    for rows in by_pair.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda x: (x.attempt_no or 0,
                                 x.answered_at or datetime.min, x.id or 0))
        first = bool(rows[0].is_correct)
        last = bool(rows[-1].is_correct)
        retried += 1
        first_correct += 1 if first else 0
        last_correct += 1 if last else 0
        if not first and last:
            improved += 1
        if first and not last:
            regressed += 1

    practice_lift = {
        'retried_questions': retried,
        'improved': improved,
        'regressed': regressed,
        'improve_rate': _pct(improved, retried),
        'first_attempt_accuracy': _pct(first_correct, retried),
        'last_attempt_accuracy': _pct(last_correct, retried),
    }

    # --- per materi (tayang & klik dihitung dari aktivitas) ---
    per_material = []
    for m in materials:
        mid = m.id
        m_states = [s for s in states if s.material_id == mid]
        m_opened = {s.student_id for s in m_states
                    if _in_range(s.first_accessed_at, start, end)}
        m_read = {s.student_id for s in m_states
                  if s.completed and _in_range(s.completed_at, start, end)}
        m_prac = {r.student_id for r in practice_rows
                  if r.material_id == mid and _in_range(r.answered_at, start, end)}
        m_quiz = {s.student_id for s in submissions
                  if s.quiz and s.quiz.material_id == mid
                  and _in_range(s.submitted_at, start, end)}
        m_shown = {k for k in shown_pairs if k[1] == mid}
        m_clicked = {k for k in matched_pairs if k[1] == mid}
        m_clicks_total = sum(1 for a in click_acts if a.material_id == mid)
        per_material.append({
            'material_id': mid,
            'title': m.title,
            'topic': m.topic,
            'opened': len(m_opened),
            'read': len(m_read),
            'practiced': len(m_prac),
            'quizzed': len(m_quiz),
            'impressions': len(m_shown),
            'clicked': len(m_clicked),
            'clicks_total': m_clicks_total,
            'ctr': _pct(len(m_clicked), len(m_shown)),
        })
    per_material.sort(key=lambda r: (-(r['opened'] or 0), r['title'] or ''))

    return {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'filters': filters,
        'scope': {'materials': len(material_ids), 'students': len(student_ids),
                  'date_from': filters.get('date_from'),
                  'date_to': filters.get('date_to')},
        'funnel': funnel,
        'recommendation': recommendation,
        'practice_lift': practice_lift,
        'by_material': per_material,
    }
