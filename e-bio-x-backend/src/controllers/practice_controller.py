"""Teacher endpoints for practice questions per material section (Fase 3).

Three jobs, in the order the workflow runs:

1. ``GET  /api/teacher/practice/sections`` - sections the teacher owns with raw
   draft counts, so the UI can say "bagian ini belum ada soal latihan" instead
   of guessing.
2. ``POST /api/teacher/practice/sections/<id>/drafts`` - ask the AI for drafts
   for ONE section the teacher picked. Drafts are stored as DRAFT and the
   section tag comes from the section record, never from the model output.
3. ``POST /api/teacher/practice/drafts/<id>/approve|reject`` - the teacher's
   decision. Only APPROVED questions can be used as practice later.
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime

from src.config.database import db
from src.models.material_section import MaterialSection
from src.models.question_bank import QuestionBank
from src.models.question_bank_option import QuestionBankOption
from src.services import practice_bank_service as practice
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