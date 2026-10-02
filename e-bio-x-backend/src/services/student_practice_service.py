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
"""
from datetime import datetime

from src.config.database import db
from src.models.question_bank import QuestionBank
from src.models.practice_answer import PracticeAnswer
from src.services import storage_service

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


def question_for_student(bq):
    """Serialize a practice question WITHOUT the answer key.

    `explanation` and `misconception` are held back as well: both are teaching
    material for the answer, not part of the question.
    """
    return {
        'id': bq.id,
        'question_text': bq.question_text,
        'question_type': bq.question_type,
        'difficulty': bq.difficulty,
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