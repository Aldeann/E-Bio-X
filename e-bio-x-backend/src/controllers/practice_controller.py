"""Practice questions per material section (Fase 3).

Teacher side, in the order the workflow runs:

1. ``GET  /api/teacher/practice/sections`` - sections the teacher owns with raw
   draft counts, so the UI can say "bagian ini belum ada soal latihan" instead
   of guessing.
2. ``POST /api/teacher/practice/sections/<id>/drafts`` - ask the AI for drafts
   for ONE section the teacher picked. Drafts are stored as DRAFT and the
   section tag comes from the section record, never from the model output.
3. ``POST /api/teacher/practice/drafts/<id>/approve|reject`` - the teacher's
   decision. Only APPROVED questions can be used as practice later.

Student side (3d):

4. ``GET  /api/student/practice/<material_id>/sections`` - which sections have
   practice questions, and how many this student already answered.
5. ``GET  /api/student/practice/<material_id>/sections/<section_id>`` - the
   APPROVED questions of one section, without the answer key.
6. ``POST /api/student/practice/<material_id>/sections/<section_id>/answer`` -
   grade one answer and record the attempt.
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime

from src.config.database import db
from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.question_bank import QuestionBank
from src.models.question_bank_option import QuestionBankOption
from src.services import practice_bank_service as practice
from src.services import student_practice_service as spractice
from src.services.learning_analytics_service import student_can_access_material
from src.controllers.quiz_controller import (
    _cur_user,
    _is_teacher,
    _teacher_owns_material,
    _validate_question_payload,
    _serialize_bank,
    VALID_DIFFICULTIES,
)


def _owned_bank(bank_id, user):
    bq = QuestionBank.query.get(bank_id)
    if not bq:
        return None, (jsonify({'error': 'Soal bank tidak ditemukan'}), 404)
    if bq.teacher_id != user.id and user.role != 'admin':
        return None, (jsonify({'error': 'Anda tidak berhak menangani soal bank ini'}), 403)
    return bq, None


@jwt_required()
def get_practice_sections():
    """Sections of the teacher's materials plus how many practice questions exist.

    `ai_available` is reported so the UI can explain up front that AI drafts are
    unavailable instead of failing on click.
    """
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    material_id = request.args.get('material_id')
    if material_id:
        try:
            material_id = int(material_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'material_id tidak valid'}), 400

    available = practice.ai_available()
    return jsonify({
        'sections': practice.section_rows(user, material_id=material_id),
        'ai_available': available,
        'ai_model': practice.model_name() if available else None,
        'ai_unavailable_reason': None if available else (
            'AI belum dikonfigurasi (AI_API_KEY). Soal latihan tetap bisa ditulis '
            'sendiri lalu ditautkan ke bagian.'
        ),
    }), 200


@jwt_required()
def generate_section_drafts(section_id):
    """Create AI drafts for one section the teacher owns."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    section = MaterialSection.query.get(section_id)
    if not section:
        return jsonify({'error': 'Bagian materi tidak ditemukan'}), 404
    material = section.material
    if not material:
        return jsonify({'error': 'Bagian ini tidak tertaut ke materi'}), 400
    if not _teacher_owns_material(user, material):
        return jsonify({'error': 'Anda tidak berhak menangani bagian ini'}), 403

    data = request.get_json(silent=True) or {}
    raw_count = data.get('count', practice.DEFAULT_COUNT)
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return jsonify({'error': 'Jumlah soal tidak valid'}), 400
    if count < 1 or count > practice.MAX_COUNT:
        return jsonify({'error': f'Jumlah soal harus antara 1 dan {practice.MAX_COUNT}'}), 400

    difficulty = (data.get('difficulty') or 'medium').strip()
    if difficulty not in VALID_DIFFICULTIES:
        return jsonify({'error': 'Tingkat kesulitan tidak valid'}), 400

    if not practice.ai_available():
        return jsonify({
            'error': 'AI belum dikonfigurasi (AI_API_KEY). Set di server lalu coba lagi, '
                     'atau tulis soal sendiri dan tautkan ke bagian ini.',
            'ai_available': False,
        }), 503

    # A section with no text at all has nothing to ground a question on. Saying so
    # beats spending an API call on invented content.
    if not practice.section_body(section).strip():
        return jsonify({
            'error': f'Bagian "{section.title}" belum punya teks, jadi tidak ada dasar '
                     'untuk membuat soal. Tambahkan isi bagian dulu.',
            'section_id': section.id,
        }), 400

    try:
        items, dropped = practice.generate_drafts(section, material, count, difficulty)
    except practice.DraftUnavailable as exc:
        return jsonify({'error': str(exc), 'ai_available': False}), 503
    except practice.DraftFailed as exc:
        return jsonify({'error': str(exc)}), 502

    created = []
    skipped = dropped
    for item in items:
        payload = {
            'question_text': item['question_text'],
            'question_type': 'multiple_choice',
            'difficulty': difficulty,
            'points': 10,
            'explanation': item.get('explanation'),
            'options': item['options'],
        }
        validated, err = _validate_question_payload(payload, bank=True)
        if err:
            # AI returned something that cannot be a question (e.g. two correct
            # options). Report the count instead of storing it.
            skipped += 1
            continue

        bq = QuestionBank(
            teacher_id=user.id,
            question_text=validated['question_text'],
            question_type=validated['question_type'],
            # Section and topic come from the section the teacher chose. The
            # model's own idea of a topic is ignored on purpose.
            section_id=section.id,
            topic=section.title,
            difficulty=difficulty,
            explanation=validated['explanation'],
            points=validated['points'],
            misconception=item.get('misconception'),
            source='ai',
            status='DRAFT',
            generated_by='ai',
            model_name=practice.model_name(),
            prompt_version=practice.PROMPT_VERSION,
            created_at=datetime.utcnow(),
        )
        db.session.add(bq)
        db.session.flush()
        for idx, opt in enumerate(item['options']):
            db.session.add(QuestionBankOption(
                bank_question_id=bq.id,
                option_text=(opt.get('option_text') or '').strip(),
                is_correct=bool(opt.get('is_correct')),
                order_index=idx,
                feedback=(opt.get('feedback') or '').strip() or None,
            ))
        created.append(bq)

    db.session.commit()

    message = f'{len(created)} draf dibuat untuk bagian "{section.title}"'
    if skipped:
        message += f'; {skipped} hasil AI tidak disimpan karena tidak valid'
    return jsonify({
        'message': message,
        'created': [_serialize_bank(b) for b in created],
        'created_count': len(created),
        'skipped_count': skipped,
        'section_id': section.id,
    }), 201


@jwt_required()
def get_draft_queue():
    """Questions waiting for the teacher's review."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    status = (request.args.get('status') or 'DRAFT').strip().upper()
    query = QuestionBank.query
    if user.role != 'admin':
        query = query.filter_by(teacher_id=user.id)
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(QuestionBank.created_at.desc()).all()

    return jsonify({
        'data': [_serialize_bank(b) for b in items],
        'status': status or None,
    }), 200


@jwt_required()
def approve_bank_draft(bank_id):
    """Teacher approval. This is the only path from DRAFT to APPROVED."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    bq, err = _owned_bank(bank_id, user)
    if err:
        return err

    if not any(bool(o.is_correct) for o in bq.options):
        return jsonify({'error': 'Soal ini tidak punya jawaban benar, tidak bisa disetujui'}), 400

    bq.status = 'APPROVED'
    bq.reviewed_by = user.id
    bq.reviewed_at = datetime.utcnow()
    bq.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'message': 'Soal disetujui dan siap dipakai sebagai latihan',
        'question': _serialize_bank(bq),
    }), 200


@jwt_required()
def reject_bank_draft(bank_id):
    """Teacher rejection. The row is kept so the decision stays auditable."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    bq, err = _owned_bank(bank_id, user)
    if err:
        return err

    bq.status = 'REJECTED'
    bq.reviewed_by = user.id
    bq.reviewed_at = datetime.utcnow()
    bq.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'message': 'Draf ditolak dan tidak akan dipakai sebagai latihan',
        'question': _serialize_bank(bq),
    }), 200


# ============================================================
# STUDENT SIDE (Fase 3d)
# ============================================================
#
# Gate yang dipakai ketiganya sama: siswa, materi sudah dipublikasikan, dan
# siswa berhak atas materi itu (kelas yang diikuti). Bagian juga harus benar
# milik materi tersebut, jadi tidak ada jalan untuk menjangkau bagian materi
# lain hanya karena tahu id-nya.

def _int_or_none(value):
    """Id dari kiriman yang mungkin rusak. None berarti "tidak ada id",
    bukan exception 500 dari dalam SQLAlchemy."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _practice_guard(material_id, section_id=None):
    user = _cur_user()
    if not user:
        return None, None, (jsonify({'error': 'User not found'}), 404)
    if user.role != 'student':
        return None, None, (jsonify({'error': 'Endpoint ini khusus siswa'}), 403)

    material = Material.query.get(_int_or_none(material_id))
    if not material:
        return None, None, (jsonify({'error': 'Materi tidak ditemukan'}), 404)
    if material.status != 'published':
        return None, None, (jsonify({'error': 'Materi belum dipublikasikan'}), 403)
    if not student_can_access_material(user, material):
        return None, None, (
            jsonify({'error': 'Materi hanya untuk kelas yang diikuti'}), 403)

    section = None
    if section_id is not None:
        section = MaterialSection.query.filter_by(
            id=_int_or_none(section_id), material_id=material.id).first()
        if not section:
            return None, None, (
                jsonify({'error': 'Bagian tidak ditemukan pada materi ini'}), 404)
    return user, (material, section), None


@jwt_required()
def get_student_practice_sections(material_id):
    """Bagian mana dari materi ini yang punya soal latihan, dan progress siswa."""
    user, ctx, err = _practice_guard(material_id)
    if err:
        return err
    material, _ = ctx

    sections = MaterialSection.query.filter_by(
        material_id=material.id).order_by(MaterialSection.position).all()
    approved = spractice.approved_count_map([s.id for s in sections])
    stats = spractice.practice_stats(user.id, material.id)

    rows = []
    for sec in sections:
        st = stats.get(sec.id, {'answered': 0, 'correct': 0, 'attempts': 0})
        total = approved.get(sec.id, 0)
        rows.append({
            'section_id': sec.id,
            'title': sec.title,
            'position': sec.position,
            # 0 = tidak ada soal yang disetujui guru. UI_DISABLE tombolnya
            # dan menjelaskan kenapa, bukan membuat soal lain.
            'practice_total': total,
            'practice_answered': st['answered'],
            'practice_correct': st['correct'],
            'practice_attempts': st['attempts'],
            'available': total > 0,
        })

    return jsonify({
        'material_id': material.id,
        'material_title': material.title,
        'sections': rows,
        'sections_with_practice': sum(1 for r in rows if r['available']),
        'sections_total': len(rows),
        # Reminder supaya angka latihan tidak dibaca sebagai nilai Finally.
        'note': 'Hanya soal yang sudah disetujui guru yang dihitung sebagai latihan.',
    }), 200


@jwt_required()
def get_student_practice_questions(material_id, section_id):
    """Soal latihan satu bagian. Kunci jawaban TIDAK ikut di respons ini."""
    user, ctx, err = _practice_guard(material_id, section_id)
    if err:
        return err
    material, section = ctx

    items = spractice.approved_for_section(section.id)
    served = items[:spractice.MAX_SERVED]
    stats = spractice.practice_stats(user.id, material.id).get(
        section.id, {'answered': 0, 'correct': 0, 'attempts': 0})

    message = None
    if not items:
        message = (f'Belum ada soal latihan yang disetujui guru untuk bagian '
                   f'"{section.title}".')
    elif len(items) > len(served):
        message = (f'Bagian ini punya {len(items)} soal latihan; '
                   f'{len(served)} yang ditampilkan sekaligus.')

    return jsonify({
        'material_id': material.id,
        'section_id': section.id,
        'section_title': section.title,
        'questions': [spractice.question_for_student(bq) for bq in served],
        'total_available': len(items),
        'total_served': len(served),
        'practice_answered': stats['answered'],
        'practice_correct': stats['correct'],
        'message': message,
    }), 200


@jwt_required()
def submit_student_practice_answer(material_id, section_id):
    """Nilai satu jawaban latihan dan catat-legal sebagai bukti belajar.

    Server memuat ulang soalnya dari bank dan mencocokkan `selected_option`
    dengan `order_index` yang tersimpan, jadi kiriman klien tidak bisa memilih
    kunci jawaban secara langsung.
    """
    user, ctx, err = _practice_guard(material_id, section_id)
    if err:
        return err
    material, section = ctx

    data = request.get_json(silent=True) or {}
    raw = data.get('selected_option', data.get('selected_index'))
    if raw is None:
        return jsonify({'error': 'Opsi jawaban belum dikirim'}), 400
    try:
        selected = int(raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'Opsi jawaban tidak valid'}), 400

    bq = QuestionBank.query.get(_int_or_none(data.get('bank_question_id')))
    if not bq:
        return jsonify({'error': 'Soal latihan tidak ditemukan'}), 404
    # Diperiksa ulang di sini, bukan hanya saat pemuatan: status bisa berubah
    # di antara keduanya dan soalnya bisa saja bukan milik bagian ini.
    if bq.status != 'APPROVED':
        return jsonify({'error': 'Soal ini belum disetujui guru, tidak bisa dikerjakan'}), 403
    if bq.section_id != section.id:
        return jsonify({'error': 'Soal ini bukan milik bagian yang diminta'}), 400

    graded = spractice.grade(bq, selected)
    if graded is None:
        return jsonify({'error': 'Opsi jawaban tidak ditemukan pada soal ini'}), 400

    row = spractice.record(user.id, material.id, section.id, bq, graded)
    db.session.commit()

    stats = spractice.practice_stats(user.id, material.id).get(
        section.id, {'answered': 0, 'correct': 0, 'attempts': 0})

    payload = dict(graded)
    payload.update({
        'section_id': section.id,
        'section_title': section.title,
        'attempt_no': row.attempt_no,
        'practice_answered': stats['answered'],
        'practice_correct': stats['correct'],
    })
    return jsonify(payload), 200