from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User
from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.material_content import MaterialContent
from src.models.material_progress import MaterialProgress
from src.models.student_answer import StudentAnswer
from src.models.learning_activity import LearningActivity
from src.models.learning_session import LearningSession
from src.models.quiz import Quiz
from src.models.submission import Submission
from src.models.course import Course
from src.models.enrollment import Enrollment
from src.controllers.material_controller import _can_student_access, _can_manage
from src.config.database import db
from src.services import learning_analytics_service as analytics


def _user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _student(payload_id=None):
    user = _user()
    if not user:
        return None, jsonify({'error': 'User not found'}), 404
    if user.role != 'student':
        return None, jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    return user, None, None


def _teacher():
    user = _user()
    if not user:
        return None, jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return None, jsonify({'error': 'Endpoint ini khusus guru'}), 403
    return user, None, None


# ============================================================
# STUDENT DASHBOARD & PROGRESS
# ============================================================

@jwt_required()
def get_student_dashboard():
    user, err, code = _student()
    if err:
        return err, code
    return jsonify(analytics.student_dashboard(user)), 200


@jwt_required()
def get_student_progress_list():
    user, err, code = _student()
    if err:
        return err, code
    materials = analytics.student_accessible_materials(user)
    rows = [analytics.material_row_for(user.id, m) for m in materials]
    rows.sort(key=lambda r: (r['last_accessed'] or ''), reverse=True)
    summary = {
        'total': len(rows),
        'completed': sum(1 for r in rows if r['status'] == 'selesai'),
        'in_progress': sum(1 for r in rows if r['status'] in ('dimulai', 'sedang_belajar')),
        'not_started': sum(1 for r in rows if r['status'] == 'belum_dimulai'),
        'average_progress': round(sum(r['progress_percentage'] for r in rows) / len(rows), 1) if rows else 0.0,
        'total_learning_seconds': sum(r['learning_seconds'] for r in rows),
    }
    return jsonify({'summary': summary, 'materials': rows}), 200


def _enrich_material_detail(user, material):
    base = analytics.material_row_for(user.id, material)
    sections = MaterialSection.query.filter_by(material_id=material.id).order_by(MaterialSection.position).all()
    done_ids = analytics.completed_section_ids(user.id, material.id)
    done_map = {r.section_id: r for r in MaterialProgress.query.filter_by(
        student_id=user.id, material_id=material.id).all()}
    total_content = analytics.content_count_of(material.id)

    section_rows = []
    mastery_rows = []
    section_masteries = []
    for sec in sections:
        sid = sec.id
        done = done_ids
        completed = sid in done
        done_record = done_map.get(sid)
        completed_at = done_record.completed_at if done_record else None
        sc = analytics.section_content_count(sid)
        viewed_in = db.session.query(analytics.StudentContentTrack.content_id).join(
            MaterialContent, analytics.StudentContentTrack.content_id == MaterialContent.id
        ).filter(MaterialContent.section_id == sid,
                 analytics.StudentContentTrack.student_id == user.id).count()
        sec_interactive = StudentAnswer.query.filter_by(student_id=user.id, section_id=sid).all()
        sec_ia_total = len(sec_interactive)
        sec_ia_correct = sum(1 for a in sec_interactive if a.is_correct)
        sec_quizzes = Quiz.query.filter_by(section_id=sid).all()
        sec_q = analytics.quiz_performance_for(user.id, [q.id for q in sec_quizzes])
        scores_parts = []
        if sec_ia_total:
            scores_parts.append(round(sec_ia_correct / sec_ia_total * 100, 1))
        if sec_q['attempts']:
            scores_parts.append(sec_q['best'])
        sec_mastery = round(sum(scores_parts) / len(scores_parts), 1) if scores_parts else (100.0 if completed else 0.0)
        section_masteries.append(sec_mastery)
        mastery_rows.append({
            'source': 'section', 'section_id': sid, 'title': sec.title,
            'position': sec.position, 'score': sec_mastery,
            'mastery': analytics.mastery_info(sec_mastery),
        })
        section_rows.append({
            'section_id': sid,
            'title': sec.title,
            'position': sec.position,
            'completed': completed,
            'completed_at': completed_at.isoformat() + 'Z' if completed_at else None,
            'content_count': sc,
            'content_viewed': viewed_in,
            'quiz_count': len(sec_quizzes),
            'interactive_total': sec_ia_total,
            'interactive_correct': sec_ia_correct,
        })

    quizzes = analytics.material_quizzes(material.id)
    quiz_rows = []
    for q in quizzes:
        qp = analytics.quiz_performance_for(user.id, [q.id])
        last_sub = Submission.query.filter_by(quiz_id=q.id, student_id=user.id, status='submitted').order_by(
            Submission.submitted_at.desc()).first()
        quiz_rows.append({
            'quiz_id': q.id,
            'title': q.title,
            'status': q.status,
            'passing_grade': q.passing_grade,
            'attempts': qp['attempts'],
            'average': qp['average'],
            'best': qp['best'],
            'last_percentage': last_sub.percentage if last_sub else None,
            'passed': (last_sub.percentage or 0) >= (q.passing_grade or 75) if last_sub else None,
        })
        mastery_rows.append({
            'source': 'quiz', 'quiz_id': q.id, 'title': q.title,
            'score': qp['best'], 'mastery': analytics.mastery_info(qp['best']),
        })

    overall_mastery = round(sum(section_masteries) / len(section_masteries), 1) if section_masteries else base['progress_percentage']
    interactive = analytics.interactive_stats(user.id, material.id)
    video = analytics.video_stats(user.id, material.id)
    activities = LearningActivity.query.filter_by(
        student_id=user.id, material_id=material.id
    ).order_by(LearningActivity.created_at.desc()).limit(20).all()

    return {
        **base,
        'mastery_score': overall_mastery,
        'mastery': analytics.mastery_info(overall_mastery),
        'quiz_performance': quiz_rows,
        'sections': section_rows,
        'mastery_rows': mastery_rows,
        'interactive': interactive,
        'video': video,
        'activities': [{
            'id': a.id,
            'event_type': a.event_type,
            'section_id': a.section_id,
            'content_id': a.content_id,
            'content_title': a.content.text if a.content and hasattr(a.content, 'text') else None,
            'data': a.data,
            'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
        } for a in activities],
    }


@jwt_required()
def get_student_material_detail(material_id):
    user, err, code = _student()
    if err:
        return err, code
    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404
    if material.status != 'published':
        return jsonify({'error': 'Materi belum dipublikasikan'}), 403
    if not _can_student_access(material, user):
        return jsonify({'error': 'Materi hanya untuk kelas yang diikuti'}), 403
    return jsonify(_enrich_material_detail(user, material)), 200


@jwt_required()
def get_student_quiz_performance():
    user, err, code = _student()
    if err:
        return err, code
    materials = analytics.student_accessible_materials(user)
    quiz_ids = []
    for m in materials:
        quiz_ids += [q.id for q in analytics.material_quizzes(m.id)]
    rows = Submission.query.filter(
        Submission.student_id == user.id, Submission.status == 'submitted'
    ).all()
    by_quiz = {}
    for s in rows:
        if s.quiz_id not in quiz_ids:
            continue
        bucket = by_quiz.setdefault(s.quiz_id, {'attempts': [], 'passed': 0})
        bucket['attempts'].append(s.percentage)
        if (s.percentage or 0) >= (s.quiz.passing_grade or 75):
            bucket['passed'] += 1
    result = []
    for q in (Quiz.query.filter(Quiz.id.in_(quiz_ids)).all() if quiz_ids else []):
        data = by_quiz.get(q.id, {'attempts': [], 'passed': 0})
        scores = [x for x in data['attempts'] if x is not None]
        result.append({
            'quiz_id': q.id,
            'title': q.title,
            'material_title': q.material.title if q.material else None,
            'difficulty': ', '.join(sorted({(qs.difficulty or 'medium') for qs in q.questions})),
            'attempts': len(scores),
            'passed': data['passed'],
            'average': round(sum(scores) / len(scores), 1) if scores else 0.0,
            'best': round(max(scores), 1) if scores else 0.0,
            'lowest': round(min(scores), 1) if scores else 0.0,
        })
    result.sort(key=lambda r: r['best'], reverse=True)
    return jsonify({'quizzes': result}), 200


@jwt_required()
def get_student_activity():
    user, err, code = _student()
    if err:
        return err, code
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    material_id = request.args.get('material_id', type=int)
    q = LearningActivity.query.filter_by(student_id=user.id)
    if material_id:
        q = q.filter_by(material_id=material_id)
    total = q.count()
    rows = q.order_by(LearningActivity.created_at.desc()).offset(
        (page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'activities': [{
            'id': a.id, 'event_type': a.event_type, 'material_id': a.material_id,
            'material_title': a.material.title if a.material else None,
            'section_id': a.section_id, 'content_id': a.content_id,
            'content_title': a.content.text if a.content and hasattr(a.content, 'text') else None,
            'data': a.data, 'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
        } for a in rows],
        'page': page, 'per_page': per_page, 'total': total,
    }), 200


# ============================================================
# TEACHER ANALYTICS
# ============================================================

def _filters_from_args():
    return {
        'course_id': request.args.get('course_id'),
        'phase': request.args.get('phase'),
        'topic': request.args.get('topic'),
        'material_id': request.args.get('material_id'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'status_learning': request.args.get('status_learning'),
        'mastery_status': request.args.get('mastery_status'),
        'search': request.args.get('search'),
    }


@jwt_required()
def get_teacher_analytics_overview():
    teacher, err, code = _teacher()
    if err:
        return err, code
    filters = _filters_from_args()
    return jsonify(analytics.teacher_overview(teacher.id, filters)), 200


@jwt_required()
def get_teacher_analytics_options():
    teacher, err, code = _teacher()
    if err:
        return err, code
    courses = analytics.teacher_courses(teacher.id)
    materials = analytics.teacher_materials({}, teacher_id=teacher.id)
    phases = sorted({m.phase for m in materials if m.phase})
    topics = sorted({m.topic for m in materials if m.topic})
    return jsonify({
        'courses': [{'id': c.id, 'name': c.name} for c in courses],
        'phases': phases,
        'topics': topics,
        'materials': [{'id': m.id, 'title': m.title, 'phase': m.phase, 'topic': m.topic} for m in materials],
        'mastery_statuses': [l['label'] for l in analytics.MASTERY_LEVELS],
        'status_learnings': ['belum_dimulai', 'dimulai', 'sedang_belajar', 'selesai'],
    }), 200


@jwt_required()
def get_teacher_analytics_materials():
    teacher, err, code = _teacher()
    if err:
        return err, code
    filters = _filters_from_args()
    return jsonify(analytics.teacher_material_summaries(teacher.id, filters)), 200


@jwt_required()
def get_teacher_analytics_material(material_id):
    teacher, err, code = _teacher()
    if err:
        return err, code
    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404
    if not _can_manage(material, teacher):
        return jsonify({'error': 'Anda hanya dapat melihat materi milik sendiri'}), 403
    return jsonify(analytics.material_analytics(material, teacher.id)), 200


@jwt_required()
def get_teacher_analytics_quiz(quiz_id):
    teacher, err, code = _teacher()
    if err:
        return err, code
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    if teacher.role != 'admin':
        if quiz.material_id:
            if not (quiz.material and quiz.material.teacher_id == teacher.id):
                return jsonify({'error': 'Anda hanya dapat melihat kuis milik sendiri'}), 403
        elif quiz.created_by:
            if quiz.created_by != teacher.id:
                return jsonify({'error': 'Anda hanya dapat melihat kuis milik sendiri'}), 403
        elif not (quiz.course and quiz.course.teacher_id == teacher.id):
            return jsonify({'error': 'Anda hanya dapat melihat kuis milik sendiri'}), 403
    return jsonify(analytics.quiz_analysis(quiz, teacher.id)), 200


@jwt_required()
def get_teacher_analytics_students():
    teacher, err, code = _teacher()
    if err:
        return err, code
    filters = _filters_from_args()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = max(1, min(per_page, 100))
    return jsonify(analytics.teacher_students_table(teacher.id, filters, page, per_page)), 200


@jwt_required()
def get_teacher_analytics_student(student_id):
    teacher, err, code = _teacher()
    if err:
        return err, code
    target = User.query.get(student_id)
    if not target or target.role != 'student':
        return jsonify({'error': 'Siswa tidak ditemukan'}), 404
    course_ids = analytics.teacher_course_ids(teacher.id)
    enrolled = Enrollment.query.filter_by(student_id=target.id).all()
    is_mine = any(e.course_id in course_ids for e in enrolled)
    if not is_mine and teacher.role != 'admin':
        return jsonify({'error': 'Siswa bukan anggota kelas Anda'}), 403

    materials = analytics.teacher_materials({}, teacher_id=teacher.id)
    material_rows = [analytics.material_row_for(target.id, m) for m in materials if any(
        c.id in {e.course_id for e in enrolled} for c in (m.course_links or [])) or not m.course_links]
    quiz_ids = []
    for m in materials:
        quiz_ids += [q.id for q in analytics.material_quizzes(m.id)]
    quiz_rows = Submission.query.filter(
        Submission.student_id == target.id, Submission.status == 'submitted',
        (Submission.quiz_id.in_(quiz_ids) if quiz_ids else db.true())
    ).all()
    qperf = analytics.quiz_performance_for(target.id, quiz_ids)
    interactive = StudentAnswer.query.filter_by(student_id=target.id).all()
    learning_seconds = 0
    for mrow in material_rows:
        learning_seconds += mrow['learning_seconds']
    return jsonify({
        'student': {
            'id': target.id, 'name': target.name, 'email': target.email,
            'enrolled_courses': [{'id': e.course.id, 'name': e.course.name,
                                  'teacher_name': e.course.teacher.name if e.course.teacher else None}
                                 for e in enrolled],
        },
        'summary': {
            'materials_total': len(materials),
            'materials_completed': sum(1 for r in material_rows if r['status'] == 'selesai'),
            'average_progress': round(sum(r['progress_percentage'] for r in material_rows) / len(material_rows), 1) if material_rows else 0.0,
            'learning_seconds': learning_seconds,
            'quiz_attempts': qperf['attempts'],
            'quiz_avg': qperf['average'],
            'quiz_best': qperf['best'],
            'interactive_answered': len(interactive),
            'interactive_accuracy': round(sum(1 for a in interactive if a.is_correct) / len(interactive) * 100, 1) if interactive else 0.0,
        },
        'materials': material_rows,
        'quizzes': [{
            'quiz_id': s.quiz_id,
            'quiz_title': s.quiz.title if s.quiz else None,
            'attempt_number': s.attempt_number,
            'percentage': s.percentage,
            'score': s.score,
            'correct_count': s.correct_count,
            'wrong_count': s.wrong_count,
            'submitted_at': s.submitted_at.isoformat() + 'Z' if s.submitted_at else None,
        } for s in sorted(quiz_rows, key=lambda s: s.submitted_at or datetime_utc(), reverse=True)],
    }), 200


def datetime_utc():
    from datetime import datetime
    return datetime.utcnow()


@jwt_required()
def get_teacher_analytics_topics():
    teacher, err, code = _teacher()
    if err:
        return err, code
    filters = _filters_from_args()
    return jsonify(analytics.teacher_topics(teacher.id, filters)), 200


@jwt_required()
def get_teacher_analytics_difficulty():
    teacher, err, code = _teacher()
    if err:
        return err, code
    filters = _filters_from_args()
    materials = analytics.teacher_materials(filters, teacher_id=teacher.id)
    student_ids = analytics.teacher_student_ids(teacher.id)
    agg = {'interactive': {}, 'quiz': {}}
    for m in materials:
        quiz_ids = [q.id for q in analytics.material_quizzes(m.id)]
        diff = analytics.difficulty_analytics(m.id, teacher.id, quiz_ids=quiz_ids, student_ids=student_ids)
        for level, bucket in diff['interactive'].items():
            b = agg['interactive'].setdefault(level, {'total': 0, 'correct': 0})
            b['total'] += bucket['total']
            b['correct'] += bucket['correct']
        for level, bucket in diff['quiz'].items():
            b = agg['quiz'].setdefault(level, {'total': 0, 'answered': 0, 'correct': 0})
            b['total'] += bucket['total']
            b['answered'] += bucket['answered']
            b['correct'] += bucket['correct']
    for b in agg['interactive'].values():
        b['accuracy'] = round(b['correct'] / b['total'] * 100, 1) if b['total'] else 0.0
    for b in agg['quiz'].values():
        b['accuracy'] = round(b['correct'] / b['answered'] * 100, 1) if b.get('answered') else 0.0
    return jsonify(agg), 200


# ============================================================
# FEATURE EXTRACTION SERVICE (ML-ready, tanpa inference ML)
# ============================================================

@jwt_required()
def post_student_features(material_id):
    user, err, code = _student()
    if err:
        return err, code
    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404
    if material.status != 'published' or not _can_student_access(material, user):
        return jsonify({'error': 'Materi tidak dapat diakses'}), 403
    features = analytics.build_student_features(user.id, material)
    return jsonify({'features': features}), 200


@jwt_required()
def get_feature_dataset():
    user = _user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role == 'student':
        dataset = analytics.build_dataset(student_ids=[user.id])
    elif user.role in ('teacher', 'admin'):
        dataset = analytics.build_dataset(teacher_id=user.id)
    else:
        return jsonify({'error': 'Akses ditolak'}), 403
    return jsonify({'count': len(dataset), 'columns': analytics.FEATURE_FIELDS, 'dataset': dataset}), 200