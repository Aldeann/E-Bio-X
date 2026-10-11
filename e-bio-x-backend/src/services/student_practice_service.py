"""Student-side practice on approved bank questions (Fase 3d).

Three rules hold everything together:

1. Only ``QuestionBank.status == 'APPROVED'`` rows are ever served. A DRAFT or
   REJECTED question is invisible here even to the teacher who wrote it, so an
   AI draft can never reach a student before a human decided it should.
2. The server never sends the key. Question payloads carry option text only;
   ``is_correct`` appears for the first time in the answer response.
3. Nothing is invented. A section with no approved questions returns an empty
   list plus a plain reason - it never falls back to another section, and never
   produces a question of its own.

Session (Fase 3f): the ORDER of those approved questions is adaptive. The
target level comes from the student's own practice answers on this section,
labeled with the MEASURED difficulty (p-value) when enough other students
answered, else with the teacher's declared label. The 60/30/10 mix only
reorders questions that already exist - it never creates new ones.
"""
from datetime import datetime

from src.config.database import db
from src.models.question_bank import QuestionBank
from src.models.practice_answer import PracticeAnswer
from src.models.student_answer import StudentAnswer
from src.models.material_content import MaterialContent
from src.services import storage_service
from src.services import question_difficulty_service as qds
from src.ml import ml_config as cfg

# Long enough for any realistic section, short enough that the payload stays
# small. The real total is reported alongside so nothing looks trimmed.
MAX_SERVED = 20


def approved_for_section(section_id):
    """APPROVED practice questions of one section, in a stable order."""
    return QuestionBank.query.filter_by(
        section_id=section_id, status='APPROVED'
    ).order_by(QuestionBank.id).all()


def approved_count_map(section_ids):
    """section_id -> jumlah soal APPROVED. Satu query untuk semua bagian."""
    if not section_ids:
        return {}
    rows = db.session.query(
        QuestionBank.section_id, db.func.count(QuestionBank.id)
    ).filter(
        QuestionBank.section_id.in_(section_ids),
        QuestionBank.status == 'APPROVED',
    ).group_by(QuestionBank.section_id).all()
    return {int(sid): int(total or 0) for sid, total in rows}


def question_for_student(bq, difficulty=None, difficulty_basis=None,
                         difficulty_note=None):
    """Serialize a practice question WITHOUT the answer key.

    `explanation` and `misconception` are held back as well: both are teaching
    material for the answer, not part of the question.

    `difficulty` is the level actually used to place the question in the
    session: the MEASURED level (from performance) when it exists, else the
    teacher's declared label. `difficulty_basis` says which one it is and
    `difficulty_note` carries the source sentence (e.g. "63 siswa menjawab,
    73% benar (+-11 poin)"). The declared label is ALWAYS included separately
    as `declared_difficulty`, so a measured label never silently replaces it.
    """
    # Label guru TIDAK lagi diwajibkan; kosong berarti "belum ditentukan", jadi
    # jangan mengarang 'medium'. Bila belum ada label terukur maupun deklarasi,
    # `difficulty` tetap None dan konsumen boleh menampilkan "belum ditentukan".
    declared = (bq.difficulty or '').strip() or None
    return {
        'id': bq.id,
        'question_text': bq.question_text,
        'question_type': bq.question_type,
        'difficulty': difficulty or declared,
        'declared_difficulty': declared,
        'difficulty_basis': difficulty_basis or 'declared',
        'difficulty_note': difficulty_note,
        'points': bq.points,
        'image_url': storage_service.out_url(bq.image_url) if bq.image_url else None,
        'source': bq.source or 'teacher',
        'options': [{
            'option_id': o.id,
            'option_text': o.option_text,
            'order_index': o.order_index,
        } for o in sorted(bq.options, key=lambda x: x.order_index)],
    }


def grade(bq, selected_option):
    """Grade one answer. Returns the feedback payload shown after answering.

    `selected_option` is matched against the stored ``order_index`` rather than
    the option row the client asked for, so a hand-crafted request cannot pick
    the key directly.
    """
    options = sorted(bq.options, key=lambda x: x.order_index)
    chosen = None
    for opt in options:
        if opt.order_index == selected_option:
            chosen = opt
            break
    if chosen is None:
        return None

    correct_opt = next((o for o in options if o.is_correct), None)
    return {
        'bank_question_id': bq.id,
        'is_correct': bool(chosen.is_correct),
        'selected_option': chosen.order_index,
        'correct_option': correct_opt.order_index if correct_opt else None,
        # Feedback per option, so a wrong pick says why it was wrong instead of
        # only revealing the right one.
        'options': [{
            'order_index': o.order_index,
            'option_text': o.option_text,
            'is_correct': bool(o.is_correct),
            'feedback': o.feedback,
        } for o in options],
        'explanation': bq.explanation,
        'misconception': bq.misconception,
        'points': bq.points,
    }


def record(student_id, material_id, section_id, bq, graded):
    """Store one attempt. Repeated attempts are kept, not overwritten."""
    previous = db.session.query(db.func.count(PracticeAnswer.id)).filter_by(
        student_id=student_id, bank_question_id=bq.id
    ).scalar() or 0
    row = PracticeAnswer(
        student_id=student_id,
        material_id=material_id,
        section_id=section_id,
        bank_question_id=bq.id,
        selected_option=graded['selected_option'],
        is_correct=graded['is_correct'],
        attempt_no=int(previous) + 1,
        question_snapshot=bq.question_text,
        answered_at=datetime.utcnow(),
    )
    db.session.add(row)
    db.session.flush()
    return row


def latest_attempts(material_id, student_ids):
    """(section_id, student_id, bank_question_id, is_correct, attempts) per question.

    One row per (siswa, soal): jawaban TERAKHIR yang dihitung, bukan jumlah
    percobaan. Mengulang satu soal yang salah sampai benar tetap terhitung
    sebagai satu soal terjawab, jadi percobaan berulang tidak bisa besar-besaran
    menambah bukti sebuah bagian. Urutan dibuat eksplisit agar "terakhir" tidak
    bergantung pada urutan acak yang kembalikan database.
    """
    if isinstance(student_ids, (list, tuple, set)):
        ids = [int(s) for s in student_ids]
    else:
        ids = [int(student_ids)]
    if not ids:
        return []

    rows = db.session.query(
        PracticeAnswer.section_id,
        PracticeAnswer.student_id,
        PracticeAnswer.bank_question_id,
        PracticeAnswer.is_correct,
        PracticeAnswer.answered_at,
        PracticeAnswer.id,
    ).filter(
        PracticeAnswer.material_id == material_id,
        PracticeAnswer.student_id.in_(ids),
    ).order_by(
        PracticeAnswer.answered_at.asc(), PracticeAnswer.id.asc()).all()

    latest = {}
    attempts = {}
    for sid, stid, bqid, ok, _at, _rid in rows:
        key = (int(sid), int(stid), int(bqid))
        latest[key] = bool(ok)
        attempts[key] = attempts.get(key, 0) + 1

    return [(key[0], key[1], key[2], ok, attempts[key])
            for key, ok in latest.items()]


def practice_stats(student_id, material_id):
    """section_id -> hitungan latihan satu siswa (lihat latest_attempts)."""
    out = {}
    for sid, _stid, _bqid, ok, attempts in latest_attempts(material_id, student_id):
        bucket = out.setdefault(sid, {'answered': 0, 'correct': 0, 'attempts': 0})
        bucket['answered'] += 1
        bucket['attempts'] += attempts
        if ok:
            bucket['correct'] += 1
    return out


# ============================================================
# SESI LATIHAN ADAPTIF (Fase 3f)
# ============================================================
#
# Yang diadaptasi hanyalah URUTAN soal yang sudah ada. Soal baru tidak pernah
# dibuat, dan hanya soal APPROVED yang ikut (aturan nomor 1 tetap berlaku).
#
# Urutan: 60% tingkat sasaran (akurasi terendah siswa di bagian ini), 30% satu
# tingkat di bawah (fondasi), 10% satu tingkat di atas (tantangan). Sisa soal
# tetap ikut di belakang dengan urutan id yang stabil, jadi daftar soal tidak
# pernah berkurang dan tidak pernah berubah-ubah tanpa sebab.
#
# Tingkat tiap soal: diukur dari performa (p-value, leave-one-out) BILA sudah
# cukup data, selain itu pakai label guru. Rumus pilihan sasaran selalu ikut
# dikirim sebagai `session_basis` sehingga siswa/peninjau tahu yang menggerakkan
# sesi itu data atau asumsi.

_LEVEL_BELOW = {'easy': None, 'medium': 'easy', 'hard': 'medium'}
_LEVEL_ABOVE = {'easy': 'medium', 'medium': 'hard', 'hard': None}


def _level_label(level):
    """Label Indonesia untuk kunci tingkat ('easy' -> 'mudah')."""
    if not level:
        return ''
    return {'easy': 'mudah', 'medium': 'sedang', 'hard': 'sulit'}.get(level, level)


def _effective_levels(approved, observed):
    """bank_question_id -> {'label','basis','note'} untuk soal yang disetujui.

    'observed' menang bila statusnya READY; kalau tidak, deklarasi guru; kalau
    deklarasinya pun tidak dikenal, soal ini TIDAK dikasih tingkat sama sekali
    (bukan ditebak jadi 'sedang'). `note` berisi kalimat sumber pengukuran.
    """
    from src.services.learning_analytics_service import normalize_difficulty

    out = {}
    for bq in approved:
        obs = observed.get(int(bq.id))
        if obs and obs.get('status') == 'READY' and obs.get('label'):
            out[int(bq.id)] = {
                'label': obs['label'],
                'basis': 'observed',
                'note': qds.observed_note(obs),
                'obs': obs,
            }
            continue
        declared = normalize_difficulty(bq.difficulty)
        if declared:
            out[int(bq.id)] = {
                'label': declared,
                'basis': 'declared',
                'note': None,
                'obs': obs,
            }
        else:
            out[int(bq.id)] = {
                'label': None,
                'basis': 'unknown',
                'note': None,
                'obs': obs,
            }
    return out


def _diagnose(student, bank_effective_current, max_questions=400):
    """Akurasi siswa per tingkat dari SELURUH riwayat jawabannya.

    Sumbernya dua hal yang benar-benar tercatat:

    - jawaban latihan TERAKHIR per soal bank, dan
    - jawaban TERAKHIR per slot soal interaktif,

    Tiap soal diberi tingkat terukur (leave-one-out) bila cukup data, selain
    itu deklarasi guru. Cakupannya seluruh materi, bukan hanya bagian ini -
    sama seperti recommendation._student_weak_difficulty yang memakai
    akurasi per tingkat lintas materi untuk memilih sasaran belajar. Tingkat
    kesulitan tidak terikat topik, jadi "siswa lemah di soal sulit" berlaku
    umum; yang dibatasi tetap soalnya (hanya soal bagian ini yang disajikan).

    `bank_effective_current` dipakai agar jawaban latihan pada bagian ini
    memakai label yang sama dengan yang dipakai menyusun sesi (tidak dihitung
    dua kali dengan hasil yang bisa berbeda).

    Mengembalikan (per_level, basis_by_level, notes_by_level, counts).
    """
    from src.services.learning_analytics_service import normalize_difficulty

    per_level, basis_by_level, notes_by_level = {}, {}, {}
    counts = {'practice': 0, 'interactive': 0}
    current_ids = set(bank_effective_current.keys())

    def record(level, basis, correct, note):
        bucket = per_level.setdefault(level, {'total': 0, 'correct': 0})
        bucket['total'] += 1
        if correct:
            bucket['correct'] += 1
        basis_by_level.setdefault(level, set()).add(basis)
        if note:
            notes_by_level.setdefault(level, []).append(note)

    # --- 1) latihan bank: jawaban terakhir per soal, seluruh materi ---
    p_rows = PracticeAnswer.query.filter_by(student_id=student.id).all()
    if p_rows:
        latest = {}
        for r in sorted(p_rows, key=lambda x: (x.answered_at or datetime.min, x.id or 0)):
            latest[int(r.bank_question_id)] = bool(r.is_correct)
        latest = dict(list(latest.items())[:max_questions])
        other_ids = [bq_id for bq_id in latest if bq_id not in current_ids]
        other_effective = {}
        if other_ids:
            banks = QuestionBank.query.filter(QuestionBank.id.in_(other_ids)).all()
            observed = qds.observed_bank_batch(other_ids, exclude_student_id=student.id)
            other_effective = _effective_levels(banks, observed)
        merged = dict(other_effective)
        merged.update(bank_effective_current)
        for bq_id, ok in latest.items():
            entry = merged.get(bq_id)
            if not entry or not entry.get('label'):
                continue
            counts['practice'] += 1
            record(entry['label'], entry['basis'], ok, entry.get('note'))

    # --- 2) soal interaktif: jawaban terakhir per slot, seluruh materi ---
    ia_rows = StudentAnswer.query.filter_by(student_id=student.id).all()
    if ia_rows:
        latest_ia = {}
        for r in sorted(ia_rows, key=lambda x: (x.answered_at or datetime.min, x.id or 0)):
            latest_ia[qds.interactive_slot_key(r)] = bool(r.is_correct)
        latest_ia = dict(list(latest_ia.items())[:max_questions])
        content_ids = {slot[1] for slot in latest_ia if slot[1] is not None}
        contents = {c.id: c for c in MaterialContent.query.filter(
            MaterialContent.id.in_(content_ids)).all()} if content_ids else {}
        observed_ia = {}
        if content_ids:
            all_rows = StudentAnswer.query.filter(
                StudentAnswer.content_id.in_(content_ids)).all()
            observed_ia = qds.interactive_batch(all_rows, exclude_student_id=student.id)
        for slot, ok in latest_ia.items():
            obs = observed_ia.get(slot)
            if obs and obs.get('status') == 'READY' and obs.get('label'):
                counts['interactive'] += 1
                record(obs['label'], 'observed', ok, qds.observed_note(obs))
                continue
            content = contents.get(slot[1])
            data = content.data if content and isinstance(content.data, dict) else {}
            declared = normalize_difficulty(data.get('difficulty'))
            if declared:
                counts['interactive'] += 1
                record(declared, 'declared', ok, None)

    return per_level, basis_by_level, notes_by_level, counts


def _weakest_level(per_level):
    """Tingkat terlemah yang benar-benar dijawab, atau None.

    Hanya tingkat yang punya minimal satu jawaban dipertimbangkan (persis
    seperti recommendation._student_weak_difficulty). Seri dipecah ke tingkat
    yang lebih mendasar dulu, karena ketika semua akurasi 0 hal yang paling
    aman dikerjakan duluan adalah yang paling dasar.
    """
    order = cfg.SESSION_LEVEL_ORDER
    attempted = [lvl for lvl in order if per_level.get(lvl, {}).get('total', 0) > 0]
    if not attempted:
        return None

    def key(lvl):
        acc = per_level[lvl]['correct'] / per_level[lvl]['total']
        return (acc, order.index(lvl))

    return min(attempted, key=key)


def _order_questions(approved, effective, target):
    """Urutkan soal sesuai komposisi 60/30/10 tanpa menghilangkan soal apa pun."""
    if not target:
        return list(approved)

    queues = {lvl: [] for lvl in cfg.SESSION_LEVEL_ORDER}
    for bq in approved:
        level = (effective.get(int(bq.id)) or {}).get('label')
        if level in queues:
            queues[level].append(bq)

    total = len(approved)
    n_target = round(total * cfg.SESSION_MIX_TARGET)
    n_below = round(total * cfg.SESSION_MIX_BELOW)
    n_above = max(total - n_target - n_below, 0)
    below = _LEVEL_BELOW[target]
    above = _LEVEL_ABOVE[target]

    chosen = []
    chosen += queues[target][:n_target]
    if below:
        chosen += queues[below][:n_below]
    if above:
        chosen += queues[above][:n_above]

    chosen_ids = {bq.id for bq in chosen}
    # Sisa semua soal (termasuk sisa kuota tiap tingkat) ikut di belakang,
    # urutan id stabil. Soal tanpa tingkat ikut di sini - bukan ditebak
    # tingkatnya, cuma tidak ditempatkan di komposisi.
    chosen += [bq for bq in approved if bq.id not in chosen_ids]
    return chosen


def session_for_section(material_id, section_id, student):
    """Sesi latihan adaptif satu bagian: (soal terurut, deskripsi sesi).

    Tidak pernah membuat soal, tidak pernah memakai soal di luar APPROVED, dan
    tidak pernah mengklaim sesuatu yang tidak diketahuinya: bila siswa belum
    menjawab apa pun di bagian ini, basis-nya 'sequential' (urutan stabil)
    bukan "sasaran dari performa".
    """
    approved = approved_for_section(section_id)
    if not approved:
        return [], {'basis': 'empty', 'basis_text': 'Bagian ini belum punya soal latihan yang disetujui guru.'}

    observed = qds.observed_bank_batch([bq.id for bq in approved],
                                       exclude_student_id=student.id)
    effective = _effective_levels(approved, observed)

    # --- diagnosis: akurasi siswa per tingkat dari seluruh riwayat jawabannya ---
    per_level, basis_by_level, notes_by_level, counts = _diagnose(student, effective)

    target = _weakest_level(per_level)

    # --- komposisi 60/30/10 ---
    ordered = _order_questions(approved, effective, target)
    total = len(approved)
    mix = {'target': 0, 'below': 0, 'above': 0}
    if target:
        mix = {
            'target': round(total * cfg.SESSION_MIX_TARGET),
            'below': round(total * cfg.SESSION_MIX_BELOW),
            'above': max(total - round(total * cfg.SESSION_MIX_TARGET)
                         - round(total * cfg.SESSION_MIX_BELOW), 0),
        }

    # --- basis: bagaimana sasaran itu terbentuk ---
    answered_total = counts['practice'] + counts['interactive']
    answered_txt = (f"{answered_total} jawabanmu ({counts['practice']} latihan + "
                    f"{counts['interactive']} interaktif) di semua materi")
    if target is None:
        basis = 'sequential'
        if answered_total:
            basis_text = ('Jawabanmu ada, tapi tingkat soalnya belum cukup data untuk diukur, '
                          'jadi soal disajikan berurutan.')
        else:
            basis_text = ('Belum ada jawabanmu yang tercatat, jadi soal disajikan berurutan sesuai id soal.')
    else:
        stats = per_level[target]
        acc = round(stats['correct'] / stats['total'] * 100, 1)
        target_sources = basis_by_level.get(target, set())
        target_notes = notes_by_level.get(target, [])
        if 'observed' in target_sources:
            basis = 'observed'
            source = target_notes[0] if target_notes else 'tingkat terukur dari performa siswa lain'
            basis_text = (
                f"Sasaran setingkat {_level_label(target)}: akurasmu {acc}% pada "
                f"{stats['total']} soal setingkat ini, dari {answered_txt}. "
                f"Tingkat soal dihitung dari performa - {source} "
                f"(leave-one-out, tanpa jawabanmu sendiri)."
            )
        elif 'declared' in target_sources:
            basis = 'declared'
            basis_text = (
                f"Sasaran setingkat {_level_label(target)}: akurasmu {acc}% pada "
                f"{stats['total']} soal setingkat ini, dari {answered_txt}. "
                f"Tingkat soalnya belum punya cukup data performa, "
                f"jadi memakai label guru (deklarasi)."
            )
        else:
            basis = 'sequential'
            basis_text = 'Tingkat soal tidak diketahui, jadi urutan tidak diubah.'

    entries = []
    for bq in ordered:
        entry = effective.get(int(bq.id)) or {}
        entries.append({
            'bq': bq,
            'label': entry.get('label'),
            'basis': entry.get('basis', 'unknown'),
            'note': entry.get('note'),
            'obs': entry.get('obs'),
        })

    session = {
        'basis': basis,
        'basis_text': basis_text,
        'target_level': target,
        'target_label': _level_label(target),
        'target_accuracy': (round(per_level[target]['correct'] / per_level[target]['total'] * 100, 1)
                            if target else None),
        'target_answered': (per_level[target]['total'] if target else 0),
        'answered_practice': counts['practice'],
        'answered_interactive': counts['interactive'],
        'mix': mix,
        'total': total,
        'served': min(total, MAX_SERVED),
        'note': ('Urutan sesi: 60% sasaran, 30% satu tingkat di bawah, 10% di atas. '
                 'Hanya soal yang disetujui guru; soal baru tidak pernah dibuat.'),
    }
    return entries, session