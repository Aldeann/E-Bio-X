"""AI Quiz Explanation Engine - API controller (Prompt 12).

Answer key is ALWAYS the teacher's (Option.is_correct). AI only produces
explanations. Students may only GET approved explanations.
"""
import traceback
from datetime import datetime

from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.config.database import db
from src.models.user import User
from src.models.question import Question
from src.models.quiz import Quiz
from src.models.question_bank import QuestionBank
from src.models.submission import Submission
from src.models.answer import Answer
from src.models.material import Material
from src.models.quiz_explanation import QuizExplanation
from src.services.ai_explanation_service import (
    AIExplanationService,
    PROMPT_VERSION,
    option_letters,
    correct_letter as _correct_letter_fn,
    build_material_context,
    validate_explanation,
)
from src.services.learning_analytics_service import log_activity

BATCH_LIMIT = 50
STUDENT_VIEWABLE = ('APPROVED', 'TEACHER_APPROVED')


def _cur_user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _is_teacher(user):
    return user and user.role in ('teacher', 'admin')


def _can_manage_quiz(quiz, user):
    if not user:
        return False
    if user.role == 'admin':
        return True
    if quiz.created_by:
        return quiz.created_by == user.id
    return quiz.course_id is not None and quiz.course and quiz.course.teacher_id == user.id


def _try_log(student_id, material_id, event_type, data=None):
    if not student_id or not material_id:
        return None
    return log_activity(student_id, material_id, event_type, data=data or {})


# ------------------------------------------------------------------
# Question source resolution
# ------------------------------------------------------------------
def _question_options(question):
    opts = sorted(question.options, key=lambda x: x.order_index)
    return [
        (option_letters(len(opts))[i], o.option_text, bool(o.is_correct))
        for i, o in enumerate(opts)
    ]


def _bank_options(bq):
    opts = sorted(bq.options, key=lambda x: x.order_index)
    return [
        (option_letters(len(opts))[i], o.option_text, bool(o.is_correct))
        for i, o in enumerate(opts)
    ]


def _material_version(material):
    return material.updated_at.isoformat() if material and material.updated_at else None


def _answer_letter(ans, question):
    if not ans or not ans.option:
        return ''
    idx = ans.option.order_index
    letters = option_letters(len(question.options)) if question else ['A']
    return letters[idx] if 0 <= idx < len(letters) else ('A' if letters else '')


def _resolve_material_for_question(question):
    quiz = Quiz.query.get(question.quiz_id) if question.quiz_id else None
    material = None
    if quiz and quiz.material_id:
        material = Material.query.get(quiz.material_id)
    return quiz, material


def _get_or_create_global(question_id=None, bank_question_id=None):
    q = None
    if question_id:
        q = QuizExplanation.query.filter_by(question_id=question_id, student_id=None).first()
    if not q and bank_question_id:
        q = QuizExplanation.query.filter_by(bank_question_id=bank_question_id, student_id=None).first()
    if not q:
        q = QuizExplanation(
            question_id=question_id,
            bank_question_id=bank_question_id,
            student_id=None,
            status='MISSING',
            explanation_version=1,
            version_history=[],
            feedback_summary={'helpful': 0, 'not_helpful': 0, 'reasons': {}},
        )
        db.session.add(q)
    return q


def _reuse_from_bank(question, existing):
    """If a quiz question came from the bank and the bank has an approved
    explanation, reuse it for this question (reuse rule)."""
    if existing and existing.status != 'MISSING':
        return existing
    if not question.bank_question_id:
        return existing
    bank_exp = QuizExplanation.query.filter_by(
        bank_question_id=question.bank_question_id, student_id=None).first()
    if not bank_exp or bank_exp.status not in ('APPROVED', 'TEACHER_APPROVED'):
        return existing
    if existing is None:
        existing = _get_or_create_global(question_id=question.id)
    existing.summary = bank_exp.summary
    existing.correct_answer_explanation = bank_exp.correct_answer_explanation
    existing.student_answer_analysis = bank_exp.student_answer_analysis
    existing.option_explanations = bank_exp.option_explanations
    existing.key_concept = bank_exp.key_concept
    existing.misconception = bank_exp.misconception
    existing.recommended_material = bank_exp.recommended_material
    existing.recommended_material_id = bank_exp.recommended_material_id
    existing.source_material_id = bank_exp.source_material_id
    existing.material_version = bank_exp.material_version
    existing.status = 'APPROVED'
    existing.generated_by = bank_exp.generated_by
    existing.model_name = bank_exp.model_name
    existing.prompt_version = bank_exp.prompt_version
    existing.edited_by_teacher = bank_exp.edited_by_teacher
    existing.approved_by = bank_exp.approved_by
    existing.approved_at = bank_exp.approved_at
    existing.updated_at = datetime.utcnow()
    db.session.add(existing)
    return existing


# ------------------------------------------------------------------
# Generation
# ------------------------------------------------------------------
def _build_payload(question_text, qtype, difficulty, topic, options, student_answer, material, material_title):
    correct = _correct_letter_fn(options)
    return {
        'question_text': question_text,
        'question_type': qtype,
        'difficulty': difficulty,
        'topic': topic,
        'options': options,
        'correct_answer': correct,
        'student_answer': student_answer,
        'material_title': material_title,
        'material_context': build_material_context(material, question_text),
    }


def _generate_into(exp, payload, source_material, actor_id=None):
    service = AIExplanationService()
    data, generated_by, model_name = service.generate(payload)
    ok, err = validate_explanation(data, payload['options'], payload['correct_answer'])
    if not ok:
        exp.status = 'FAILED'
        exp.generated_by = generated_by
        exp.model_name = model_name
        exp.prompt_version = PROMPT_VERSION
        exp.updated_at = datetime.utcnow()
        db.session.add(exp)
        db.session.commit()
        _try_log(actor_id, source_material.id if source_material else None, 'AI_EXPLANATION_VALIDATION_FAILED',
                 {'explanation_id': exp.id, 'reason': err})
        return False, err

    history = exp.version_history or []
    if exp.summary:
        history.append(exp.snapshot())
    exp.version_history = history[-20:]
    exp.explanation_version = (exp.explanation_version or 1) + 1 if exp.summary else 1

    exp.summary = data['summary']
    exp.correct_answer_explanation = data['correct_answer_explanation']
    exp.student_answer_analysis = data.get('student_answer_analysis') or ''
    exp.option_explanations = data['option_explanations']
    exp.key_concept = data.get('key_concept') or ''
    exp.misconception = data.get('misconception') or ''
    exp.recommended_material = data.get('recommended_material') or ''
    exp.recommended_material_id = source_material.id if source_material else None
    exp.source_material_id = source_material.id if source_material else None
    exp.material_version = _material_version(source_material)
    exp.generated_by = generated_by
    exp.model_name = model_name
    exp.prompt_version = PROMPT_VERSION
    exp.status = 'AI_GENERATED'
    exp.updated_at = datetime.utcnow()
    db.session.add(exp)
    db.session.commit()
    _try_log(actor_id, source_material.id if source_material else None, 'AI_EXPLANATION_GENERATED',
             {'explanation_id': exp.id, 'generated_by': generated_by})
    return True, None


# ------------------------------------------------------------------
# Serialization
# ------------------------------------------------------------------
def _serialize(exp, for_student=False, personal=None):
    data = {
        'id': exp.id,
        'question_id': exp.question_id,
        'bank_question_id': exp.bank_question_id,
        'status': exp.status,
        'generated_by': exp.generated_by,
        'model_name': exp.model_name,
        'prompt_version': exp.prompt_version,
        'explanation_version': exp.explanation_version,
        'edited_by_teacher': exp.edited_by_teacher,
        'approved_at': exp.approved_at.isoformat() if exp.approved_at else None,
        'summary': exp.summary,
        'correct_answer_explanation': exp.correct_answer_explanation,
        'student_answer_analysis': exp.student_answer_analysis,
        'option_explanations': exp.option_explanations,
        'key_concept': exp.key_concept,
        'misconception': exp.misconception,
        'recommended_material': exp.recommended_material,
        'recommended_material_id': exp.recommended_material_id,
        'source_material_id': exp.source_material_id,
        'feedback_summary': exp.feedback_summary,
        'created_at': exp.created_at.isoformat() if exp.created_at else None,
        'updated_at': exp.updated_at.isoformat() if exp.updated_at else None,
    }
    if for_student and personal:
        data['personal'] = personal
    return data


def _personal_analysis(exp, student_answer_letter, is_correct):
    """Deterministic per-student analysis built from the global explanation
    (1 global + personal analysis; no per-student AI call)."""
    oes = exp.option_explanations or []
    chosen = next((o for o in oes if str(o.get('option', '')).upper() == (student_answer_letter or '').upper()), None)
    correct_letter = None
    for o in oes:
        if o.get('is_correct'):
            correct_letter = o.get('option')
            break
    if is_correct:
        analysis = 'Jawaban Anda benar. ' + (exp.correct_answer_explanation or '')
    else:
        bits = [f'Jawaban Anda ({student_answer_letter}) kurang tepat.']
        if chosen and chosen.get('explanation'):
            bits.append(f'{chosen["explanation"]}')
        if correct_letter:
            bits.append(f'Kunci jawaban yang benar adalah {correct_letter}.')
        if exp.correct_answer_explanation:
            bits.append(exp.correct_answer_explanation)
        analysis = ' '.join(bits)
    return {
        'student_answer': student_answer_letter,
        'is_correct': bool(is_correct),
        'correct_answer': correct_letter,
        'analysis': analysis,
        'misconception': exp.misconception if not is_correct else '',
    }


def _mark_stale_if_needed(exp):
    if exp.source_material_id:
        mat = Material.query.get(exp.source_material_id)
        cur = _material_version(mat)
        if cur and exp.material_version and exp.material_version != cur:
            if exp.status in ('APPROVED', 'TEACHER_APPROVED'):
                exp.status = 'STALE'
                exp.updated_at = datetime.utcnow()
                db.session.add(exp)
                db.session.commit()


# ------------------------------------------------------------------
# GENERATE (teacher)
# ------------------------------------------------------------------
@jwt_required()
def generate_question_explanation(question_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat membuat pembahasan'}), 403
    question = Question.query.get(question_id)
    if not question:
        return jsonify({'error': 'Soal tidak ditemukan'}), 404
    quiz = Quiz.query.get(question.quiz_id) if question.quiz_id else None
    if quiz and not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Soal bukan milik Anda'}), 403

    body = request.get_json(silent=True) or {}
    force = bool(body.get('force'))
    _, material = _resolve_material_for_question(question)
    exp = _get_or_create_global(question_id=question.id)
    exp = _reuse_from_bank(question, exp)
    db.session.commit()

    if exp.status == 'TEACHER_APPROVED':
        return jsonify({'message': 'Pembahasan guru tidak ditimpa AI (BAGIAN M)', 'explanation': _serialize(exp)}), 200
    if exp.status in ('APPROVED',) and not force:
        return jsonify({'message': 'Pembahasan sudah disetujui. Gunakan regenerate untuk membuat versi baru.', 'explanation': _serialize(exp)}), 200
    if exp.status == 'STALE':
        force = True

    payload = _build_payload(
        question.text, question.question_type, question.difficulty,
        material.topic if material else None, _question_options(question),
        None, material, material.title if material else None,
    )
    ok, err = _generate_into(exp, payload, material, actor_id=user.id)
    if not ok:
        return jsonify({'error': 'Gagal membuat pembahasan', 'reason': err}), 502
    return jsonify({'message': 'Pembahasan AI berhasil dibuat.', 'explanation': _serialize(exp)}), 201


@jwt_required()
def generate_bank_explanation(bank_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat membuat pembahasan'}), 403
    bq = QuestionBank.query.get(bank_id)
    if not bq:
        return jsonify({'error': 'Soal bank tidak ditemukan'}), 404
    if user.role != 'admin' and bq.teacher_id != user.id:
        return jsonify({'error': 'Soal bank bukan milik Anda'}), 403

    body = request.get_json(silent=True) or {}
    force = bool(body.get('force'))
    material = None
    material_id = body.get('material_id')
    if material_id:
        material = Material.query.get(int(material_id))
        if not material:
            return jsonify({'error': 'Materi tidak ditemukan'}), 404

    exp = _get_or_create_global(bank_question_id=bq.id)
    db.session.commit()
    if exp.status == 'TEACHER_APPROVED':
        return jsonify({'message': 'Pembahasan guru tidak ditimpa AI (BAGIAN M)', 'explanation': _serialize(exp)}), 200
    if exp.status in ('APPROVED',) and not force:
        return jsonify({'message': 'Pembahasan sudah disetujui.', 'explanation': _serialize(exp)}), 200

    payload = _build_payload(
        bq.question_text, bq.question_type, bq.difficulty,
        bq.topic, _bank_options(bq), None, material, material.title if material else None,
    )
    ok, err = _generate_into(exp, payload, material, actor_id=user.id)
    if not ok:
        return jsonify({'error': 'Gagal membuat pembahasan', 'reason': err}), 502
    return jsonify({'message': 'Pembahasan AI berhasil dibuat.', 'explanation': _serialize(exp)}), 201


@jwt_required()
def batch_generate_explanations():
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat membuat pembahasan'}), 403
    body = request.get_json(silent=True) or {}
    question_ids = [int(x) for x in (body.get('question_ids') or []) if str(x).isdigit()]
    bank_ids = [int(x) for x in (body.get('bank_question_ids') or body.get('question_bank_ids') or []) if str(x).isdigit()]
    target_ids = question_ids or bank_ids
    is_bank = bool(bank_ids and not question_ids)
    if not target_ids:
        return jsonify({'error': 'Tidak ada soal yang dipilih'}), 400
    if len(target_ids) > BATCH_LIMIT:
        return jsonify({'error': f'Maksimal {BATCH_LIMIT} soal per batch'}), 400

    results = []
    ok_count = 0
    for tid in target_ids:
        try:
            if is_bank:
                bq = QuestionBank.query.get(tid)
                if not bq or (user.role != 'admin' and bq.teacher_id != user.id):
                    results.append({'id': tid, 'status': 'Failed', 'reason': 'bukan milik Anda'})
                    continue
                exp = _get_or_create_global(bank_question_id=tid)
                db.session.commit()
                if exp.status in ('APPROVED', 'TEACHER_APPROVED'):
                    results.append({'id': tid, 'status': 'Approved'})
                    continue
                material = None
                payload = _build_payload(
                    bq.question_text, bq.question_type, bq.difficulty,
                    bq.topic, _bank_options(bq), None, None, None)
                ok, err = _generate_into(exp, payload, None, actor_id=user.id)
            else:
                question = Question.query.get(tid)
                if not question:
                    results.append({'id': tid, 'status': 'Failed', 'reason': 'soal tidak ditemukan'})
                    continue
                quiz = Quiz.query.get(question.quiz_id) if question.quiz_id else None
                if quiz and not _can_manage_quiz(quiz, user):
                    results.append({'id': tid, 'status': 'Failed', 'reason': 'bukan milik Anda'})
                    continue
                exp = _get_or_create_global(question_id=tid)
                exp = _reuse_from_bank(question, exp)
                db.session.commit()
                if exp.status in ('APPROVED', 'TEACHER_APPROVED'):
                    results.append({'id': tid, 'status': 'Approved'})
                    continue
                _, material = _resolve_material_for_question(question)
                payload = _build_payload(
                    question.text, question.question_type, question.difficulty,
                    material.topic if material else None, _question_options(question),
                    None, material, material.title if material else None)
                ok, err = _generate_into(exp, payload, material, actor_id=user.id)
            if ok:
                ok_count += 1
                results.append({'id': tid, 'status': 'Generated'})
            else:
                results.append({'id': tid, 'status': 'Failed', 'reason': err})
        except Exception as e:
            db.session.rollback()
            results.append({'id': tid, 'status': 'Failed', 'reason': str(e)[:120]})
    return jsonify({'total': len(results), 'generated': ok_count, 'results': results}), 200


# ------------------------------------------------------------------
# STUDENT view + feedback
# ------------------------------------------------------------------
@jwt_required()
def get_question_explanation(question_id):
    user = _cur_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    exp = QuizExplanation.query.filter_by(question_id=question_id, student_id=None).first()
    if not exp:
        return jsonify({'error': 'Pembahasan belum tersedia'}), 404
    _mark_stale_if_needed(exp)
    if exp.status not in STUDENT_VIEWABLE:
        return jsonify({'error': 'Pembahasan belum disetujui guru'}), 403
    question = Question.query.get(question_id)
    personal = None
    if question:
        _, material = _resolve_material_for_question(question)
        opts = _question_options(question)
        answer = None
        if user.role == 'student':
            answer = Answer.query.filter_by(
                question_id=question.id, student_id=user.id).order_by(Answer.id.desc()).first()
        if answer is not None and answer.option:
            letter = _answer_letter(answer, question)
            personal = _personal_analysis(exp, letter, bool(answer.is_correct))
        _try_log(user.id, material.id if material else None, 'QUIZ_EXPLANATION_VIEWED',
                 {'question_id': question.id, 'explanation_id': exp.id, 'status': exp.status})
    return jsonify({'explanation': _serialize(exp, for_student=True, personal=personal)}), 200


@jwt_required()
def get_attempt_explanations(attempt_id):
    user = _cur_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    attempt = Submission.query.get(attempt_id)
    if not attempt:
        return jsonify({'error': 'Attempt tidak ditemukan'}), 404
    if user.role == 'student' and attempt.student_id != user.id:
        return jsonify({'error': 'Bukan attempt Anda'}), 403

    q_order = {q.id: i for i, q in enumerate(sorted(attempt.quiz.questions, key=lambda x: x.order_index))} if attempt.quiz else {}
    results = []
    answers = Answer.query.filter_by(submission_id=attempt.id).all()
    for ans in answers:
        qid = ans.question_id
        question = Question.query.get(qid)
        letter = _answer_letter(ans, question)
        exp = QuizExplanation.query.filter_by(question_id=qid, student_id=None).first()
        if not exp:
            results.append({'question_id': qid, 'order_index': q_order.get(qid, 0), 'status': 'MISSING',
                        'explanation': None, 'personal': None, 'answer': letter,
                        'is_correct': ans.is_correct,
                        'options': [{'option': o[0], 'text': o[1]} for o in _question_options(question)] if question else []})
            continue
        _mark_stale_if_needed(exp)
        if exp.status not in STUDENT_VIEWABLE:
            results.append({'question_id': qid, 'order_index': q_order.get(qid, 0), 'status': 'NOT_AVAILABLE',
                            'explanation': None, 'personal': None, 'answer': letter,
                            'is_correct': ans.is_correct,
                            'options': [{'option': o[0], 'text': o[1]} for o in _question_options(question)] if question else []})
            continue
        personal = _personal_analysis(exp, letter, bool(ans.is_correct))
        if question and user.role == 'student':
            _, material = _resolve_material_for_question(question)
            _try_log(user.id, material.id if material else None, 'QUIZ_EXPLANATION_VIEWED',
                     {'attempt_id': attempt.id, 'question_id': qid, 'explanation_id': exp.id})
        results.append({'question_id': qid, 'order_index': q_order.get(qid, 0),
                        'status': exp.status, 'explanation': _serialize(exp, for_student=True),
                        'personal': personal, 'answer': letter,
                        'is_correct': ans.is_correct,
                        'options': [{'option': o[0], 'text': o[1]} for o in _question_options(question)] if question else []})
    results.sort(key=lambda x: x['order_index'])
    return jsonify({'attempt_id': attempt.id, 'quiz_id': attempt.quiz_id, 'results': results}), 200


@jwt_required()
def submit_explanation_feedback(explanation_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Hanya siswa yang dapat memberi umpan balik'}), 403
    exp = QuizExplanation.query.get(explanation_id)
    if not exp:
        return jsonify({'error': 'Pembahasan tidak ditemukan'}), 404
    if exp.status not in STUDENT_VIEWABLE:
        return jsonify({'error': 'Pembahasan belum disetujui'}), 403
    body = request.get_json(silent=True) or {}
    rating = body.get('rating')
    if rating not in ('helpful', 'not_helpful'):
        return jsonify({'error': 'Rating tidak valid'}), 400
    reason = (body.get('reason') or '')[:200]
    fs = exp.feedback_summary or {'helpful': 0, 'not_helpful': 0, 'reasons': {}}
    fs['helpful'] = int(fs.get('helpful', 0)) + (1 if rating == 'helpful' else 0)
    fs['not_helpful'] = int(fs.get('not_helpful', 0)) + (1 if rating == 'not_helpful' else 0)
    if reason:
        rk = 'helpful' if rating == 'helpful' else 'not_helpful'
        reasons = fs.setdefault('reasons', {})
        reasons.setdefault(rk, []).append(reason)
        fs['reasons'][rk] = reasons[rk][-50:]
    exp.feedback_summary = fs
    exp.updated_at = datetime.utcnow()
    db.session.add(exp)
    db.session.commit()
    if exp.question_id:
        question = Question.query.get(exp.question_id)
        if question:
            _, material = _resolve_material_for_question(question)
            _try_log(user.id, material.id if material else None, 'AI_EXPLANATION_VIEWED_FEEDBACK',
                     {'explanation_id': exp.id, 'rating': rating})
    return jsonify({'message': 'Terima kasih atas umpan balik Anda.'}), 200


@jwt_required()
def log_recommended_material_click(explanation_id):
    user = _cur_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    exp = QuizExplanation.query.get(explanation_id)
    if not exp:
        return jsonify({'error': 'Pembahasan tidak ditemukan'}), 404
    _try_log(user.id, exp.recommended_material_id, 'RECOMMENDED_MATERIAL_CLICKED',
             {'explanation_id': exp.id, 'source': 'quiz_explanation'})
    return jsonify({'message': 'ok'}), 200


# ------------------------------------------------------------------
# TEACHER dashboard / management
# ------------------------------------------------------------------
@jwt_required()
def teacher_explanation_dashboard():
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat mengakses dashboard'}), 403

    scope_q = Quiz.query.all()
    if user.role != 'admin':
        qids = [q.id for q in scope_q if _can_manage_quiz(q, user)]
    else:
        qids = [q.id for q in scope_q]
    qid_set = set(qids) if qids else None

    def _in_scope(exp):
        if user.role == 'admin':
            return True
        if exp.bank_question_id:
            bq = QuestionBank.query.get(exp.bank_question_id)
            return bq and bq.teacher_id == user.id
        if exp.question_id:
            q = Question.query.get(exp.question_id)
            return q and q.quiz_id in qid_set if qid_set is not None else False
        return False

    exps = QuizExplanation.query.filter(QuizExplanation.student_id.is_(None)).all()
    exps = [e for e in exps if _in_scope(e)]
    status_map = {}
    for e in exps:
        status_map[e.status] = status_map.get(e.status, 0) + 1

    status_filter = request.args.get('status')
    q_filter = request.args.get('question_id')
    if status_filter and status_filter != 'ALL':
        exps = [e for e in exps if e.status == status_filter]
    if q_filter:
        exps = [e for e in exps if e.question_id == int(q_filter)]

    items = []
    for e in sorted(exps, key=lambda x: x.updated_at or x.created_at, reverse=True):
        items.append({
            'id': e.id,
            'question_id': e.question_id,
            'bank_question_id': e.bank_question_id,
            'question_text': (Question.query.get(e.question_id).text if e.question_id else None)
                             or (QuestionBank.query.get(e.bank_question_id).question_text if e.bank_question_id else None),
            'question_type': (Question.query.get(e.question_id).question_type if e.question_id else None)
                             or (QuestionBank.query.get(e.bank_question_id).question_type if e.bank_question_id else None),
            'status': e.status,
            'generated_by': e.generated_by,
            'model_name': e.model_name,
            'edited_by_teacher': e.edited_by_teacher,
            'recommended_material_id': e.recommended_material_id,
            'feedback_summary': e.feedback_summary,
            'updated_at': e.updated_at.isoformat() if e.updated_at else None,
        })

    return jsonify({
        'summary': {'total': len(exps), 'by_status': status_map},
        'items': items[:200],
    }), 200


@jwt_required()
def teacher_explanation_detail(explanation_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat mengakses'}), 403
    exp = QuizExplanation.query.get(explanation_id)
    if not exp:
        return jsonify({'error': 'Pembahasan tidak ditemukan'}), 404
    q = Question.query.get(exp.question_id) if exp.question_id else None
    if q and q.quiz_id and not _can_manage_quiz(q.quiz, user):
        return jsonify({'error': 'Bukan milik Anda'}), 403
    if exp.bank_question_id and user.role != 'admin':
        bq = QuestionBank.query.get(exp.bank_question_id)
        if bq and bq.teacher_id != user.id:
            return jsonify({'error': 'Bukan milik Anda'}), 403
    return jsonify({'explanation': _serialize(exp)}), 200


@jwt_required()
def approve_explanation(explanation_id):
    return _set_explanation_status(explanation_id, 'APPROVED', 'approve')


@jwt_required()
def reject_explanation(explanation_id):
    return _set_explanation_status(explanation_id, 'REJECTED', 'reject')


@jwt_required()
def _set_explanation_status(explanation_id, status, action):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat mengelola pembahasan'}), 403
    exp = QuizExplanation.query.get(explanation_id)
    if not exp:
        return jsonify({'error': 'Pembahasan tidak ditemukan'}), 404
    if exp.question_id:
        q = Question.query.get(exp.question_id)
        if q and q.quiz_id and not _can_manage_quiz(Quiz.query.get(q.quiz_id), user):
            return jsonify({'error': 'Bukan milik Anda'}), 403
    if exp.bank_question_id and user.role != 'admin':
        bq = QuestionBank.query.get(exp.bank_question_id)
        if bq and bq.teacher_id != user.id:
            return jsonify({'error': 'Bukan milik Anda'}), 403
    if exp.status == 'TEACHER_APPROVED' and status != 'APPROVED':
        return jsonify({'error': 'Pembahasan guru tidak boleh diubah AI (BAGIAN M)'}), 409
    exp.status = status
    if action == 'approve':
        exp.approved_by = user.id
        exp.approved_at = datetime.utcnow()
    exp.updated_at = datetime.utcnow()
    db.session.add(exp)
    db.session.commit()
    if exp.question_id:
        q = Question.query.get(exp.question_id)
        if q:
            _, mat = _resolve_material_for_question(q)
            _try_log(user.id, mat.id if mat else None, 'AI_EXPLANATION_APPROVED',
                     {'explanation_id': exp.id, 'status': status})
    return jsonify({'message': 'Status diperbarui.', 'explanation': _serialize(exp)}), 200


@jwt_required()
def regenerate_explanation(explanation_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat membuat ulang'}), 403
    exp = QuizExplanation.query.get(explanation_id)
    if not exp:
        return jsonify({'error': 'Pembahasan tidak ditemukan'}), 404
    if exp.status == 'TEACHER_APPROVED':
        return jsonify({'error': 'Pembahasan guru tidak boleh ditimpa AI (BAGIAN M)'}), 409
    if exp.question_id:
        question = Question.query.get(exp.question_id)
        quiz, material = _resolve_material_for_question(question) if question else (None, None)
        if quiz and not _can_manage_quiz(quiz, user):
            return jsonify({'error': 'Bukan milik Anda'}), 403
        if not question:
            return jsonify({'error': 'Soal tidak ditemukan'}), 404
        payload = _build_payload(
            question.text, question.question_type, question.difficulty,
            material.topic if material else None, _question_options(question),
            None, material, material.title if material else None)
        source_mat = material
    else:
        bq = QuestionBank.query.get(exp.bank_question_id)
        if not bq:
            return jsonify({'error': 'Soal bank tidak ditemukan'}), 404
        if user.role != 'admin' and bq.teacher_id != user.id:
            return jsonify({'error': 'Bukan milik Anda'}), 403
        payload = _build_payload(
            bq.question_text, bq.question_type, bq.difficulty,
            bq.topic, _bank_options(bq), None, None, None)
        source_mat = None
    ok, err = _generate_into(exp, payload, source_mat, actor_id=user.id)
    if not ok:
        return jsonify({'error': 'Gagal membuat ulang', 'reason': err}), 502
    if exp.question_id:
        q = Question.query.get(exp.question_id)
        if q:
            _, mat = _resolve_material_for_question(q)
            _try_log(user.id, mat.id if mat else None, 'AI_EXPLANATION_REGENERATED',
                     {'explanation_id': exp.id})
    return jsonify({'message': 'Pembahasan dibuat ulang.', 'explanation': _serialize(exp)}), 200


@jwt_required()
def edit_explanation(explanation_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat mengedit'}), 403
    exp = QuizExplanation.query.get(explanation_id)
    if not exp:
        return jsonify({'error': 'Pembahasan tidak ditemukan'}), 404
    body = request.get_json(silent=True) or {}
    for key in ('summary', 'correct_answer_explanation', 'student_answer_analysis',
                'option_explanations', 'key_concept', 'misconception',
                'recommended_material', 'recommended_material_id'):
        if key in body:
            setattr(exp, key, body[key])
    exp.edited_by_teacher = True
    exp.updated_at = datetime.utcnow()
    db.session.add(exp)
    db.session.commit()
    return jsonify({'message': 'Pembahasan diperbarui.', 'explanation': _serialize(exp)}), 200


@jwt_required()
def manual_explanation(question_id=None, bank_question_id=None):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat menulis pembahasan'}), 403
    body = request.get_json(silent=True) or {}
    question_id = question_id or body.get('question_id')
    bank_question_id = bank_question_id or body.get('bank_question_id')
    if not question_id and not bank_question_id:
        return jsonify({'error': 'question_id atau bank_question_id wajib'}), 400

    exp = _get_or_create_global(question_id=question_id, bank_question_id=bank_question_id)
    if question_id:
        q = Question.query.get(question_id)
        if q and q.quiz_id and not _can_manage_quiz(q.quiz, user):
            return jsonify({'error': 'Bukan milik Anda'}), 403
    if bank_question_id and user.role != 'admin':
        bq = QuestionBank.query.get(bank_question_id)
        if bq and bq.teacher_id != user.id:
            return jsonify({'error': 'Bukan milik Anda'}), 403
    for key in ('summary', 'correct_answer_explanation', 'student_answer_analysis',
                'option_explanations', 'key_concept', 'misconception',
                'recommended_material', 'recommended_material_id'):
        if key in body:
            setattr(exp, key, body[key])
    exp.status = 'TEACHER_APPROVED'
    exp.edited_by_teacher = True
    exp.approved_by = user.id
    exp.approved_at = datetime.utcnow()
    exp.generated_by = 'teacher'
    exp.model_name = None
    exp.prompt_version = None
    exp.updated_at = datetime.utcnow()
    db.session.add(exp)
    db.session.commit()
    return jsonify({'message': 'Pembahasan guru disimpan.', 'explanation': _serialize(exp)}), 201


@jwt_required()
def manual_explanation_from_id(explanation_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Hanya guru yang dapat menulis pembahasan'}), 403
    exp = QuizExplanation.query.get(explanation_id)
    if not exp:
        return jsonify({'error': 'Pembahasan tidak ditemukan'}), 404
    question_id = exp.question_id
    bank_question_id = exp.bank_question_id
    if not question_id and not bank_question_id:
        return jsonify({'error': 'Pembahasan tidak terkait soal apapun'}), 400
    return manual_explanation(question_id=question_id, bank_question_id=bank_question_id)

