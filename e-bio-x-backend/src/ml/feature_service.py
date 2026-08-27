# ============================================================
# TAHAP 5 - ML data preparation / feature engineering.
#
# Converts raw Tahap-4 data into one aggregated feature row per
# student. `student_id` is ONLY an identifier, never a model feature.
#
# Mapping DB field -> ML feature:
#   MDone/materials                              -> material_completion_rate
#   completed sections / total sections          -> section_completion_rate
#   student_answers (correct/total)              -> interactive_accuracy
#   submissions.percentage (mean)                -> quiz_average
#   submissions.percentage (max)                 -> quiz_best_score
#   student_answers by content difficulty        -> easy/medium/hard_accuracy
#   learning_sessions / state total seconds      -> learning_minutes
#   submissions count                            -> quiz_attempts
#   (interactive + quiz) correct / answered      -> correct_rate
#   forum_posts (no parent)                      -> forum_posts_count
#   forum_posts (with parent)                    -> forum_replies_count
#   forum_questions (questioner)                 -> forum_questions_asked
#   forum_answers (presenter)                    -> forum_answers_given
#   forum_reactions on student posts             -> forum_reactions_received
#   quiz_explanations (viewable statuses)        -> ai_explanations_viewed
#   quiz_explanations (feedback.helpful=true)    -> ai_explanations_helpful
# ============================================================
from src.models.material_section import MaterialSection
from src.models.material_progress import MaterialProgress
from src.models.material_student_state import MaterialStudentState
from src.models.student_answer import StudentAnswer
from src.models.learning_activity import LearningActivity
from src.models.submission import Submission
from src.services import learning_analytics_service as analytics
from src.ml import ml_config as cfg


def accessible_materials(student):
    return analytics.student_accessible_materials(student)


def _started_material_ids(student):
    ids = {r.material_id for r in MaterialStudentState.query.filter_by(student_id=student.id).all()}
    ids.update(p.material_id for p in MaterialProgress.query.filter_by(student_id=student.id).all())
    ids.update(a.material_id for a in LearningActivity.query.filter_by(student_id=student.id).all())
    return ids


def _aggregate_difficulty(student, started_materials):
    by_diff = {}
    for m in started_materials:
        bucket = analytics._difficulty_accuracy_material(student.id, m.id)
        for diff, b in bucket.items():
            target = by_diff.setdefault(diff, {'total': 0, 'correct': 0})
            target['total'] += b['total']
            target['correct'] += b['correct']
    return by_diff


def aggregate_student_features(student):
    """Build one aggregated ML feature row for the student.

    Returns None when data is insufficient (INSUFFICIENT_DATA) - we never
    fabricate a row that would silently produce a fake profile.
    """
    materials = accessible_materials(student)
    started_ids = _started_material_ids(student)
    started = [m for m in materials if m.id in started_ids]

    # ---- signal count -------------------------------------------
    quiz_rows = Submission.query.filter_by(
        student_id=student.id, status='submitted').all()
    interactive_rows = StudentAnswer.query.filter_by(student_id=student.id).all()
    completed_sections = MaterialProgress.query.filter_by(student_id=student.id).count()
    signals = len(interactive_rows) + len([s for s in quiz_rows if s.percentage is not None]) + completed_sections
    if signals < cfg.MIN_SIGNALS_FOR_STUDENT:
        return None

    # ---- progress -----------------------------------------------
    pcts = [analytics.progress_percentage(m.id, student.id) for m in started]
    material_completion_rate = (sum(pcts) / len(pcts)) / 100.0 if pcts else 0.0

    total_sections = 0
    completed_sections_total = 0
    for m in materials:
        sections = MaterialSection.query.filter_by(material_id=m.id).all()
        sid_set = {s.id for s in sections}
        total_sections += len(sid_set)
        completed_sections_total += len(analytics.completed_section_ids(student.id, m.id) & sid_set)
    section_completion_rate = (completed_sections_total / total_sections) if total_sections else 0.0

    # ---- interactive accuracy -----------------------------------
    ia_total = len(interactive_rows)
    ia_correct = sum(1 for r in interactive_rows if r.is_correct)
    interactive_accuracy = (ia_correct / ia_total) if ia_total else 0.0

    # ---- difficulty accuracy -------------------------------------
    diff = _aggregate_difficulty(student, started)

    def diff_acc(level):
        b = diff.get(level)
        return (b['correct'] / b['total']) if b and b['total'] else 0.0

    # ---- quiz ----------------------------------------------------
    scores = [r.percentage for r in quiz_rows if r.percentage is not None]
    quiz_average = (sum(scores) / len(scores)) / 100.0 if scores else 0.0
    quiz_best_score = (max(scores) / 100.0) if scores else 0.0
    quiz_attempts = len(scores)

    # ---- learning time -------------------------------------------
    learning_minutes = analytics.student_total_seconds(student.id) / 60.0

    # ---- overall correct rate ------------------------------------
    quiz_correct = sum(r.correct_count or 0 for r in quiz_rows)
    quiz_wrong = sum(r.wrong_count or 0 for r in quiz_rows)
    answered_total = ia_total + quiz_correct + quiz_wrong
    answered_correct = ia_correct + quiz_correct
    correct_rate = (answered_correct / answered_total) if answered_total else 0.0

    # ---- forum activity ------------------------------------------
    from src.models.forum import ForumPost, ForumQuestion, ForumAnswer, ForumReaction
    forum_posts = ForumPost.query.filter_by(
        author_id=student.id, deleted_at=None).filter(
        ForumPost.parent_id.is_(None)).count()
    forum_replies = ForumPost.query.filter_by(
        author_id=student.id, deleted_at=None).filter(
        ForumPost.parent_id.isnot(None)).count()
    forum_questions = ForumQuestion.query.filter_by(questioner_id=student.id).count()
    forum_answers = ForumAnswer.query.filter_by(presenter_id=student.id).count()

    # reactions received on student's posts
    student_post_ids = [p.id for p in ForumPost.query.filter_by(
        author_id=student.id, deleted_at=None).with_entities(ForumPost.id).all()]
    forum_reactions = ForumReaction.query.filter(
        ForumReaction.post_id.in_(student_post_ids)).count() if student_post_ids else 0

    # ---- AI explanation interactions ------------------------------
    from src.models.quiz_explanation import QuizExplanation
    STUDENT_VIEWABLE = ('APPROVED', 'TEACHER_APPROVED')
    explanation_rows = QuizExplanation.query.filter_by(student_id=student.id).filter(
        QuizExplanation.status.in_(STUDENT_VIEWABLE)).all()
    ai_explanations_viewed = len(explanation_rows)
    ai_explanations_helpful = sum(
        1 for e in explanation_rows
        if isinstance(e.feedback_summary, dict) and e.feedback_summary.get('helpful')
    )

    return {
        cfg.ID_COLUMN: student.id,
        'material_completion_rate': round(material_completion_rate, 4),
        'section_completion_rate': round(section_completion_rate, 4),
        'interactive_accuracy': round(interactive_accuracy, 4),
        'quiz_average': round(quiz_average, 4),
        'quiz_best_score': round(quiz_best_score, 4),
        'easy_accuracy': round(diff_acc('easy'), 4),
        'medium_accuracy': round(diff_acc('medium'), 4),
        'hard_accuracy': round(diff_acc('hard'), 4),
        'learning_minutes': round(learning_minutes, 2),
        'quiz_attempts': quiz_attempts,
        'correct_rate': round(correct_rate, 4),
        'forum_posts_count': forum_posts,
        'forum_replies_count': forum_replies,
        'forum_questions_asked': forum_questions,
        'forum_answers_given': forum_answers,
        'forum_reactions_received': forum_reactions,
        'ai_explanations_viewed': ai_explanations_viewed,
        'ai_explanations_helpful': ai_explanations_helpful,
    }


def build_dataset(students):
    """Returns [feature rows]; only students with sufficient data included."""
    rows = []
    for s in students:
        row = aggregate_student_features(s)
        if row is not None:
            rows.append(row)
    return rows


def feature_matrix(rows):
    """Return X (list of lists aligned to cfg.FEATURES) and identifiers."""
    ids = [r[cfg.ID_COLUMN] for r in rows]
    X = [[r.get(f, 0.0) for f in cfg.FEATURES] for r in rows]
    return ids, X