"""Langkah berikutnya / Next Best Action (Fase 5).

Satu KEPUTUSAN, bukan daftar: dari sinyal yang sudah ada, pilih SATU aksi
paling masuk akal untuk siswa saat ini, lengkap dengan alasan yang bisa
diaudit. Ini lapisan tipis di atas sinyal yang sama dengan rekomendasi -
bukan ranker kedua dan bukan model baru. Mastery tetap dibaca dari
`section_mastery_for_student` (diagnosis yang sudah ada), bukan dihitung
ulang dengan rumus baru.

Sumber sinyal (semuanya sudah dipakai fitur lain):
- penguasaan & bukti per bagian: analytics.section_mastery_for_student
- ketersediaan soal latihan: student_practice_service.approved_count_map
- progres baca per bagian: analytics.completed_section_ids (MaterialProgress)
- status materi: analytics.material_row_for
- kuis tertunda: Quiz + Submission
- kebaruan latihan: recommendation._practice_recency_map

Aturan jujur: bila tidak ada aksi yang benar-benar didukung data, kembalikan
type 'done' dengan alasan apa adanya - jangan mengarang langkah.
"""
from datetime import datetime

from src.ml import ml_config as cfg
from src.ml import recommendation as rec_service
from src.models.material_section import MaterialSection
from src.models.quiz import Quiz
from src.models.submission import Submission
from src.services import learning_analytics_service as analytics
from src.services import student_practice_service as spractice


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _done(message=None):
    return {
        'action': {
            'type': 'done',
            'priority': cfg.NBA_WEIGHTS.get('done', 0.0),
            'title': 'Semua beres',
            'reason': message or 'Belum ada langkah lanjutan yang jujur untuk '
                                 'disarankan sekarang.',
            'reason_source': 'none',
            'cta': None,
            'meta': {},
        },
        'alternatives': [],
        'basis': 'rule',
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'context': {},
    }


def _section_title(srow):
    return srow.get('title') or 'bagian ini'


def next_action_for_student(student, material_id=None, section_id=None,
                            context=None):
    """Pilih satu langkah berikutnya untuk `student`.

    `material_id`/`section_id` opsional: dipakai halaman yang sedang dibuka
    untuk mendorong aksi yang nyambung (lihat NBA_CONTEXT_*_BOOST). `context`
    teks bebas (mis. 'just_finished_section') diteruskan apa adanya.
    """
    materials = analytics.student_accessible_materials(student)
    if not materials:
        return _done('Belum ada materi untukmu. Hubungi gurumu.')

    ctx_material = _to_int(material_id)
    ctx_section = _to_int(section_id)
    material_ids = [m.id for m in materials]
    material_by_id = {m.id: m for m in materials}

    # --- sinyal bersama, dihitung sekali ---
    rows = [analytics.material_row_for(student.id, m) for m in materials]
    row_by_material = {r['material_id']: r for r in rows}
    context_ctx = analytics.student_section_context(student)
    recency = rec_service._practice_recency_map(student.id)

    sections = MaterialSection.query.filter(
        MaterialSection.material_id.in_(material_ids)).order_by(
        MaterialSection.position).all()
    sections_by_material = {}
    for sec in sections:
        sections_by_material.setdefault(sec.material_id, []).append(sec)
    practice_counts = spractice.approved_count_map([s.id for s in sections])

    quizzes = Quiz.query.filter(Quiz.material_id.in_(material_ids)).all()
    taken_quiz_ids = {s.quiz_id for s in Submission.query.filter_by(
        student_id=student.id).all()}

    def _boost(mid, sid=None):
        boost = 0.0
        if ctx_material is not None and mid == ctx_material:
            boost += cfg.NBA_CONTEXT_MATERIAL_BOOST
        if ctx_section is not None and sid is not None and sid == ctx_section:
            boost += cfg.NBA_CONTEXT_SECTION_BOOST
        return boost

    def _add(cands, ctype, mid, sid, title, reason, reason_source, cta, meta,
             need=0.0):
        base = cfg.NBA_WEIGHTS.get(ctype, 0.0)
        cands.append({
            'type': ctype,
            'priority': round(base + need + _boost(mid, sid), 4),
            'title': title,
            'reason': reason,
            'reason_source': reason_source,
            'cta': cta,
            'meta': meta,
        })

    candidates = []

    # Materi yang sedang dikerjakan (paling baru diakses, belum selesai).
    started = [r for r in rows if r['status'] in ('dimulai', 'sedang_belajar')]
    started.sort(key=lambda r: (r['last_accessed'] or ''), reverse=True)
    active_id = started[0]['material_id'] if started else None

    for m in materials:
        mid = m.id
        row = row_by_material.get(mid) or {}
        done_ids = analytics.completed_section_ids(student.id, mid)
        data = analytics.section_mastery_for_student(
            student.id, mid, context=context_ctx)
        for srow in data['sections']:
            sid = srow['section_id']
            p_total = int(practice_counts.get(int(sid), 0))
            rec = recency.get(int(sid))
            is_done = sid in done_ids
            stitle = _section_title(srow)
            if srow['status'] == 'READY':
                score = srow.get('score') or 0.0
                if score < cfg.PRACTICE_PASS_SCORE:
                    if p_total > 0:
                        need = max(0.0, (cfg.PRACTICE_PASS_SCORE - score)) / 100.0
                        _add(candidates, 'practice_weak', mid, sid,
                             f'Latihan adaptif: {stitle}',
                             f'Akurasi bagian ini {score:.0f}% - di bawah '
                             f'tuntas {cfg.PRACTICE_PASS_SCORE}%.',
                             'section_mastery',
                             {'kind': 'practice', 'label': 'Latihan adaptif',
                              'material_id': mid, 'section_id': sid,
                              'section_title': stitle},
                             {'mastery': score, 'pass_score': cfg.PRACTICE_PASS_SCORE,
                              'practice_total': p_total,
                              'practice_answered': srow.get('practice_answered', 0)},
                             need=need)
                    elif is_done:
                        # Lemah tapi belum ada soal latihan yang disetujui:
                        # jangan menawarkan tombol latihan yang kosong.
                        _add(candidates, 'continue_reading', mid, sid,
                             f'Pelajari ulang: {stitle}',
                             f'Akurasi bagian ini {score:.0f}%, tetapi belum '
                             f'ada soal latihan untuk bagian ini.',
                             'section_mastery',
                             {'kind': 'read', 'label': 'Buka materi',
                              'material_id': mid, 'section_id': sid},
                             {'mastery': score, 'practice_total': 0})
                else:
                    # Sudah tuntas: hanya diangkat bila lama tak disentuh.
                    stale = (rec is None) or (rec['days'] >= cfg.NBA_REVIEW_STALE_DAYS)
                    if stale:
                        days = round(rec['days']) if rec else None
                        reason = ('Sudah tuntas, tapi belum kamu sentuh lagi '
                                  f'{days} hari.' if days is not None
                                  else 'Sudah tuntas. Ulangi untuk menjaga ingatan.')
                        _add(candidates, 'review_mastered', mid, sid,
                             f'Ulangi: {stitle}', reason, 'practice_recency',
                             {'kind': 'practice' if p_total > 0 else 'read',
                              'label': 'Latihan adaptif' if p_total > 0 else 'Buka materi',
                              'material_id': mid, 'section_id': sid,
                              'section_title': stitle},
                             {'mastery': score, 'practice_total': p_total,
                              'days_since_practice': days})
            else:
                # Bukti belum cukup untuk menilai (INSUFFICIENT_DATA).
                if is_done and p_total > 0 and srow.get('practice_answered', 0) == 0:
                    _add(candidates, 'practice_after_read', mid, sid,
                         f'Latihan adaptif: {stitle}',
                         'Bagian ini sudah kamu baca, tapi belum pernah dilatih.',
                         'material_progress+practice',
                         {'kind': 'practice', 'label': 'Latihan adaptif',
                          'material_id': mid, 'section_id': sid,
                          'section_title': stitle},
                         {'practice_total': p_total, 'practice_answered': 0},
                         need=0.3)
                elif not is_done and mid == active_id:
                    _add(candidates, 'continue_reading', mid, sid,
                         f'Lanjutkan: {stitle}',
                         f'Materi "{m.title}" belum selesai kamu baca.',
                         'material_progress',
                         {'kind': 'read', 'label': 'Lanjutkan membaca',
                          'material_id': mid, 'section_id': sid},
                         {'progress': row.get('progress_percentage')})

        # Kuis tertunda: materi sudah disentuh, kuis dipublikasikan, belum dinilai.
        if row.get('status') in ('sedang_belajar', 'selesai'):
            for q in quizzes:
                if q.material_id != mid or q.status != 'published' or q.is_closed:
                    continue
                if q.id in taken_quiz_ids:
                    continue
                _add(candidates, 'take_quiz', mid, None,
                     f'Kerjakan kuis: {q.title}',
                     'Kamu sudah membaca materinya; kuis ini belum kamu kerjakan.',
                     'quiz+submission',
                     {'kind': 'quiz', 'label': 'Kerjakan kuis',
                      'material_id': mid, 'quiz_id': q.id},
                     {'quiz_id': q.id})
                break  # satu kuis tertunda per materi sudah cukup

    # Materi berikutnya: bila materi aktif sudah selesai (atau belum ada).
    if active_id is None:
        next_m = _first_unfinished(materials, row_by_material)
        if next_m is not None:
            _add(candidates, 'start_next_material', next_m.id, None,
                 f'Mulai materi: {next_m.title}',
                 'Ini materi yang belum kamu mulai.',
                 'material_status',
                 {'kind': 'material', 'label': 'Buka materi',
                  'material_id': next_m.id},
                 {})
    else:
        active_row = row_by_material.get(active_id) or {}
        if active_row.get('status') == 'selesai':
            next_m = _first_unfinished(materials, row_by_material)
            if next_m is not None:
                _add(candidates, 'start_next_material', next_m.id, None,
                     f'Mulai materi: {next_m.title}',
                     'Materi sebelumnya sudah kamu selesaikan.',
                     'material_status',
                     {'kind': 'material', 'label': 'Buka materi',
                      'material_id': next_m.id},
                     {})

    if not candidates:
        return _done()

    # Urutkan: prioritas menurun, lalu tipe (bobot dasar), lalu id agar stabil.
    candidates.sort(key=lambda c: (-c['priority'],
                                   -cfg.NBA_WEIGHTS.get(c['type'], 0.0),
                                   c['cta']['material_id'] if c['cta'] else 0,
                                   (c['cta'].get('section_id') or 0) if c['cta'] else 0))

    action = candidates[0]
    alternatives = [c for c in candidates[1:] if not _same_target(c, action)][:2]
    return {
        'action': action,
        'alternatives': alternatives,
        'basis': 'rule',
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'context': {'material_id': ctx_material, 'section_id': ctx_section,
                    'context': context},
    }


def _first_unfinished(materials, row_by_material):
    """Materi paling awal yang belum selesai (deterministik, tanpa skor)."""
    for m in materials:
        row = row_by_material.get(m.id) or {}
        if row.get('status') != 'selesai':
            return m
    return None


def _same_target(a, b):
    ca, cb = a.get('cta') or {}, b.get('cta') or {}
    return (ca.get('material_id') == cb.get('material_id')
            and ca.get('section_id') == cb.get('section_id')
            and ca.get('quiz_id') == cb.get('quiz_id'))
