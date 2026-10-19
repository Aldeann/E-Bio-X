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
from src.services import storage_service
from src.services import question_difficulty_service as qds
from src.ml import ml_config as cfg

# Jendela jalur DIAGNOSTIK: urutan tetap dan jumlahnya kecil (beberapa soal per
# bagian), jadi 20 cukup memuat semuanya sekaligus. Jalur LATIHAN adaptif
# memakai SESSION_SIZE + rotasi di bawah, bukan MAX_SERVED.
MAX_SERVED = 20

# Jendela satu sesi latihan adaptif (lihat ml_config.SESSION_SIZE untuk alasan
# angkanya). Nilainya diambil dari konfigurasi supaya ambang sesi tinggal
# diubah di satu tempat.
SESSION_SIZE = cfg.SESSION_SIZE


def approved_for_section(section_id):
    """APPROVED practice questions of one section, in a stable order.

    `purpose='practice'` is what keeps the ADAPTIVE session (and the plain
    question list shown to students) free of diagnostic questions. The two
    sets must never mix: a diagnostic answer would drag the 60/30/10 mix
    towards a fixed question, and a practice answer would drag the measured
    difficulty of the material towards a question deliberately aimed at the
    student's weakest level.
    """
    return QuestionBank.query.filter_by(
        section_id=section_id, status='APPROVED', purpose='practice'
    ).order_by(QuestionBank.id).all()


def diagnostic_for_section(section_id):
    """APPROVED diagnostic questions of one section, stable order (no mix).

    Fixed order, never reshuffled: the diagnostic set is only comparable
    between students because everyone answers the same questions in the
    same sequence.
    """
    return QuestionBank.query.filter_by(
        section_id=section_id, status='APPROVED', purpose='diagnostic'
    ).order_by(QuestionBank.id).all()


def approved_count_map(section_ids):
    """section_id -> jumlah soal latihan APPROVED. Satu query untuk semua bagian."""
    if not section_ids:
        return {}
    rows = db.session.query(
        QuestionBank.section_id, db.func.count(QuestionBank.id)
    ).filter(
        QuestionBank.section_id.in_(section_ids),
        QuestionBank.status == 'APPROVED',
        QuestionBank.purpose == 'practice',
    ).group_by(QuestionBank.section_id).all()
    return {int(sid): int(total or 0) for sid, total in rows}


def diagnostic_count_map(section_ids):
    """section_id -> jumlah soal diagnostik APPROVED. Satu query untuk semua bagian.

    Terpisah dari `approved_count_map` supaya UI tidak pernah menjumlahkan
    dua pool yang berbeda lalu menyebutnya "soal latihan".
    """
    if not section_ids:
        return {}
    rows = db.session.query(
        QuestionBank.section_id, db.func.count(QuestionBank.id)
    ).filter(
        QuestionBank.section_id.in_(section_ids),
        QuestionBank.status == 'APPROVED',
        QuestionBank.purpose == 'diagnostic',
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


def record(student_id, material_id, section_id, bq, graded, mode='practice'):
    """Store one attempt. Repeated attempts are kept, not overwritten.

    `mode` is the honest marker of which lane wrote this row: 'practice' for
    adaptive answers, 'diagnostic' for Asesmen Diagnostik. The material level
    reads only 'diagnostic' rows (see material_level_observed).
    """
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
        mode=mode or 'practice',
        answered_at=datetime.utcnow(),
    )
    db.session.add(row)
    db.session.flush()
    return row


def latest_attempts(material_id, student_ids, mode=None):
    """(section_id, student_id, bank_question_id, is_correct, attempts) per question.

    One row per (siswa, soal): jawaban TERAKHIR yang dihitung, bukan jumlah
    percobaan. Mengulang satu soal yang salah sampai benar tetap terhitung
    sebagai satu soal terjawab, jadi percobaan berulang tidak bisa besar-besaran
    menambah bukti sebuah bagian. Urutan dibuat eksplisit agar "terakhir" tidak
    bergantung pada urutan acak yang kembalikan database.

    `mode` menyaring jalur jawaban ('practice' atau 'diagnostic'). `None` berarti
    semua jalur, yang dipakai oleh hitungan latihan biasa.
    """
    if isinstance(student_ids, (list, tuple, set)):
        ids = [int(s) for s in student_ids]
    else:
        ids = [int(student_ids)]
    if not ids:
        return []

    query = db.session.query(
        PracticeAnswer.section_id,
        PracticeAnswer.student_id,
        PracticeAnswer.bank_question_id,
        PracticeAnswer.is_correct,
        PracticeAnswer.answered_at,
        PracticeAnswer.id,
    ).filter(
        PracticeAnswer.material_id == material_id,
        PracticeAnswer.student_id.in_(ids),
    )
    if mode:
        query = query.filter(PracticeAnswer.mode == mode)

    rows = query.order_by(
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


def diagnostic_stats(student_id, material_id):
    """section_id -> hitungan ASESMEN DIAGNOSTIK satu siswa.

    Terpisah dari `practice_stats` dengan sengaja: angka latihan adaptif dan
    angka diagnostik menjawab dua pertanyaan berbeda (sedang berlatih vs
    sampel pengukuran yang netral) dan tidak pernah dijumlahkan. Sumber
    hitungannya tetap `latest_attempts` - satu soal dihitung dari jawaban
    terakhir - supaya dua fungsi ini tidak bisa berbeda aturan. Yang menambah
    ketat di sini adalah `mode='diagnostic'`: sebuah soal yang tadinya latihan
    lalu guru tandai diagnostik tidak otomatis dianggap "sudah dikerjakan"
    hanya karena ada jawaban lamanya.
    """
    from src.models.material_section import MaterialSection

    section_ids = [s.id for s in MaterialSection.query.filter_by(
        material_id=material_id).all()]
    if not section_ids:
        return {}
    diag_ids = {int(b.id) for b in QuestionBank.query.filter(
        QuestionBank.section_id.in_(section_ids),
        QuestionBank.purpose == 'diagnostic',
    ).all()}
    if not diag_ids:
        return {}

    out = {}
    for sid, _stid, bqid, ok, attempts in latest_attempts(
            material_id, student_id, mode='diagnostic'):
        if int(bqid) not in diag_ids:
            continue
        bucket = out.setdefault(sid, {'answered': 0, 'correct': 0, 'attempts': 0})
        bucket['answered'] += 1
        bucket['attempts'] += attempts
        if ok:
            bucket['correct'] += 1
    return out


def section_progress(student_id, material_id, section_id):
    """Ringkasan latihan SATU bagian: answered/correct/accuracy.

    Sumbernya sama dengan practice_stats - jawaban TERAKHIR per soal - jadi
    mengulang satu soal sampai benar tidak menambah bukti. `accuracy` None bila
    belum ada jawaban (tidak mengarang 0%). Dipakai untuk menentukan status
    keluar sesi (tuntas / sedang berlatih), bukan untuk skor resmi.
    """
    answered = correct = 0
    for sid, _stid, _bqid, ok, _attempts in latest_attempts(material_id, student_id):
        if int(sid) != int(section_id):
            continue
        answered += 1
        if ok:
            correct += 1
    accuracy = round(correct / answered * 100, 1) if answered else None
    return {'answered': answered, 'correct': correct, 'accuracy': accuracy}


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
    """Akurasi siswa per tingkat dari SELURUH riwayat jawaban latihannya.

    Sumbernya satu hal yang benar-benar tercatat: jawaban latihan TERAKHIR per
    soal bank.

    Tiap soal diberi tingkat terukur (leave-one-out) bila cukup data, selain
    itu deklarasi guru. Cakupannya seluruh materi, bukan hanya bagian ini -
    sama seperti recommendation._student_weak_difficulty yang memakai
    akurasi per tingkat lintas materi untuk memilih sasaran belajar. Tingkat
    kesulitan tidak terikat topik, jadi "siswa lemah di soal sulit" berlaku
    umum; yang dibatasi tetap soalnya (hanya soal bagian ini yang disajikan).

    Sumber kedua yang dulu ada di sini, "jawaban soal interaktif", DIHAPUS
    bersama kanalnya (tidak pernah dijawab siapa pun) dan parameter
    `include_interactive` ikut hilang: sekarang tidak ada lagi dua definisi
    "akurasi per tingkat" yang perlu dijaga agar sama.

    `bank_effective_current` dipakai agar jawaban latihan pada bagian ini
    memakai label yang sama dengan yang dipakai menyusun sesi (tidak dihitung
    dua kali dengan hasil yang bisa berbeda).

    Mengembalikan (per_level, basis_by_level, notes_by_level, counts).
    """
    from src.services.learning_analytics_service import normalize_difficulty

    per_level, basis_by_level, notes_by_level = {}, {}, {}
    counts = {'practice': 0}
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

    # Blok "soal interaktif" (jawaban terakhir per slot) DIHAPUS di sini:
    # kanalnya tidak pernah dijawab siapa pun, jadi `counts['interactive']`
    # selalu 0 dan tidak ada satu angka pun yang hilang.

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


def focus_for_student_section(student, approved):
    """Label miskonsepsi yang paling sering salah untuk (siswa, bagian), atau None.

    Dihitung dari jawaban TERAKHIR per soal, konsisten dengan `latest_attempts`:
    mengulang satu soal sampai benar tetap terhitung satu soal terjawab, jadi
    fokus tidak bisa ditimbun lewat percobaan berulang.

    Hanya label dengan minimal ``FOCUS_MIN_SAMPLE`` jawaban yang dipertimbangkan,
    dan hanya bila salah > benar. Label kosong diabaikan - tidak mengarang.
    Seri dipecah ke label yang paling baru dijawab (masalah yang masih hangat
    didahulukan).

    Label dipakai server untuk mengurutkan sesi dan TIDAK pernah dikirim ke
    klien sebelum soal dijawab (bisa membocorkan konsep benar). Agregat angka
    saja yang boleh keluar.
    """
    if not approved:
        return None
    rows = PracticeAnswer.query.filter_by(
        student_id=student.id, section_id=approved[0].section_id
    ).order_by(PracticeAnswer.answered_at.asc(), PracticeAnswer.id.asc()).all()
    if not rows:
        return None

    latest = {}
    last_at = {}
    for r in rows:
        latest[int(r.bank_question_id)] = bool(r.is_correct)
        last_at[int(r.bank_question_id)] = r.answered_at

    by_id = {int(bq.id): bq for bq in approved}
    agg = {}
    for bq_id, ok in latest.items():
        bq = by_id.get(bq_id)
        label = ((bq.misconception or '').strip()[:cfg.FOCUS_LABEL_MAXLEN]
                 if bq else '')
        if not label:
            continue
        a = agg.setdefault(label, {
            'label': label, 'wrong': 0, 'correct': 0, 'total': 0, 'last_at': None})
        a['total'] += 1
        a['correct' if ok else 'wrong'] += 1
        a['last_at'] = last_at.get(bq_id)

    candidates = [a for a in agg.values()
                  if a['total'] >= cfg.FOCUS_MIN_SAMPLE
                  and a['wrong'] > a['correct']]
    if not candidates:
        return None
    candidates.sort(key=lambda a: (-(a['wrong'] - a['correct']),
                                   -((a['last_at'] or datetime.min).timestamp())))
    best = candidates[0]
    return {'label': best['label'], 'wrong': best['wrong'],
            'correct': best['correct'], 'total': best['total']}


def _rotation_key(bq, history, focus_label=None):
    """Kunci rotasi: soal yang BELUM dijawab dulu, lalu yang paling lama.

    `history` = {bank_question_id: waktu jawaban latihan terakhir}. Soal yang
    tidak ada di sana selalu di depan (diurutkan fokus lebih dulu lalu id).
    Sesama soal yang sudah dijawab diurutkan dari yang paling lama, sehingga
    sesi berikutnya memakai soal yang lebih jarang dilihat. `focus_label` hanya
    memecah seri - tidak pernah menimpa rotasi.
    """
    at = history.get(int(bq.id)) if history else None
    focus_rank = (
        0 if (focus_label
              and (bq.misconception or '').strip()[:cfg.FOCUS_LABEL_MAXLEN] == focus_label)
        else 1
    )
    return (1 if at is not None else 0, at or datetime.min, focus_rank, int(bq.id))


def _practice_history(section_id, student_id):
    """bank_question_id -> waktu jawaban LATIHAN terakhir (mode='practice').

    Hanya jalur latihan yang dihitung: jawaban asesmen diagnostik tidak boleh
    dianggap "sudah dilatih" (dua pool itu memang dipisah). Dipakai untuk
    rotasi sesi supaya seluruh bank terpakai lintas sesi.
    """
    rows = PracticeAnswer.query.filter_by(
        student_id=student_id, section_id=section_id, mode='practice'
    ).order_by(PracticeAnswer.answered_at.asc(), PracticeAnswer.id.asc()).all()
    out = {}
    for r in rows:
        out[int(r.bank_question_id)] = r.answered_at
    return out


def section_practice_counts(section_id, student_id):
    """(total, seen) soal latihan APPROVED satu bagian untuk satu siswa.

    `total` = soal latihan yang disetujui guru; `seen` = berapa yang sudah
    pernah dijawab (mode='practice'). Dipakai UI untuk menawarkan "sesi
    berikutnya" hanya bila memang masih ada soal yang belum dilatih - tidak ada
    sisa yang dikarang.
    """
    total = len(approved_for_section(section_id))
    seen = len(_practice_history(section_id, student_id))
    return total, seen


def _order_questions(approved, effective, target, focus_label=None,
                     history=None, size=None):
    """Urutkan soal sesuai komposisi 60/30/10, dengan jendela + rotasi.

    Dua perilaku, sengaja dipisah:

    - Tanpa `size` ATAU bank <= jendela: seluruh soal tersaji dalam urutan
      60/30/10 (fokus lebih dulu di dalam tiap tingkat, lalu id stabil). Ini
      perilaku lama, jadi regresi aman.
    - Bank lebih besar dari jendela DAN ada `history`: kuota 60/30/10 dihitung
      dari ukuran jendela, dan tiap tingkat dirotasi - soal yang belum pernah
      dijawab didahulukan, lalu yang paling lama dijawab. Sifat adaptif tetap,
      tetapi seluruh bank terpakai lintas sesi.

    Hasil selalu memuat SELURUH soal (jendela dulu, sisa di belakang), supaya
    pemanggil bisa memotong `[:size]` untuk sesi dan tetap tahu totalnya.
    """
    total = len(approved)
    window = min(total, size) if size else total
    rotating = bool(history) and total > window

    if not target:
        if rotating:
            return sorted(
                approved, key=lambda bq: _rotation_key(bq, history, focus_label))
        return list(approved)

    queues = {lvl: [] for lvl in cfg.SESSION_LEVEL_ORDER}
    for bq in approved:
        level = (effective.get(int(bq.id)) or {}).get('label')
        if level in queues:
            queues[level].append(bq)

    for lvl in cfg.SESSION_LEVEL_ORDER:
        if rotating:
            queues[lvl].sort(key=lambda bq: _rotation_key(bq, history, focus_label))
        elif focus_label:
            queues[lvl].sort(key=lambda bq: (
                # 0 = cocok fokus -> didahulukan; 1 = bukan fokus. Hanya
                # menggeser posisi, tidak menambah/membuang soal.
                0 if (bq.misconception or '').strip()[:cfg.FOCUS_LABEL_MAXLEN] == focus_label else 1,
                bq.id,
            ))

    n_target = round(window * cfg.SESSION_MIX_TARGET)
    n_below = round(window * cfg.SESSION_MIX_BELOW)
    n_above = max(window - n_target - n_below, 0)
    below = _LEVEL_BELOW[target]
    above = _LEVEL_ABOVE[target]

    chosen = []
    chosen += queues[target][:n_target]
    if below:
        chosen += queues[below][:n_below]
    if above:
        chosen += queues[above][:n_above]

    chosen_ids = {bq.id for bq in chosen}
    # Sisa semua soal (termasuk sisa kuota tiap tingkat) ikut di belakang.
    # Soal tanpa tingkat ikut di sini - bukan ditebak tingkatnya, cuma tidak
    # ditempatkan di komposisi. Saat berotasi, sisa pun diurut rotasi supaya
    # jendela berikutnya tetap menghitung soal yang belum dijawab lebih dulu.
    rest = [bq for bq in approved if bq.id not in chosen_ids]
    if rotating:
        rest.sort(key=lambda bq: _rotation_key(bq, history, focus_label))
    chosen += rest
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

    # --- fokus miskonsepsi (Tahap 2): urutan DI DALAM tiap tingkat ---
    focus = focus_for_student_section(student, approved)
    focus_label = focus['label'] if focus else None

    # --- rotasi sesi: riwayat jawaban LATIHAN bagian ini (bukan diagnostik) ---
    history = _practice_history(section_id, student.id)

    # --- komposisi 60/30/10 di dalam jendela sesi ---
    ordered = _order_questions(approved, effective, target, focus_label,
                               history=history, size=SESSION_SIZE)
    total = len(approved)
    window_served = min(total, SESSION_SIZE)
    mix = {'target': 0, 'below': 0, 'above': 0}
    if target:
        mix = {
            'target': round(window_served * cfg.SESSION_MIX_TARGET),
            'below': round(window_served * cfg.SESSION_MIX_BELOW),
            'above': max(window_served - round(window_served * cfg.SESSION_MIX_TARGET)
                         - round(window_served * cfg.SESSION_MIX_BELOW), 0),
        }

    # --- basis: bagaimana sasaran itu terbentuk ---
    answered_total = counts['practice']
    answered_txt = f"{answered_total} jawaban latihanmu di semua materi"
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

    # --- tujuan & status keluar bagian (Fase 3 lanjutan) ---
    # Tuntas hanya diklaim bila buktinya cukup (>= PRACTICE_MIN_SAMPLE soal)
    # DAN akurasinya >= PRACTICE_PASS_SCORE. Sebelum itu statusnya "sedang
    # berlatih" - kita tidak pernah bilang tuntas tanpa dasar.
    progress = section_progress(student.id, material_id, section_id)
    if progress['answered'] == 0:
        exit_status = 'not_started'
    elif progress['answered'] < cfg.PRACTICE_MIN_SAMPLE:
        exit_status = 'in_progress'
    elif (progress['accuracy'] or 0) >= cfg.PRACTICE_PASS_SCORE:
        exit_status = 'mastered'
    else:
        exit_status = 'needs_reinforcement'

    # "Naik tingkat saat tuntas": hanya bila bagian sudah tuntas DAN bagian ini
    # memang masih menyimpan soal di tingkat atasnya. Kalau tidak ada, jangan
    # menjanjikan tantangan yang tidak eksis.
    next_level = None
    if exit_status == 'mastered' and target:
        candidate = _LEVEL_ABOVE.get(target)
        if candidate and any(
                (effective.get(int(bq.id)) or {}).get('label') == candidate
                for bq in approved):
            next_level = candidate

    if exit_status == 'mastered':
        exit_message = f"Bagian ini sudah tuntas (akurasi {progress['accuracy']}%). "
        exit_message += (f"Tantang soal {_level_label(next_level)} berikutnya."
                         if next_level else
                         "Ulangi besok agar pemahamanmu bertahan.")
    elif exit_status == 'in_progress':
        exit_message = (f"Baru {progress['answered']} dari minimal "
                        f"{cfg.PRACTICE_MIN_SAMPLE} soal terjawab di bagian ini.")
    elif exit_status == 'needs_reinforcement':
        exit_message = (f"Akurasi bagian ini {progress['accuracy']}%, masih di bawah "
                        f"{cfg.PRACTICE_PASS_SCORE}%. Latih lagi.")
    else:
        exit_message = "Belum ada jawaban di bagian ini. Mulai dari soal pertama."

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
        'mix': mix,
        'total': total,
        'served': window_served,
        'session_size': window_served,
        # Rotasi sesi: berapa soal latihan bagian ini yang sudah pernah dijawab
        # (`seen_in_section`) dan apakah masih ada soal yang belum pernah
        # muncul. Dipakai UI untuk menawarkan "Lanjut sesi berikutnya" tanpa
        # mengarang sisa yang tidak ada.
        'seen_in_section': len(history),
        'has_more': len(history) < total,
        # Fokus miskonsepsi (Tahap 2): hanya agregat ANGKA yang keluar, teks
        # label tidak pernah dikirim sebelum dijawab. Urutan sudah memakai
        # label ini secara diam-diam di server.
        'focus_available': focus is not None,
        'focus_wrong': focus['wrong'] if focus else 0,
        'focus_total': focus['total'] if focus else 0,
        'focus_text': ('Sesi ini menekankan soal yang paling sering kamu lewatkan.'
                       if focus else None),
        'note': ('Urutan sesi: 60% sasaran, 30% satu tingkat di bawah, 10% di atas. '
                 'Hanya soal yang disetujui guru; soal baru tidak pernah dibuat.'),
        # --- aturan keluar sesi (Fase 3 lanjutan) ---
        # Status bagian ini + kalimat langkah berikutnya. Angka apa adanya:
        # `accuracy` None berarti belum ada jawaban.
        'exit_status': exit_status,
        'exit_message': exit_message,
        'progress': progress,
        'pass_score': cfg.PRACTICE_PASS_SCORE,
        'pass_min_sample': cfg.PRACTICE_MIN_SAMPLE,
        'next_level': next_level,
        'next_level_label': _level_label(next_level),
    }
    return entries, session