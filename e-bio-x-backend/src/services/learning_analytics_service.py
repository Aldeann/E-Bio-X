from datetime import datetime, timedelta
from src.config.database import db
from src.models.material import Material, material_courses
from src.models.material_section import MaterialSection
from src.models.material_content import MaterialContent
from src.models.material_progress import MaterialProgress
from src.models.material_student_state import MaterialStudentState
from src.models.student_answer import StudentAnswer
from src.models.student_content_track import StudentContentTrack
from src.models.video_progress import VideoProgress
from src.models.learning_session import LearningSession
from src.models.learning_activity import LearningActivity
from src.models.quiz import Quiz
from src.models.question import Question
from src.models.answer import Answer
from src.models.submission import Submission
from src.models.course import Course
from src.models.enrollment import Enrollment
from src.models.user import User
from sqlalchemy import func, distinct

# ============================================================
# MASTERY
# ============================================================

MASTERY_LEVELS = [
    {'min_score': 90, 'max_score': 100, 'label': 'Baik Sekali'},
    {'min_score': 75, 'max_score': 89, 'label': 'Baik'},
    {'min_score': 60, 'max_score': 74, 'label': 'Cukup'},
    {'min_score': 0, 'max_score': 59, 'label': 'Kurang'},
]


def mastery_info(score):
    s = score if score is not None else 0
    for level in MASTERY_LEVELS:
        if s >= level['min_score']:
            return {'label': level['label'], 'min_score': level['min_score'],
                    'max_score': level['max_score'], 'score': round(float(s), 1)}
    return {'label': 'Kurang', 'min_score': 0, 'max_score': 59, 'score': round(float(s), 1)}


def status_learning(progress_percentage, started, completed):
    if completed:
        return 'selesai'
    if started and progress_percentage > 0:
        return 'sedang_belajar'
    if started:
        return 'dimulai'
    return 'belum_dimulai'


# ============================================================
# ACTIVITY LOGGING
# ============================================================

ALLOWED_EVENT_TYPES = {
    'material_opened',
    'material_closed',
    'section_opened',
    'section_completed',
    'content_viewed',
    'video_played',
    'video_paused',
    'video_completed',
    'pdf_opened',
    'interactive_started',
    'question_answered',
    'quiz_started',
    'quiz_submitted',
    'material_completed',
    'note_created',
    'bookmark_created',
    'recommendation_clicked',
}


def log_activity(student_id, material_id, event_type, section_id=None, content_id=None, data=None, silent=True):
    if event_type not in ALLOWED_EVENT_TYPES:
        return None
    try:
        activity = LearningActivity(
            student_id=student_id,
            material_id=material_id,
            section_id=section_id,
            content_id=content_id,
            event_type=event_type,
            data=data or {},
        )
        db.session.add(activity)
        t = touch_state(student_id, material_id, section_id=section_id, content_id=content_id, silent=True)
        db.session.commit()
        return activity
    except Exception:
        db.session.rollback()
        if not silent:
            raise
        return None


def touch_state(student_id, material_id, section_id=None, content_id=None, silent=True):
    try:
        state = MaterialStudentState.query.filter_by(
            material_id=material_id, student_id=student_id
        ).first()
        if not state:
            state = MaterialStudentState(material_id=material_id, student_id=student_id, completed=False)
            db.session.add(state)
        now = datetime.utcnow()
        if not state.first_accessed_at:
            state.first_accessed_at = now
        state.last_accessed = now
        if section_id is not None:
            state.last_section_id = section_id
        if content_id is not None:
            state.last_content_id = content_id
            content = MaterialContent.query.get(content_id)
            if content and content.section_id:
                state.last_section_id = content.section_id
        return state
    except Exception:
        db.session.rollback()
        if not silent:
            raise
        return None


def mark_content_viewed(student_id, material_id, content_id, silent=True):
    try:
        track = StudentContentTrack.query.filter_by(
            student_id=student_id, content_id=content_id
        ).first()
        if track:
            track.view_count = (track.view_count or 1) + 1
            track.viewed_at = datetime.utcnow()
        else:
            track = StudentContentTrack(
                student_id=student_id, material_id=material_id,
                content_id=content_id, view_count=1,
            )
            db.session.add(track)
        touch_state(student_id, material_id, content_id=content_id, silent=True)
        db.session.commit()
        return track
    except Exception:
        db.session.rollback()
        if not silent:
            raise
        return None


# ============================================================
# SESSIONS
# ============================================================

def _active_seconds(session, now=None):
    end = session.last_seen_at or session.ended_at or (now or datetime.utcnow())
    try:
        delta = (end - session.started_at).total_seconds()
    except Exception:
        return 0
    return max(0, int(round(delta)))


def get_active_session(student_id, material_id):
    return LearningSession.query.filter_by(
        student_id=student_id, material_id=material_id, status='active'
    ).order_by(LearningSession.started_at.desc()).first()


def open_session(student_id, material_id):
    session = get_active_session(student_id, material_id)
    if session:
        last_seen = session.last_seen_at or session.started_at
        if datetime.utcnow() - last_seen > timedelta(minutes=5):
            session.status = 'closed'
            session.ended_at = session.last_seen_at or datetime.utcnow()
            db.session.add(session)
            db.session.flush()
            session = LearningSession(student_id=student_id, material_id=material_id)
            db.session.add(session)
            db.session.flush()
        else:
            session.last_seen_at = datetime.utcnow()
            db.session.add(session)
            db.session.flush()
            _sync_learning_seconds(student_id, material_id)
            return session
    else:
        session = LearningSession(student_id=student_id, material_id=material_id)
        db.session.add(session)
        db.session.flush()
    _sync_learning_seconds(student_id, material_id)
    return session


def _sync_learning_seconds(student_id, material_id):
    sessions = LearningSession.query.filter_by(student_id=student_id, material_id=material_id).all()
    total = 0
    for s in sessions:
        if s.status == 'closed' and s.ended_at:
            try:
                total += max(0, int(round((s.ended_at - s.started_at).total_seconds())))
            except Exception:
                pass
        else:
            total += _active_seconds(s)
    state = MaterialStudentState.query.filter_by(material_id=material_id, student_id=student_id).first()
    if state is None:
        state = MaterialStudentState(material_id=material_id, student_id=student_id, completed=False)
        db.session.add(state)
    state.total_learning_seconds = total
    return total


def close_session(student_id, material_id):
    session = get_active_session(student_id, material_id)
    if session:
        session.status = 'closed'
        session.ended_at = session.last_seen_at or datetime.utcnow()
        db.session.add(session)
        _sync_learning_seconds(student_id, material_id)
        db.session.commit()


def learning_seconds_for(student_id, material_id):
    sessions = LearningSession.query.filter_by(student_id=student_id, material_id=material_id).all()
    total = 0
    for s in sessions:
        if s.status == 'closed' and s.ended_at:
            try:
                total += max(0, int(round((s.ended_at - s.started_at).total_seconds())))
            except Exception:
                pass
        else:
            total += _active_seconds(s)
    return max(total, 0)


def student_total_seconds(student_id):
    states = MaterialStudentState.query.filter_by(student_id=student_id).all()
    return sum(s.total_learning_seconds or 0 for s in states)


# ============================================================
# PROGRESS HELPERS
# ============================================================

def section_ids_of(material_id):
    rows = MaterialSection.query.filter_by(material_id=material_id).order_by(MaterialSection.position).all()
    return rows


def total_sections(material_id):
    return MaterialSection.query.filter_by(material_id=material_id).count()


def completed_section_ids(student_id, material_id):
    return {r.section_id for r in MaterialProgress.query.filter_by(
        student_id=student_id, material_id=material_id).all()}


def progress_percentage(material_id, student_id):
    total_sec = total_sections(material_id)
    if total_sec == 0:
        return 100.0
    done = len(completed_section_ids(student_id, material_id))
    return round(done / total_sec * 100, 1)


def content_count_of(material_id):
    return db.session.query(func.count(MaterialContent.id)).join(
        MaterialSection, MaterialContent.section_id == MaterialSection.id
    ).filter(MaterialSection.material_id == material_id).scalar() or 0


def section_content_count(section_id):
    return MaterialContent.query.filter_by(section_id=section_id).count()


def interactive_stats(student_id, material_id):
    rows = StudentAnswer.query.filter_by(student_id=student_id, material_id=material_id).all()
    total = len(rows)
    correct = sum(1 for r in rows if r.is_correct)
    return {
        'interactive_total': total,
        'interactive_correct': correct,
        'interactive_accuracy': round(correct / total * 100, 1) if total else 0.0,
        'difficulty_accuracy': _difficulty_accuracy_material(student_id, material_id),
    }


def _difficulty_accuracy_material(student_id, material_id):
    rows = StudentAnswer.query.filter_by(student_id=student_id, material_id=material_id).all()
    by_diff = {}
    for r in rows:
        section = MaterialSection.query.get(r.section_id)
        content = MaterialContent.query.get(r.content_id)
        diff = None
        if content and isinstance(content.data, dict):
            diff = content.data.get('difficulty') or content.data.get('level')
        if not diff:
            diff = 'medium'
        bucket = by_diff.setdefault(diff, {'total': 0, 'correct': 0})
        bucket['total'] += 1
        if r.is_correct:
            bucket['correct'] += 1
    result = {}
    for diff, bucket in by_diff.items():
        result[diff] = {
            'total': bucket['total'],
            'correct': bucket['correct'],
            'accuracy': round(bucket['correct'] / bucket['total'] * 100, 1) if bucket['total'] else 0.0,
        }
    return result


def quiz_performance_for(student_id, quiz_ids=None):
    q = Submission.query.filter_by(student_id=student_id, status='submitted')
    if quiz_ids:
        q = q.filter(Submission.quiz_id.in_(quiz_ids))
    rows = q.all()
    scores = [r.percentage for r in rows if r.percentage is not None]
    return {
        'attempts': len(rows),
        'passed': sum(1 for r in rows if (r.percentage or 0) >= 75),
        'average': round(sum(scores) / len(scores), 1) if scores else 0.0,
        'best': round(max(scores), 1) if scores else 0.0,
        'lowest': round(min(scores), 1) if scores else 0.0,
    }


def material_quizzes(material_id):
    return Quiz.query.filter_by(material_id=material_id).all()


def video_stats(student_id, material_id):
    rows = VideoProgress.query.filter_by(student_id=student_id, material_id=material_id).all()
    if not rows:
        return {'videos': 0, 'completed_videos': 0, 'average_completion': 0.0}
    comps = []
    for r in rows:
        if r.video_duration and r.video_duration > 0:
            comps.append(min(100.0, (r.watched_duration or 0) / r.video_duration * 100))
        elif r.completed:
            comps.append(100.0)
    return {
        'videos': len(rows),
        'completed_videos': sum(1 for r in rows if r.completed),
        'average_completion': round(sum(comps) / len(comps), 1) if comps else 0.0,
    }


# ============================================================
# STUDENT SCOPING
# ============================================================

def student_accessible_materials(student):
    materials = Material.query.filter_by(status='published')
    enrolled_ids = {e.course_id for e in student.enrollments}
    result = []
    for m in materials:
        if m.course_links:
            if any(c.id in enrolled_ids for c in m.course_links):
                result.append(m)
        else:
            result.append(m)
    return result


def material_status_for(student_id, material_id):
    state = MaterialStudentState.query.filter_by(student_id=student_id, material_id=material_id).first()
    started = state is not None and (state.first_accessed_at is not None)
    completed = bool(state.completed if state else False)
    pct = progress_percentage(material_id, student_id)
    return status_learning(pct, started, completed)


def material_row_for(student_id, material):
    state = MaterialStudentState.query.filter_by(student_id=student_id, material_id=material.id).first()
    pct = progress_percentage(material.id, student_id)
    done_ids = completed_section_ids(student_id, material.id)
    qperf = quiz_performance_for(student_id, [q.id for q in material_quizzes(material.id)])
    overall_pct = qperf['best'] if qperf['attempts'] else pct
    return {
        'material_id': material.id,
        'title': material.title,
        'description': material.description,
        'phase': material.phase,
        'topic': material.topic,
        'teacher_id': material.teacher_id,
        'teacher_name': material.teacher.name if material.teacher else None,
        'estimated_time': material.estimated_time,
        'status': material_status_for(student_id, material.id),
        'progress_percentage': pct,
        'completed_sections': len(done_ids),
        'total_sections': total_sections(material.id),
        'content_count': content_count_of(material.id),
        'learning_seconds': state.total_learning_seconds if state else 0,
        'last_section_id': state.last_section_id if state else None,
        'last_section_title': state.last_section.title if state and state.last_section else None,
        'last_content_id': state.last_content_id if state else None,
        'last_accessed': state.last_accessed.isoformat() + 'Z' if state and state.last_accessed else None,
        'completed_at': state.completed_at.isoformat() + 'Z' if state and state.completed_at else None,
        'quiz_attempts': qperf['attempts'],
        'quiz_avg': qperf['average'],
        'quiz_best': qperf['best'],
        'mastery_score': overall_pct,
        'mastery': mastery_info(overall_pct),
    }


def student_dashboard(student):
    materials = student_accessible_materials(student)
    rows = [material_row_for(student.id, m) for m in materials]
    started = [r for r in rows if r['status'] in ('dimulai', 'sedang_belajar', 'selesai')]
    completed = [r for r in rows if r['status'] == 'selesai']
    avg_progress = round(sum(r['progress_percentage'] for r in rows) / len(rows), 1) if rows else 0.0
    learning_seconds = sum(r['learning_seconds'] for r in rows)
    quiz_rows = Submission.query.filter_by(student_id=student.id, status='submitted').all()
    quiz_scores = [r.percentage for r in quiz_rows if r.percentage is not None]
    ia = StudentAnswer.query.filter_by(student_id=student.id).count()
    iac = StudentAnswer.query.filter_by(student_id=student.id, is_correct=True).count()
    summary = {
        'materials_total': len(rows),
        'materials_started': len(started),
        'materials_completed': len(completed),
        'average_progress': avg_progress,
        'learning_seconds': learning_seconds,
        'learning_minutes': round(learning_seconds / 60, 1),
        'quizzes_taken': len(quiz_rows),
        'quiz_avg': round(sum(quiz_scores) / len(quiz_scores), 1) if quiz_scores else 0.0,
        'quiz_best': round(max(quiz_scores), 1) if quiz_scores else 0.0,
        'interactive_answered': ia,
        'interactive_correct': iac,
        'interactive_accuracy': round(iac / ia * 100, 1) if ia else 0.0,
    }
    pending = [r for r in started if r['status'] in ('dimulai', 'sedang_belajar')]
    pending.sort(key=lambda r: (r['last_accessed'] or ''), reverse=True)
    return {
        'summary': summary,
        'continue_learning': pending[:3],
        'materials': rows,
    }


# ============================================================
# TEACHER SCOPING
# ============================================================

def teacher_course_ids(teacher_id):
    return [c.id for c in Course.query.filter_by(teacher_id=teacher_id).all()]


def teacher_courses(teacher_id):
    return Course.query.filter_by(teacher_id=teacher_id).all()


def teacher_student_users(teacher_id):
    course_ids = teacher_course_ids(teacher_id)
    if not course_ids:
        return []
    rows = db.session.query(User).join(Enrollment, Enrollment.student_id == User.id).filter(
        Enrollment.course_id.in_(course_ids), User.role == 'student'
    ).distinct().all()
    return rows


def teacher_student_ids(teacher_id):
    return [u.id for u in teacher_student_users(teacher_id)]


def teacher_materials(filters=None, teacher_id=None):
    if teacher_id is None:
        teacher_id = 0
    filters = filters or {}
    q = Material.query.filter(Material.teacher_id == teacher_id)
    course_id = filters.get('course_id')
    if course_id:
        try:
            course_id = int(course_id)
        except (TypeError, ValueError):
            course_id = None
        if course_id:
            linked = set(r[0] for r in db.session.query(material_courses.c.material_id).filter(
                material_courses.c.course_id == course_id).all())
            legacy = set(r[0] for r in db.session.query(Material.id).filter(
                Material.course_id == course_id).all())
            ids = linked | legacy
            q = q.filter(Material.id.in_(ids) if ids else Material.id == -1)
    if filters.get('phase'):
        q = q.filter(Material.phase == filters['phase'])
    if filters.get('topic'):
        q = q.filter(Material.topic == filters['topic'])
    if filters.get('material_id'):
        try:
            q = q.filter(Material.id == int(filters['material_id']))
        except (TypeError, ValueError):
            q = q.filter(Material.id == -1)
    return q.all()


def _date_filtered(students, date_from, date_to, material_id=None):
    sids = [u.id for u in students]
    if not sids:
        return []
    q = LearningActivity.query.filter(LearningActivity.student_id.in_(sids))
    if material_id:
        q = q.filter(LearningActivity.material_id == int(material_id))
    if date_from:
        try:
            q = q.filter(LearningActivity.created_at >= datetime.fromisoformat(str(date_from)))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(LearningActivity.created_at <= datetime.fromisoformat(str(date_to)) + timedelta(days=1))
        except ValueError:
            pass
    return q.all()


def material_student_ids(material_id, teacher_id):
    """Students of the teacher's courses that have touched the material OR all teacher students."""
    students = teacher_student_users(teacher_id)
    ids = [u.id for u in students]
    if not ids:
        return []
    touched = set(r[0] for r in db.session.query(MaterialStudentState.student_id).filter(
        MaterialStudentState.material_id == material_id,
        MaterialStudentState.student_id.in_(ids)).all())
    return list(touched)


def material_analytics(material, teacher_id):
    total_sec = total_sections(material.id)
    students = teacher_student_users(teacher_id)
    student_ids = [u.id for u in students]
    if not student_ids:
        return {'empty': True}

    states = MaterialStudentState.query.filter(MaterialStudentState.material_id == material.id,
                                              MaterialStudentState.student_id.in_(student_ids)).all()
    state_map = {s.student_id: s for s in states}
    progress_rows = MaterialProgress.query.filter(MaterialProgress.material_id == material.id,
                                                 MaterialProgress.student_id.in_(student_ids)).all()
    done_map = {}
    for r in progress_rows:
        done_map.setdefault(r.student_id, set()).add(r.section_id)

    per_student = []
    for sid in student_ids:
        state = state_map.get(sid)
        done = done_map.get(sid, set())
        pct = round(len(done) / total_sec * 100, 1) if total_sec else 100.0
        per_student.append({
            'student_id': sid,
            'progress_percentage': pct,
            'completed_sections': len(done),
            'started': state is not None and state.first_accessed_at is not None,
            'completed': bool(state.completed if state else False),
            'learning_seconds': state.total_learning_seconds if state else 0,
            'last_accessed': state.last_accessed.isoformat() + 'Z' if state and state.last_accessed else None,
        })

    # section completion
    sections = MaterialSection.query.filter_by(material_id=material.id).order_by(MaterialSection.position).all()
    section_completion = []
    for sec in sections:
        done_count = sum(1 for done in done_map.values() if sec.id in done)
        section_completion.append({
            'section_id': sec.id,
            'title': sec.title,
            'position': sec.position,
            'content_count': section_content_count(sec.id),
            'completed_students': done_count,
            'total_students': len(student_ids),
            'completion_rate': round(done_count / len(student_ids) * 100, 1) if student_ids else 0.0,
        })

    interactive_rows = StudentAnswer.query.filter(StudentAnswer.material_id == material.id,
                                                  StudentAnswer.student_id.in_(student_ids)).all()
    interactive = {
        'total': len(interactive_rows),
        'students_active': len({r.student_id for r in interactive_rows}),
        'correct': sum(1 for r in interactive_rows if r.is_correct),
        'accuracy': round(sum(1 for r in interactive_rows if r.is_correct) / len(interactive_rows) * 100, 1) if interactive_rows else 0.0,
    }

    quizzes = material_quizzes(material.id)
    quiz_ids = [q.id for q in quizzes]
    quiz_totals = {'attempts': 0, 'avg': 0.0, 'passed': 0, 'students_active': 0}
    scores = []
    quiz_student_set = set()
    if quiz_ids:
        subs = Submission.query.filter(Submission.quiz_id.in_(quiz_ids), Submission.status == 'submitted').all()
        quiz_totals['attempts'] = len(subs)
        for s in subs:
            quiz_student_set.add(s.student_id)
            if s.percentage is not None:
                scores.append(s.percentage)
                if s.percentage >= 75:
                    quiz_totals['passed'] += 1
        quiz_totals['avg'] = round(sum(scores) / len(scores), 1) if scores else 0.0
        quiz_totals['students_active'] = len(quiz_student_set)

    ratios = [p['progress_percentage'] for p in per_student]
    avg_progress = round(sum(ratios) / len(ratios), 1) if ratios else 0.0
    mastery_dist = {'Baik Sekali': 0, 'Baik': 0, 'Cukup': 0, 'Kurang': 0}
    status_dist = {'dimulai': 0, 'sedang_belajar': 0, 'selesai': 0, 'belum_dimulai': 0}
    state_lookup = {s.student_id: s for s in states}
    for sid in student_ids:
        state = state_lookup.get(sid)
        comp = bool(state.completed if state else False)
        started = bool(state and state.first_accessed_at)
        pct = ratio_of_material(sid, done_map, total_sec, material.id)
        label = mastery_info(pct if pct else 0)['label']
        mastery_dist[label] = mastery_dist.get(label, 0) + 1
        sl = status_learning(pct, started, comp)
        status_dist[sl] = status_dist.get(sl, 0) + 1

    difficulty = difficulty_analytics(material.id, teacher_id, quiz_ids=quiz_ids, student_ids=student_ids)

    return {
        'empty': False,
        'material_id': material.id,
        'title': material.title,
        'phase': material.phase,
        'topic': material.topic,
        'total_students': len(student_ids),
        'students_active': len(states),
        'total_sections': total_sec,
        'students_completed': sum(1 for p in per_student if p['completed']),
        'average_progress': avg_progress,
        'average_learning_seconds': round(sum(p['learning_seconds'] for p in per_student) / len(per_student), 1) if per_student else 0,
        'interactive': interactive,
        'quiz': quiz_totals,
        'section_completion': section_completion,
        'per_student': sorted(per_student, key=lambda p: p['learning_seconds'], reverse=True),
        'mastery_distribution': mastery_dist,
        'status_distribution': status_dist,
        'difficulty': difficulty,
    }


def ratio_of_material(student_id, done_map, total_sec, material_id):
    done = done_map.get(student_id, set())
    return round(len(done) / total_sec * 100, 1) if total_sec else 100.0


def difficulty_analytics(material_id, teacher_id, quiz_ids=None, student_ids=None):
    if student_ids is None:
        student_ids = teacher_student_ids(teacher_id)
    if not student_ids:
        return {'interactive': {}, 'quiz': {}}

    ia = {}
    rows = StudentAnswer.query.filter(StudentAnswer.material_id == material_id,
                                      StudentAnswer.student_id.in_(student_ids)).all()
    for r in rows:
        content = MaterialContent.query.get(r.content_id)
        diff = None
        if content and isinstance(content.data, dict):
            diff = content.data.get('difficulty') or content.data.get('level')
        diff = diff or 'medium'
        bucket = ia.setdefault(diff, {'total': 0, 'correct': 0, 'accuracy': 0.0})
        bucket['total'] += 1
        if r.is_correct:
            bucket['correct'] += 1
    for b in ia.values():
        b['accuracy'] = round(b['correct'] / b['total'] * 100, 1) if b['total'] else 0.0

    qd = {}
    if quiz_ids:
        qrows = Question.query.filter(Question.quiz_id.in_(quiz_ids)).all()
        for qst in qrows:
            diff = (qst.difficulty or 'medium').lower()
            bucket = qd.setdefault(diff, {'total': 0, 'answered': 0, 'correct': 0, 'accuracy': 0.0})
            bucket['total'] += 1
            for a in qst.answers if hasattr(qst, 'answers') else []:
                if a.student_id in student_ids:
                    bucket['answered'] += 1
                    if a.is_correct:
                        bucket['correct'] += 1
        for b in qd.values():
            b['accuracy'] = round(b['correct'] / b['answered'] * 100, 1) if b.get('answered') else 0.0

    return {'interactive': ia, 'quiz': qd}


def quiz_analysis(quiz, teacher_id):
    student_ids = teacher_student_ids(teacher_id)
    subs = Submission.query.filter_by(quiz_id=quiz.id, status='submitted').order_by(Submission.submitted_at).all()
    if student_ids:
        subs = [s for s in subs if s.student_id in student_ids]
    scores = [s.percentage for s in subs if s.percentage is not None]
    summary = {
        'quiz_id': quiz.id,
        'title': quiz.title,
        'attempts': len(subs),
        'students_active': len({s.student_id for s in subs}),
        'average': round(sum(scores) / len(scores), 1) if scores else 0.0,
        'best': round(max(scores), 1) if scores else 0.0,
        'lowest': round(min(scores), 1) if scores else 0.0,
        'passing_grade': quiz.passing_grade or 75,
        'passed': sum(1 for s in scores if s >= (quiz.passing_grade or 75)),
        'pass_rate': round(sum(1 for s in scores if s >= (quiz.passing_grade or 75)) / len(scores) * 100, 1) if scores else 0.0,
    }
    questions = Question.query.filter_by(quiz_id=quiz.id).order_by(Question.order_index).all()
    per_question = []
    for q in questions:
        answers = Answer.query.filter_by(question_id=q.id).all()
        total_ans = len(answers)
        correct_ans = sum(1 for a in answers if a.is_correct)
        per_question.append({
            'question_id': q.id,
            'question_text': q.text[:200],
            'difficulty': q.difficulty,
            'points': q.points,
            'order_index': q.order_index,
            'answered': total_ans,
            'correct': correct_ans,
            'accuracy': round(correct_ans / total_ans * 100, 1) if total_ans else 0.0,
            'skipped': max(0, len(subs) - total_ans),
        })
    attempts_by_student = [{
        'student_id': s.student_id,
        'student_name': s.student.name if s.student else None,
        'attempt_number': s.attempt_number,
        'score': s.score,
        'percentage': s.percentage,
        'correct_count': s.correct_count,
        'wrong_count': s.wrong_count,
        'submitted_at': s.submitted_at.isoformat() + 'Z' if s.submitted_at else None,
        'passed': (s.percentage or 0) >= (quiz.passing_grade or 75),
    } for s in subs]
    difficulty = {}
    for q in questions:
        diff = (q.difficulty or 'medium').lower()
        bucket = difficulty.setdefault(diff, {'total': 0, 'answered': 0, 'correct': 0})
        bucket['total'] += 1
        answers = Answer.query.filter_by(question_id=q.id).all()
        for a in answers:
            bucket['answered'] += 1
            if a.is_correct:
                bucket['correct'] += 1
    for b in difficulty.values():
        b['accuracy'] = round(b['correct'] / b['answered'] * 100, 1) if b.get('answered') else 0.0
    return {'summary': summary, 'per_question': per_question,
            'attempts_by_student': attempts_by_student, 'difficulty': difficulty}


def teacher_students_table(teacher_id, filters=None, page=1, per_page=20):
    filters = filters or {}
    students = teacher_student_users(teacher_id)
    materials = teacher_materials(filters, teacher_id=teacher_id)
    material_ids = [m.id for m in materials]
    if not material_ids:
        return {'students': [], 'page': page, 'per_page': per_page, 'total': 0, 'total_pages': 0}

    rows = []
    for u in students:
        pcts = []
        completed = 0
        q_attempts = 0
        q_scores = []
        ia_total = 0
        ia_correct = 0
        learn_secs = 0
        # aggregate across filtered materials
        states = MaterialStudentState.query.filter(MaterialStudentState.student_id == u.id,
                                                   MaterialStudentState.material_id.in_(material_ids)).all()
        for st in states:
            learn_secs += st.total_learning_seconds or 0
            if st.completed:
                completed += 1
            pcts.append(progress_percentage(st.material_id, u.id))
        subs = Submission.query.filter(Submission.student_id == u.id,
                                       Submission.status == 'submitted').all()
        quiz_ids = set(Quiz.query.filter(Quiz.material_id.in_(material_ids)).with_entities(Quiz.id).all())
        subs = [s for s in subs if s.quiz_id in quiz_ids]
        q_attempts = len(subs)
        for s in subs:
            if s.percentage is not None:
                q_scores.append(s.percentage)
        ia_rows = StudentAnswer.query.filter(StudentAnswer.student_id == u.id,
                                             StudentAnswer.material_id.in_(material_ids)).all()
        ia_total = len(ia_rows)
        ia_correct = sum(1 for r in ia_rows if r.is_correct)
        avg_pct = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
        overall_mastery = round(sum(q_scores) / len(q_scores), 1) if q_scores else avg_pct
        sl = 'belum_dimulai'
        if completed > 0:
            sl = 'selesai'
        elif states:
            sl = 'sedang_belajar'
        rows.append({
            'student_id': u.id,
            'name': u.name,
            'email': u.email,
            'materials_started': len(states),
            'materials_completed': completed,
            'average_progress': avg_pct,
            'quiz_attempts': q_attempts,
            'quiz_avg': round(sum(q_scores) / len(q_scores), 1) if q_scores else 0.0,
            'interactive_answered': ia_total,
            'interactive_accuracy': round(ia_correct / ia_total * 100, 1) if ia_total else 0.0,
            'learning_seconds': learn_secs,
            'status_learning': sl,
            'mastery_score': overall_mastery,
            'mastery': mastery_info(overall_mastery),
        })

    if filters.get('status_learning'):
        rows = [r for r in rows if r['status_learning'] == filters['status_learning']]
    if filters.get('mastery_status'):
        rows = [r for r in rows if r['mastery']['label'] == filters['mastery_status']]
    if filters.get('search'):
        s = str(filters['search']).lower()
        rows = [r for r in rows if s in r['name'].lower() or s in r['email'].lower()]
    rows.sort(key=lambda r: r['mastery_score'], reverse=True)
    total = len(rows)
    total_pages = max(1, -(-total // per_page))
    start = (page - 1) * per_page
    paged = rows[start:start + per_page]
    return {'students': paged, 'page': page, 'per_page': per_page,
            'total': total, 'total_pages': total_pages}


def teacher_material_summaries(teacher_id, filters=None):
    materials = teacher_materials(filters, teacher_id=teacher_id)
    if not materials:
        return []
    students = teacher_student_users(teacher_id)
    sids = [u.id for u in students]
    out = []
    for m in materials:
        states = MaterialStudentState.query.filter(MaterialStudentState.material_id == m.id,
                                                   (MaterialStudentState.student_id.in_(sids) if sids else db.true())).all()
        completed = sum(1 for st in states if st.completed)
        ia = StudentAnswer.query.filter(StudentAnswer.material_id == m.id,
                                        (StudentAnswer.student_id.in_(sids) if sids else db.true())).all()
        qids = [q.id for q in material_quizzes(m.id)]
        subs = []
        if qids:
            subs = Submission.query.filter(Submission.quiz_id.in_(qids), Submission.status == 'submitted',
                                       (Submission.student_id.in_(sids) if sids else db.true())).all()
        avg_progress = round(sum(progress_percentage(m.id, st.student_id) for st in states) / len(states), 1) if states else 0.0
        out.append({
            'material_id': m.id,
            'title': m.title,
            'phase': m.phase,
            'topic': m.topic,
            'total_students': len(sids),
            'students_started': len(states),
            'students_completed': completed,
            'average_progress': avg_progress,
            'interactive': {
                'total': len(ia),
                'accuracy': round(sum(1 for a in ia if a.is_correct) / len(ia) * 100, 1) if ia else 0.0,
            },
            'quiz': {'attempts': len(subs)},
            'average_learning_seconds': round(sum((st.total_learning_seconds or 0) for st in states) / len(sids), 1) if sids else 0,
        })
    out.sort(key=lambda r: r['average_progress'], reverse=True)
    return out


def teacher_overview(teacher_id, filters=None):
    filters = filters or {}
    materials = teacher_materials(filters, teacher_id=teacher_id)
    if not materials:
        return {'materials': 0, 'students': 0, 'total_learning_seconds': 0,
                'mastery_distribution': {'Baik Sekali': 0, 'Baik': 0, 'Cukup': 0, 'Kurang': 0},
                'status_distribution': {'belum_dimulai': 0, 'dimulai': 0, 'sedang_belajar': 0, 'selesai': 0},
                'average_progress': 0.0, 'interactive': 0, 'quiz_attempts': 0}
    students = teacher_student_users(teacher_id)
    student_ids = [u.id for u in students]
    material_ids = [m.id for m in materials]

    states = MaterialStudentState.query.filter(
        MaterialStudentState.material_id.in_(material_ids),
        (MaterialStudentState.student_id.in_(student_ids) if student_ids else MaterialStudentState.material_id == -1)
    ).all() if student_ids else []

    total_secs = sum(s.total_learning_seconds or 0 for s in states)
    mastery_dist = {'Baik Sekali': 0, 'Baik': 0, 'Cukup': 0, 'Kurang': 0}
    status_dist = {'belum_dimulai': 0, 'dimulai': 0, 'sedang_belajar': 0, 'selesai': 0}
    pcts = []
    for st in states:
        pct = progress_percentage(st.material_id, st.student_id)
        pcts.append(pct)
        mastery_dist[mastery_info(pct)['label']] = mastery_dist.get(mastery_info(pct)['label'], 0) + 1
        comp = bool(st.completed)
        started = st.first_accessed_at is not None
        sl = status_learning(pct, started, comp)
        status_dist[sl] = status_dist.get(sl, 0) + 1

    ia_rows = StudentAnswer.query.filter(StudentAnswer.material_id.in_(material_ids)).all()
    if student_ids:
        ia_rows = [r for r in ia_rows if r.student_id in student_ids]
    ia_correct = sum(1 for r in ia_rows if r.is_correct)

    quiz_ids = set(Quiz.query.filter(Quiz.material_id.in_(material_ids)).with_entities(Quiz.id).all())
    subs = Submission.query.filter(Submission.quiz_id.in_(quiz_ids) if quiz_ids else db.true()).all() if quiz_ids else []
    subs = [s for s in subs if s.status == 'submitted' and (s.student_id in student_ids or not student_ids)]
    scores = [s.percentage for s in subs if s.percentage is not None]

    date_from = filters.get('date_from')
    date_to = filters.get('date_to')
    activity = _date_filtered(students, date_from, date_to)
    active_student_ids = {a.student_id for a in activity} if activity else set()

    sids = student_ids or []
    return {
        'materials': len(materials),
        'materials_with_completion': sum(1 for m in materials if any(s.material_id == m.id and s.completed for s in states)),
        'students': len(sids),
        'students_active': len(active_student_ids),
        'materials_started': len({(s.student_id, s.material_id) for s in states}),
        'materials_completed_count': sum(1 for s in states if s.completed),
        'average_progress': round(sum(pcts) / len(pcts), 1) if pcts else 0.0,
        'total_learning_seconds': total_secs,
        'learning_hours': round(total_secs / 3600, 1),
        'interactive_total': len(ia_rows),
        'interactive_correct': ia_correct,
        'interactive_accuracy': round(ia_correct / len(ia_rows) * 100, 1) if ia_rows else 0.0,
        'quiz_attempts': len(subs),
        'quiz_avg': round(sum(scores) / len(scores), 1) if scores else 0.0,
        'quiz_pass_rate': round(sum(1 for s in scores if s >= 75) / len(scores) * 100, 1) if scores else 0.0,
        'mastery_distribution': mastery_dist,
        'status_distribution': status_dist,
        'avg_duration_minutes': round((total_secs / len(states)) / 60, 1) if states else 0.0,
    }


def teacher_topics(teacher_id, filters=None):
    filters = filters or {}
    materials = teacher_materials(filters, teacher_id=teacher_id)
    students = teacher_student_users(teacher_id)
    student_ids = [u.id for u in students]
    by_topic = {}
    for m in materials:
        topic = m.topic or 'Umum'
        bucket = by_topic.setdefault(topic, {'topic': topic, 'materials': 0, 'material_ids': [],
                                             'completed': 0, 'started': 0, 'pcts': []})
        bucket['materials'] += 1
        bucket['material_ids'].append(m.id)
    if not by_topic:
        return []
    ids_by_topic = {k: v['material_ids'] for k, v in by_topic.items()}
    all_ids = [i for v in ids_by_topic.values() for i in v]
    states = MaterialStudentState.query.filter(MaterialStudentState.material_id.in_(all_ids)).all() if all_ids else []
    if student_ids:
        states = [s for s in states if s.student_id in student_ids]
    for st in states:
        mtopic = None
        for k, v in by_topic.items():
            if st.material_id in v['material_ids']:
                mtopic = k
        if not mtopic:
            continue
        bucket = by_topic[mtopic]
        pct = progress_percentage(st.material_id, st.student_id)
        bucket['pcts'].append(pct)
        bucket['started'] += 1
        if st.completed:
            bucket['completed'] += 1
    result = []
    for topic, bucket in by_topic.items():
        avg = round(sum(bucket['pcts']) / len(bucket['pcts']), 1) if bucket['pcts'] else 0.0
        result.append({
            'topic': bucket['topic'],
            'materials': bucket['materials'],
            'students_started': bucket['started'],
            'students_completed': bucket['completed'],
            'average_progress': avg,
            'mastery': mastery_info(avg),
        })
    result.sort(key=lambda r: r['average_progress'], reverse=True)
    return result


# ============================================================
# FEATURE EXTRACTION (feature engineering for ML, tanpa inference ML)
# ============================================================

FEATURE_FIELDS = [
    'student_id', 'material_id', 'progress_percentage', 'learning_seconds',
    'interactive_answered', 'interactive_correct', 'interactive_accuracy',
    'content_viewed', 'content_total', 'view_ratio',
    'video_completion_avg', 'videos_completed',
    'quiz_attempts', 'quiz_average', 'quiz_best',
    'mastery_score', 'mastery_label', 'status_learning',
    'days_since_first_access', 'active_days', 'activity_count',
]


def _active_days(student_id, material_id):
    rows = LearningActivity.query.filter_by(student_id=student_id, material_id=material_id).all()
    return len({r.created_at.date() for r in rows})


def build_student_features(student_id, material, state=None):
    if state is None:
        state = MaterialStudentState.query.filter_by(student_id=student_id, material_id=material.id).first()
    pct = progress_percentage(material.id, student_id)
    ia = interactive_stats(student_id, material.id)
    viewed = StudentContentTrack.query.filter_by(student_id=student_id, material_id=material.id).count()
    total_content = content_count_of(material.id)
    vs = video_stats(student_id, material.id)
    qperf = quiz_performance_for(student_id, [q.id for q in material_quizzes(material.id)])
    acts = LearningActivity.query.filter_by(student_id=student_id, material_id=material.id).count()
    days = (datetime.utcnow() - state.first_accessed_at).days if state and state.first_accessed_at else 0
    overall = qperf['best'] if qperf['attempts'] else pct
    feats = {
        'student_id': student_id,
        'material_id': material.id,
        'progress_percentage': pct,
        'learning_seconds': state.total_learning_seconds if state else 0,
        'interactive_answered': ia['interactive_total'],
        'interactive_correct': ia['interactive_correct'],
        'interactive_accuracy': ia['interactive_accuracy'],
        'content_viewed': viewed,
        'content_total': total_content,
        'view_ratio': round(viewed / total_content, 3) if total_content else 0.0,
        'video_completion_avg': vs['average_completion'],
        'videos_completed': vs['completed_videos'],
        'quiz_attempts': qperf['attempts'],
        'quiz_average': qperf['average'],
        'quiz_best': qperf['best'],
        'mastery_score': overall,
        'mastery_label': mastery_info(overall)['label'],
        'status_learning': material_status_for(student_id, material.id),
        'days_since_first_access': max(0, days),
        'active_days': _active_days(student_id, material.id),
        'activity_count': acts,
    }
    return {k: feats.get(k) for k in FEATURE_FIELDS}


def build_dataset(teacher_id=None, material_ids=None, student_ids=None):
    if teacher_id:
        materials = teacher_materials({}, teacher_id=teacher_id)
    elif material_ids:
        materials = Material.query.filter(Material.id.in_(material_ids)).all()
    else:
        materials = Material.query.all()
    if student_ids:
        sid_set = set(student_ids)
    elif teacher_id:
        sid_set = set(teacher_student_ids(teacher_id))
    else:
        sid_set = {u.id for u in User.query.filter_by(role='student').all()}
    dataset = []
    for m in materials:
        for sid in sid_set:
            state = MaterialStudentState.query.filter_by(student_id=sid, material_id=m.id).first()
            if state is None and not StudentActivityQuery(sid, m.id):
                continue
            dataset.append(build_student_features(sid, m, state))
    return dataset


def StudentActivityQuery(student_id, material_id):
    return LearningActivity.query.filter_by(student_id=student_id, material_id=material_id).first() is not None