# ============================================================
# TAHAP 5 - Recommendation engine.
#
# Rule-based scoring layer (NOT ML). Weights live in ml_config and are
# deliberately NOT claimed to be learned. Every reason is backed by real
# student data. Handles cold start / new student / fallback.
# ============================================================
from datetime import datetime

from src.config.database import db
from src.models.recommendation import Recommendation
from src.ml import ml_config as cfg
from src.services import learning_analytics_service as analytics
from src.models.material import Material
from src.models.submission import Submission
from src.models.practice_answer import PracticeAnswer
from src.ml import ranker as ranker_mod


# ------------------------------------------------------------
# Pure scoring (unit-testable without a database).
# `m` is a dict:
#  {
#    'mastery': 0..100, 'question_error_rate': 0..1, 'finished': bool,
#    'topic': str|None, 'topic_mastery': 0..100,
#    'difficulty': str|None, 'student_weak_difficulty': str|None,
#  }
# ------------------------------------------------------------
def score_material(m, weights=None):
    w = weights or dict(cfg.REC_WEIGHTS)
    mastery = m.get('mastery', 0) or 0
    mastery_gap = max(0.0, 1.0 - mastery / 100.0)
    question_error = m.get('question_error_rate', 0) or 0.0
    unfinished = 0.0 if (m.get('finished') or False) else 1.0
    topic = m.get('topic')
    topic_mastery = m.get('topic_mastery')
    relevance = 0.5
    if topic and topic_mastery is not None:
        relevance = max(0.0, 1.0 - topic_mastery / 100.0)
    difficulty = analytics.normalize_difficulty(m.get('difficulty'))
    weak = m.get('student_weak_difficulty')
    difficulty_fit = 1.0 if (difficulty and difficulty == weak) else 0.5

    return round(
        mastery_gap * w['mastery_gap']
        + question_error * w['question_error']
        + unfinished * w['unfinished']
        + relevance * w['relevance']
        + difficulty_fit * w['difficulty_fit'],
        4,
    )


def _reasons_for(m, student_row):
    reasons = []
    mastery = m.get('mastery') or 0
    if mastery < 75:
        reasons.append(f'Penguasaan materi masih {mastery:.0f}%')
    if m.get('question_error_rate', 0) and 0 < m['question_error_rate'] <= 1:
        err_pct = round(m['question_error_rate'] * 100)
        reasons.append(f'Masih banyak kesalahan pada soal ({err_pct}% salah)')
    if not (m.get('finished') or False):
        reasons.append('Materi belum selesai')
    if m.get('topic') and m.get('topic_mastery') is not None and m['topic_mastery'] < 75:
        reasons.append(f'Topik {m["topic"]} perlu penguatan')
    if m.get('difficulty') and m.get('student_weak_difficulty'):
        # normalize again here: this is the display layer, so an
        # unrecognised raw value must never reach the student.
        _d = analytics.normalize_difficulty(m['difficulty'])
        if _d:
            reasons.append(f'Fokus pada tingkat {analytics.difficulty_label(_d)}')
    if not reasons:
        reasons.append('Direkomendasikan berdasarkan perkembangan belajar Anda')
    return reasons[:4]


def _student_weak_difficulty(row):
    """Difficulty level the student is weakest at, or None.

    Only levels the student ACTUALLY answered are considered. The test
    must be "were any questions answered at this level", NOT "is the
    accuracy above zero": a student who answered every easy question
    wrongly has easy_accuracy = 0.0, and treating that as "never
    attempted" hid the very level they need the most help with.

    `row` supplies `<level>_attempted` counts (see
    feature_service.aggregate_student_features). When that metadata is
    absent - e.g. an older cached row - we return None rather than guess,
    because guessing would send the weakest student to the wrong level.
    """
    levels = ['easy', 'medium', 'hard']
    counts = {k: row.get(f'{k}_attempted') for k in levels}
    if all(c is None for c in counts.values()):
        return None                      # no attempt metadata -> no claim

    attempted = [k for k in levels
                 if counts.get(k) is not None and counts.get(k) > 0]
    if not attempted:
        return None                      # nothing attempted at any level

    # Lowest accuracy among attempted levels. `levels` is ordered
    # easy -> hard, so min() breaks ties toward the more foundational
    # level, which is the right default when everything is at 0.
    return min(attempted, key=lambda k: row.get(f'{k}_accuracy') or 0.0)


def _material_metrics(student, material, student_row):
    base = analytics.material_row_for(student.id, material)
    mastery = base['mastery_score'] or 0.0

    # Quiz errors on this material's quizzes (submitted attempts).
    #
    # Kanal "soal interaktif" yang dulu ikut dijumlahkan di sini sudah dihapus:
    # tidak pernah dijawab siapa pun, jadi sumbungannya selalu nol dan
    # `question_error_rate` kini murni dari kuis — angkanya identik dengan
    # sebelumnya, hanya tanpa satu query mati per material.
    quiz_ids = [q.id for q in analytics.material_quizzes(material.id)]
    subs = Submission.query.filter(
        Submission.student_id == student.id, Submission.status == 'submitted',
        (Submission.quiz_id.in_(quiz_ids) if quiz_ids else db.true())
    ).all()
    quiz_answered = sum((s.correct_count or 0) + (s.wrong_count or 0) for s in subs)
    quiz_wrong = sum(s.wrong_count or 0 for s in subs)

    answered = quiz_answered
    wrong = quiz_wrong
    error_rate = (wrong / answered) if answered else 0.0

    topic = material.topic
    topic_mastery = None
    if topic:
        topic_masteries = []
        for m in analytics.student_accessible_materials(student):
            if m.topic == topic:
                topic_masteries.append((analytics.material_row_for(student.id, m)['mastery_score'] or 0.0))
        if topic_masteries:
            topic_mastery = sum(topic_masteries) / len(topic_masteries)

    finished = base['status'] == 'selesai'

    return {
        'material_id': material.id,
        'title': material.title,
        'topic': topic,
        'phase': material.phase,
        'estimated_time': material.estimated_time,
        'mastery': round(mastery, 1),
        'question_error_rate': round(error_rate, 4),
        'finished': finished,
        'topic_mastery': round(topic_mastery, 1) if topic_mastery is not None else None,
        'difficulty': analytics.normalize_difficulty(material.difficulty),
        'student_weak_difficulty': _student_weak_difficulty(student_row),
    }


# ------------------------------------------------------------
# Per-SECTION recommendation (Fase 3e). Same rule-based spirit as
# the material level above: transparent weights, no trained model.
# ------------------------------------------------------------
def _prerequisite_factor(s):
    """Faktor prioritas dari status prasyarat (Fase 4e).

    - ``False`` (prasyarat TERBUKTI belum tuntas) -> faktor < 1, supaya
      bagian dasarnya lebih dulu disarankan;
    - ``None`` (belum bisa dinilai), ``True``, atau kunci tidak ada ->
      netral (1.0). Bertindak atas dasar ketidaktahuan akan sama dengan
      mengarang penilaian.
    """
    if s.get('prerequisite_met') is False:
        return cfg.REC_SECTION_UNMET_PREREQ_FACTOR
    return 1.0


def score_section(s, weights=None):
    """Priority score 0..1 for one section (unit-testable, no database).

    `s` is a row from analytics.section_mastery_for_student(). Only
    sections with status == 'READY' are meant to reach this function:
    without a real mastery score there is nothing honest to rank on, and
    inventing one is exactly what the rest of this codebase refuses to do.

    A MISSING score (None) contributes 0 to the mastery term instead of
    being read as 0%. That distinction matters: treating "unknown" as
    "knows nothing" would hand top priority to exactly the sections we
    know least about. The error-rate term is different - it comes from
    answers that really exist, so it stays.

    Fase 4e: bila prasyarat bagian ini TERBUKTI belum tuntas, skornya
    dikalikan faktor penalti supaya dasarnya lebih dulu disarankan. Bila
    prasyaratnya belum bisa dinilai, skor TIDAK diubah.

    Tahap 3: `s` boleh membawa `practice_hours`/`practice_days` (sejak
    latihan terakhir siswa pada bagian itu). Koefisien pengulangan:
    - baru saja dilAtih (< REC_COOLDOWN_HOURS) -> dikali REC_COOLDOWN_FACTOR
      ("ulangi besok", jangan didorong dua kali);
    - lama tak disentuh (>= REC_STALE_DAYS) -> dikali REC_STALE_BOOST;
    - tanpa data -> netral 1.0.
    """
    w = weights or dict(cfg.REC_SECTION_WEIGHTS)
    score = s.get('score')
    mastery_gap = 0.0 if score is None else max(0.0, 1.0 - score / 100.0)
    answered = s.get('answered') or 0
    wrong = max(0, answered - (s.get('correct') or 0))
    error = (wrong / answered) if answered else 0.0
    base = (mastery_gap * w['section_mastery_gap']
            + error * w['section_error'])
    return round(base * _prerequisite_factor(s) * _recency_factor(s), 4)


def _recency_factor(s):
    """Faktor pengulangan (Tahap 3), netral bila tidak ada data latihan."""
    hours = s.get('practice_hours')
    if hours is None:
        return 1.0
    if hours < cfg.REC_COOLDOWN_HOURS:
        return cfg.REC_COOLDOWN_FACTOR
    days = s.get('practice_days')
    if days is not None and days >= cfg.REC_STALE_DAYS:
        return cfg.REC_STALE_BOOST
    return 1.0


def _practice_recency_map(student_id):
    """section_id -> {'hours', 'days'} sejak latihan terakhir siswa.

    Satu query berkelompok untuk SEMUA bagian (PracticeAnswer.answered_at),
    bukan query per bagian. Bagian yang tidak pernah dilatih tidak ada di
    peta ini - dan ketidakhadiran itu sengaja dijaga tetap netral
    (REC_COOLDOWN/BOST tidak berlaku, tidak mengarang).
    """
    rows = db.session.query(
        PracticeAnswer.section_id,
        db.func.max(PracticeAnswer.answered_at),
    ).filter(PracticeAnswer.student_id == student_id).group_by(
        PracticeAnswer.section_id).all()
    now = datetime.utcnow()
    out = {}
    for section_id, last_at in rows:
        if last_at is None:
            continue
        hours = max(0.0, (now - last_at).total_seconds() / 3600.0)
        out[int(section_id)] = {'hours': hours, 'days': hours / 24.0}
    return out


def _section_reasons(s):
    """Reasons for a RANKED section. Every number here is real data."""
    reasons = []
    hours = s.get('practice_hours')
    if hours is not None and hours < cfg.REC_COOLDOWN_HOURS:
        reasons.append('Baru kamu latih - ulangi besok agar lebih efektif')
    elif (s.get('practice_days') or 0) >= cfg.REC_STALE_DAYS:
        reasons.append(f'Belum kamu sentuh {round(s["practice_days"])} hari')
    if s.get('prerequisite_met') is False:
        unmet = [p for p in (s.get('prerequisites') or [])
                 if p.get('met') is False]
        title = unmet[0].get('prerequisite_title') if unmet else None
        if title:
            reasons.append(f'Prasyarat belum tuntas: "{title}"')
    score = s.get('score')
    if score is not None and score < cfg.REC_PASS_SCORE:
        reasons.append(f'Penguasaan bagian ini baru {score:.0f}%')
    answered = s.get('answered') or 0
    wrong = max(0, answered - (s.get('correct') or 0))
    if wrong:
        reasons.append(f'Masih {wrong} jawaban salah dari {answered}')
    sources = s.get('score_sources') or []
    if sources:
        reasons.append('Bukti: ' + ', '.join(sources))
    if not reasons:
        reasons.append('Bagian ini sudah dikuasai dengan baik')
    return reasons[:4]


def _section_hint_reasons(s):
    """Reasons for an UNRANKED section. No score is claimed at all."""
    answered = s.get('answered') or 0
    if answered == 0:
        return ['Belum ada jawaban di bagian ini']
    return [f'Baru {answered} jawaban - belum cukup untuk dinilai']


def recommend_sections_for_student(student):
    """Sections this student most needs to work on, weakest first (Fase 3e).

    Returns two kinds of item in one list, and the difference is explicit
    rather than smoothed over:

    - **ranked** (`ranked: true`, numeric `score`): sections whose mastery
      is genuinely READY, ordered by need. These are what get persisted.
    - **hints** (`ranked: false`, `score: null`): sections whose answers are
      still too few to judge. Their raw counts are reported, but they are
      deliberately NOT ranked - ordering them would invent a priority the
      data cannot support. Hints are never persisted, so no 0.0 is ever
      written to the database pretending to be a priority.

    Sections already mastered (>= HIGH_MASTERY_CUTOFF) are dropped, the
    same way the material ranking drops mastered materials.
    """
    ranked, hints = [], []
    # Graph prasyarat + peta penguasaan dihitung SEKALI untuk semua materi,
    # bukan per materi. Graph-nya bisa lintas materi, jadi prasyarat sebuah
    # bagian bisa berada di materi lain dan tetap bisa dinilai di sini.
    context = analytics.student_section_context(student)
    # Tahap 3: jam/hari sejak latihan terakhir siswa di tiap bagian, satu
    # query. Dipakai score_section (cooldown + boost) dan alasan teks.
    recency = _practice_recency_map(student.id)
    for material in analytics.student_accessible_materials(student):
        data = analytics.section_mastery_for_student(
            student.id, material.id, context=context)
        for row in data['sections']:
            item = {
                'material_id': material.id,
                'section_id': row['section_id'],
                'material_title': material.title,
                'section_title': row['title'],
                'position': row['position'],
                'status': row['status'],
                'answered': row['answered'],
                'correct': row['correct'],
                'wrong': row['wrong'],
                'mastery_score': row['score'],
                'mastery_label': (row.get('mastery') or {}).get('label'),
                'sources': row.get('score_sources') or [],
                # Fase 4e (otomatis): apakah prasyarat bagian ini sudah tuntas.
                # True / False / None (belum bisa dinilai). Dipakai Commit
                # berikutnya untuk prioritas; di sini disajikan transparan dulu.
                'prerequisite_met': row.get('prerequisite_met'),
                'prerequisites': row.get('prerequisites') or [],
                # Tahap 3: default tak disentuh; diisi ulang untuk ranked.
                'recently_practiced': False,
                'days_since_practice': None,
            }
            if row['status'] != 'READY':
                # Below MIN_SECTION_SAMPLE: report counts, claim no score.
                item['ranked'] = False
                item['score'] = None
                item['reasons'] = _section_hint_reasons(row)
                hints.append(item)
                continue
            if (row['score'] or 0) >= cfg.HIGH_MASTERY_CUTOFF:
                continue
            # Tahap 3: tempel recency ke salinan baris agar score_section dan
            # alasan teks bisa membacanya. Bila bagian tak pernah dilatih,
            # `rec` kosong -> kunci practice_hours/days TIDAK dipasang ->
            # _recency_factor kembali 1.0 (netral, tidak mengarang).
            rec = recency.get(int(row['section_id']))
            row_scored = dict(row)
            if rec:
                row_scored['practice_hours'] = rec['hours']
                row_scored['practice_days'] = rec['days']
            item['ranked'] = True
            item['score'] = score_section(row_scored)
            item['reasons'] = _section_reasons(row_scored)
            item['recently_practiced'] = bool(
                rec and rec['hours'] < cfg.REC_COOLDOWN_HOURS)
            item['days_since_practice'] = (
                round(rec['days']) if rec else None)
            ranked.append(item)

    ranked.sort(key=lambda x: (-x['score'], x['material_id'], x['position']))
    ranked = ranked[:cfg.REC_SECTION_MAX_RESULTS]
    # Hints are NOT ranked - they carry no score. They are only ordered so
    # the list reads sensibly: sections that already have some answers come
    # first ("hampir cukup bukti"), never-touched sections come last.
    hints.sort(key=lambda x: (-x['answered'], x['material_id'], x['position']))
    hints = hints[:cfg.REC_SECTION_HINTS]

    results = ranked + hints
    # Rekomendasi adaptif Tahap 1: sertakan ketersediaan soal latihan supaya
    # UI bisa menawarkan tombol "Latihan adaptif" langsung dari dashboard dan
    # mematikannya dengan jujur saat guru belum menyetujui soal apa pun untuk
    # bagian itu. Satu query untuk semua bagian (approved_count_map).
    from src.services import student_practice_service as spractice
    counts = spractice.approved_count_map(
        [item['section_id'] for item in results])
    for item in results:
        total = counts.get(int(item['section_id']), 0)
        item['practice_available'] = total > 0
        item['practice_total'] = total

    # Only ranked sections are persisted: a hint has no score, and the
    # column is NOT NULL, so storing 0.0 for it would fabricate a priority.
    _persist_sections(student.id, ranked)
    return results


def recommend_for_student(student, student_row=None, model_version=None,
                          fallback_reason=None, meta=None):
    """Rank a student's materials. Try learned ranker if available; else rule-based.

    If `meta` is a dict, it is filled with the method that actually produced
    the returned order (`ranking_method`: 'ml' | 'rule' | 'fallback') so the
    API can report the truth instead of assuming the rule ran.
    """
    materials = analytics.student_accessible_materials(student)
    results = []
    all_mastered = True

    srow = student_row or {k: 0.0 for k in cfg.FEATURES}
    for material in materials:
        m = _material_metrics(student, material, srow)
        if m['mastery'] < cfg.HIGH_MASTERY_CUTOFF:
            all_mastered = False
        m['score'] = score_material(m)
        m['reasons'] = _reasons_for(m, srow)
        results.append(m)

    if not all_mastered:
        results = [r for r in results if r['mastery'] < cfg.HIGH_MASTERY_CUTOFF]
    else:
        for r in results:
            r['score'] = round(r['score'] * 0.5, 4)
            r['reasons'] = ['Materi sudah dikuasai. Ini adalah pengulangan untuk mempertahankan penguasaan.']

    # Rekomendasi adaptif: pakai ranker ML bila artifact tersedia dan layak.
    # Bila tidak, urutkan dengan rule transparan (perilaku lama) - tidak ada
    # regresi, dan ranking_method melaporkan mana yang benar-benar dipakai.
    artifact = None
    try:
        artifact = ranker_mod.load_ranker()
    except Exception:
        artifact = None

    material_map = {mat.id: mat for mat in materials}
    ranking_method = 'rule'
    if artifact and results:
        try:
            ml_scores = ranker_mod.predict_scores(srow, materials, artifact)
            for r in results:
                sm = ml_scores.get(r['material_id'])
                if sm is not None:
                    r['score_ml'] = sm
            if any(r.get('score_ml') is not None for r in results):
                results.sort(key=lambda x: (
                    -(x.get('score_ml') if x.get('score_ml') is not None else x['score']),
                    x['material_id']))
                ranking_method = 'ml'
                # The stored ranking is now genuinely produced by the ranker,
                # so it is correct (and required, for honesty) to attribute it
                # to the ranker's own version.
                model_version = (artifact.get('_meta') or {}).get('model_version')
                for r in results:
                    mat = material_map.get(r['material_id'])
                    try:
                        ml_reasons = ranker_mod.explain_ml(srow, mat, artifact)
                    except Exception:
                        ml_reasons = None
                    r['reasons_ml'] = ml_reasons
                    if ml_reasons:
                        r['reasons'] = ml_reasons
        except Exception:
            # Any failure in the ML path must degrade to the transparent
            # rule, never to an exception or an unattributed ranking.
            results.sort(key=lambda x: (-x['score'], x['material_id']))
            ranking_method = 'rule'
    else:
        results.sort(key=lambda x: (-x['score'], x['material_id']))

    results = results[:cfg.REC_MAX_RESULTS]
    _persist(student.id, results, 'fallback' if fallback_reason else ranking_method, model_version)
    if meta is not None:
        meta['ranking_method'] = 'fallback' if fallback_reason else ranking_method
    return results


def fallback_recommendations(student):
    """Cold-start / new-student fallback: recommended without ML claims."""
    materials = analytics.student_accessible_materials(student)
    rows = []
    for m in materials:
        base = analytics.material_row_for(student.id, m)
        rows.append({
            'material_id': m.id,
            'title': m.title,
            'topic': m.topic,
            'phase': m.phase,
            'estimated_time': m.estimated_time,
            'mastery': base['mastery_score'] or 0.0,
            'finished': base['status'] == 'selesai',
            'status': base['status'],
        })
    not_started = [r for r in rows if r['status'] == 'belum_dimulai']
    in_progress = [r for r in rows if r['status'] in ('dimulai', 'sedang_belajar')]
    ordered = sorted(not_started, key=lambda r: (r['estimated_time'] or '')) + in_progress
    ordered = ordered[:cfg.FALLBACK_RESULTS]
    for r in ordered:
        r['score'] = None
        r['reasons'] = ['Mulai belajar untuk mendapatkan rekomendasi yang lebih sesuai.']
    _persist(student.id, ordered, 'fallback', None)
    return ordered


def _persist(student_id, results, rec_type, model_version):
    keep = {item['material_id'] for item in results}

    # Drop rows this student no longer receives. Without this the table
    # only ever grows and existing_recommendations() keeps returning
    # materials that dropped out of the top-N, so the student sees stale
    # advice and the closed-loop evaluation counts clicks for
    # recommendations that are no longer on screen.
    #
    # `section_id IS NULL` is load-bearing: without it this would delete
    # every SECTION-level row (Fase 3e) on each material refresh, because
    # their material_id may well not be in `keep`.
    stale = Recommendation.query.filter(
        Recommendation.student_id == student_id,
        Recommendation.section_id.is_(None),
        Recommendation.material_id.notin_(keep) if keep else True).all()
    for s in stale:
        db.session.delete(s)

    for item in results:
        record = Recommendation.query.filter_by(
            student_id=student_id, material_id=item['material_id'],
            section_id=None).first()
        if record is None:
            record = Recommendation(student_id=student_id, material_id=item['material_id'])
            db.session.add(record)
        record.recommendation_score = float(item.get('score') or 0.0)
        record.reason_json = item.get('reasons') or []
        record.recommendation_type = rec_type
        record.model_version = model_version
        record.created_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _persist_sections(student_id, ranked_sections):
    """Persist RANKED section rows without touching material-level rows.

    Only ranked items arrive here; hints are display-only and never stored,
    so no 0.0 is written to a NOT NULL column pretending to be a priority.
    """
    keep = {(i['material_id'], i['section_id']) for i in ranked_sections}

    stale = Recommendation.query.filter(
        Recommendation.student_id == student_id,
        Recommendation.section_id.isnot(None)).all()
    for r in stale:
        if (r.material_id, r.section_id) not in keep:
            db.session.delete(r)

    for item in ranked_sections:
        record = Recommendation.query.filter_by(
            student_id=student_id, material_id=item['material_id'],
            section_id=item['section_id']).first()
        if record is None:
            record = Recommendation(student_id=student_id,
                                   material_id=item['material_id'],
                                   section_id=item['section_id'])
            db.session.add(record)
        record.recommendation_score = float(item.get('score') or 0.0)
        record.reason_json = item.get('reasons') or []
        # Rule-based, exactly like the material level: no trained model is
        # consulted for the ordering, so it is never labelled 'ml' and
        # model_version stays NULL.
        record.recommendation_type = 'rule'
        record.model_version = None
        record.created_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def mark_clicked(student_id, material_id, section_id=None):
    from src.services.learning_analytics_service import log_activity
    q = Recommendation.query.filter_by(student_id=student_id, material_id=material_id)
    # A section click must touch the SECTION row only, never the
    # material-level one, and vice versa.
    q = q.filter_by(section_id=int(section_id)) if section_id else q.filter(
        Recommendation.section_id.is_(None))
    records = q.all()
    now = datetime.utcnow()
    for r in records:
        if r.clicked_at is None:
            r.clicked_at = now
    db.session.commit()
    log_activity(student_id, material_id, 'recommendation_clicked', data={'at': now.isoformat()})
    return len(records) > 0


def mark_completed(student_id, material_id):
    # Material-level only: finishing a material is not the same event as
    # finishing one section, and conflating them would make section rows
    # look completed when the student only got to the end of the material.
    records = Recommendation.query.filter(
        Recommendation.student_id == student_id,
        Recommendation.material_id == material_id,
        Recommendation.section_id.is_(None)).all()
    if not records:
        return False
    now = datetime.utcnow()
    for r in records:
        if r.completed_at is None:
            r.completed_at = now
    db.session.commit()
    return True


def existing_recommendations(student_id):
    # Material-level rows only. Section rows (Fase 3e) live in the same
    # table, and mixing the two levels in one ranked list would compare
    # scores that were never meant to be compared.
    rows = Recommendation.query.filter(
        Recommendation.student_id == student_id,
        Recommendation.section_id.is_(None)).order_by(
        Recommendation.recommendation_score.desc()).limit(cfg.REC_MAX_RESULTS).all()
    return [{
        'material_id': r.material_id,
        'title': r.material.title if r.material else None,
        'topic': r.material.topic if r.material else None,
        'phase': r.material.phase if r.material else None,
        'estimated_time': r.material.estimated_time if r.material else None,
        'score': r.recommendation_score,
        'reasons': r.reason_json or [],
        'recommendation_type': r.recommendation_type,
        'model_version': r.model_version,
        'created_at': r.created_at.isoformat() + 'Z' if r.created_at else None,
        'clicked_at': r.clicked_at.isoformat() + 'Z' if r.clicked_at else None,
    } for r in rows]