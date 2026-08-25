import re
import time
from datetime import datetime
from src.config.database import db
from src.models.user import User
from src.models.forum import (
    Forum, ForumMember, ForumPost, ForumReaction, ForumMention,
    ForumAttachment, ForumQuestion, ForumAnswer, ForumFeedback,
    ForumReport, ForumModerationLog, Notification, UserXp, XpLog,
    Achievement, UserAchievement, ForumSetting,
)
from src.models.enrollment import Enrollment
from src.models.course import Course
from src.services import storage_service

# ============================================================
# SANITIZATION
# ============================================================

_TAG_RE = re.compile(r'<[^>]+>')
_JS_URL_RE = re.compile(r'(?i)(javascript|vbscript|data)\s*:')
_URL_RE = re.compile(r'(?i)(https?://[^\s<>"]+)')

FORUM_EVENT_TYPES = {
    'FORUM_CREATED',
    'FORUM_VIEWED',
    'POST_CREATED',
    'REPLY_CREATED',
    'QUESTION_CREATED',
    'QUESTION_ANSWERED',
    'REACTION_ADDED',
    'BEST_ANSWER_SELECTED',
    'TEACHER_FEEDBACK_CREATED',
    'FORUM_COMPLETED',
}

FORUM_STATUS_ALLOWED = ('DRAFT', 'SCHEDULED', 'ACTIVE', 'CLOSED', 'ARCHIVED')


def sanitize_text(text):
    """Strip HTML/scripts and dangerous URL protocols. Content is stored as
    safe plain text; the client renders a restricted markdown subset."""
    if text is None:
        return ''
    text = _TAG_RE.sub('', str(text))
    text = _JS_URL_RE.sub('', text)
    return text.strip()


def sanitize_url(url):
    if not url:
        return None
    url = str(url).strip()
    if _JS_URL_RE.search(url):
        return None
    return url


def extract_urls(text):
    return _URL_RE.findall(text or '')


def plain_links(content):
    """Replace http(s) URLs with a safe [url](url) markdown token."""
    return _URL_RE.sub(r'[\1](\1)', content or '')


# ============================================================
# PERMISSIONS
# ============================================================

def is_teacher(user):
    return bool(user and user.role in ('teacher', 'admin'))


def is_student(user):
    return bool(user and user.role == 'student')


def resolve_forum_status(forum):
    """Lazy status resolution: SCHEDULED->ACTIVE on start, auto-close on end."""
    now = datetime.utcnow()
    changed = False
    if forum.status == 'SCHEDULED' and forum.start_at and forum.start_at <= now:
        forum.status = 'ACTIVE'
        changed = True
    if forum.status in ('ACTIVE', 'SCHEDULED') and forum.end_at and forum.end_at < now:
        forum.status = 'CLOSED'
        forum.end_at = now
        changed = True
    if changed:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
    return forum.status


def can_view_forum(forum, user):
    if not user:
        return False
    if user.role == 'admin':
        return True
    if forum.visibility == 'PRIVATE':
        if str(forum.created_by) == str(user.id):
            return True
        if user.role == 'teacher':
            return _teacher_of_forum(forum, user) or str(forum.created_by) == str(user.id)
        return False
    # CLASS / COURSE
    if user.role == 'teacher':
        if _teacher_of_forum(forum, user) or str(forum.created_by) == str(user.id):
            return True
        return False
    if user.role == 'student':
        return _student_in_forum_course(forum, user)
    return False


def can_manage_forum(forum, user):
    if not user:
        return False
    if user.role == 'admin':
        return True
    if user.role == 'teacher':
        return _teacher_of_forum(forum, user) or str(forum.created_by) == str(user.id)
    return False


def can_post_in_forum(forum, user):
    """Posting allowed in ACTIVE forums. Teachers may also reply to closed forums."""
    if not user:
        return False
    if not can_view_forum(forum, user):
        return False
    status = forum.status
    if status in ('DRAFT', 'ARCHIVED'):
        return can_manage_forum(forum, user)
    if status == 'CLOSED':
        return is_teacher(user) and can_manage_forum(forum, user)
    return True


def is_presenter(forum, user):
    if not user:
        return False
    if forum.presenter_id and str(forum.presenter_id) == str(user.id):
        return True
    return ForumMember.query.filter_by(
        forum_id=forum.id, user_id=user.id, role='presenter'
    ).first() is not None


def can_answer_question(forum, user):
    if is_teacher(user) and can_manage_forum(forum, user):
        return True
    return is_presenter(forum, user)


def _teacher_of_forum(forum, user):
    if forum.course_id and forum.course:
        return str(forum.course.teacher_id) == str(user.id)
    if forum.material_id and forum.material and forum.material.teacher_id:
        return str(forum.material.teacher_id) == str(user.id)
    return False


def _student_in_forum_course(forum, user):
    if forum.course_id:
        return Enrollment.query.filter_by(student_id=user.id, course_id=forum.course_id).first() is not None
    if forum.material_id and forum.material:
        from src.controllers.material_controller import _can_student_access
        return forum.material.status == 'published' and _can_student_access(forum.material, user)
    return True


def presenters_of(forum):
    members = ForumMember.query.filter_by(forum_id=forum.id, role='presenter').all()
    ids = [m.user_id for m in members]
    if forum.presenter_id and forum.presenter_id not in ids:
        ids.append(forum.presenter_id)
    return ids


def group_members_of(forum):
    members = ForumMember.query.filter_by(forum_id=forum.id).all()
    return [m for m in members if m.role in ('presenter', 'member')]


# ============================================================
# SETTINGS
# ============================================================

def get_setting(key, default=None):
    row = ForumSetting.query.filter_by(key=key).first()
    return row.value if row else default


def set_setting(key, value):
    row = ForumSetting.query.filter_by(key=key).first()
    if not row:
        row = ForumSetting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
    row.updated_at = datetime.utcnow()
    db.session.commit()
    return row


def allow_student_creation():
    return (get_setting('allow_student_forum_creation', 'true') or 'true').lower() in ('1', 'true', 'yes')


# ============================================================
# RATE LIMIT & IDEMPOTENCY (in-memory, single process dev)
# ============================================================

_RATE = {}
_IDEMPOTENCY = {}
POST_LIMIT = 5
POST_WINDOW = 60
IDEM_TTL = 300


def check_rate_limit(user_id):
    now = time.time()
    window = [t for t in _RATE.get(user_id, []) if now - t < POST_WINDOW]
    if len(window) >= POST_LIMIT:
        return False
    window.append(now)
    _RATE[user_id] = window
    return True


def check_idempotency(user_id, request_id):
    if not request_id:
        return True
    key = f'{user_id}:{request_id}'
    if key in _IDEMPOTENCY:
        return False
    _IDEMPOTENCY[key] = time.time() + IDEM_TTL
    if len(_IDEMPOTENCY) > 2000:
        for k, exp in list(_IDEMPOTENCY.items()):
            if exp < time.time():
                del _IDEMPOTENCY[k]
    return True


# ============================================================
# XP & ACHIEVEMENTS (backend-computed only)
# ============================================================

SPAM_SHORT = {'ok', 'iya', 'ya', 'y', 'setuju', 'sepakat', 'haha', 'hehe', 'wkwk', 'lol', 'j', 'gj', 'ga', 'g', 'hmm', 'mantap', 'nice'}


def _xp_row(user_id):
    row = UserXp.query.filter_by(user_id=user_id).first()
    if not row:
        row = UserXp(user_id=user_id, xp=0, level=1)
        db.session.add(row)
        db.session.flush()
    return row


def _level_from_xp(xp):
    return 1 + xp // 100


def award_xp(user_id, source, points, ref_type, ref_id):
    """Idempotent XP award. Only meaningful content awards points (checked by caller)."""
    if points <= 0:
        return None
    existing = XpLog.query.filter_by(source=source, ref_type=ref_type, ref_id=ref_id).first()
    if existing:
        return existing
    try:
        row = _xp_row(user_id)
        row.xp = (row.xp or 0) + points
        row.level = _level_from_xp(row.xp)
        row.updated_at = datetime.utcnow()
        log = XpLog(user_id=user_id, source=source, points=points, ref_type=ref_type, ref_id=ref_id)
        db.session.add(log)
        db.session.commit()
        return log
    except Exception:
        db.session.rollback()
        return None


ACHIEVEMENT_DEFS = [
    ('discussion-starter', '💬 Discussion Starter', 'Membuat forum pertama.', 'mdi:forum-plus-outline'),
    ('curious-learner', '❓ Curious Learner', 'Membuat 10 pertanyaan.', 'mdi:comment-question-outline'),
    ('collaborative-learner', '🤝 Collaborative Learner', 'Memberikan 20 reply.', 'mdi:handshake-outline'),
    ('best-answer', '⭐ Best Answer', 'Jawaban ditandai sebagai Best Answer.', 'mdi:star-circle-outline'),
    ('great-presenter', '🎤 Great Presenter', 'Menyelesaikan forum presentasi.', 'mdi:microphone-outline'),
]


def _ensure_achievements():
    for code, label, desc, icon in ACHIEVEMENT_DEFS:
        if not Achievement.query.filter_by(code=code).first():
            db.session.add(Achievement(code=code, label=label, description=desc, icon=icon))
    db.session.commit()


def _count(model, user_id, **filters):
    return model.query.filter_by(user_id=user_id, **filters).count()


def evaluate_achievements(user_id):
    _ensure_achievements()
    from src.models.forum import Forum, ForumPost
    awarded = []
    forum_count = Forum.query.filter_by(created_by=user_id).count()
    question_count = ForumQuestion.query.filter_by(questioner_id=user_id).count()
    reply_count = ForumPost.query.filter_by(author_id=user_id, post_type='reply').count()
    best_count = ForumPost.query.filter_by(author_id=user_id, is_best_answer=True).count()

    checks = [
        ('discussion-starter', forum_count >= 1),
        ('curious-learner', question_count >= 10),
        ('collaborative-learner', reply_count >= 20),
        ('best-answer', best_count >= 1),
    ]
    # great-presenter: presenter (member) of at least one presentation forum
    presented = ForumMember.query.filter_by(user_id=user_id, role='presenter').all()
    if presented:
        closed_presentations = [m for m in presented if m.forum.type == 'PRESENTATION' and m.forum.status in ('CLOSED', 'ARCHIVED')]
        checks.append(('great-presenter', len(closed_presentations) >= 1))

    for code, ok in checks:
        if not ok:
            continue
        ach = Achievement.query.filter_by(code=code).first()
        if not ach:
            continue
        existing = UserAchievement.query.filter_by(user_id=user_id, achievement_id=ach.id).first()
        if existing:
            continue
        try:
            db.session.add(UserAchievement(user_id=user_id, achievement_id=ach.id))
            db.session.commit()
            awarded.append(ach)
        except Exception:
            db.session.rollback()
    return awarded


def user_stats(user_id):
    from src.models.forum import Forum, ForumPost
    return {
        'forums_created': Forum.query.filter_by(created_by=user_id).count(),
        'questions': ForumQuestion.query.filter_by(questioner_id=user_id).count(),
        'replies': ForumPost.query.filter_by(author_id=user_id, post_type='reply').count(),
        'posts': ForumPost.query.filter_by(author_id=user_id).count(),
        'best_answers': ForumPost.query.filter_by(author_id=user_id, is_best_answer=True).count(),
        'reactions_received': ForumReaction.query.join(ForumPost).filter(ForumPost.author_id == user_id).count(),
        'xp': (UserXp.query.filter_by(user_id=user_id).first().xp if UserXp.query.filter_by(user_id=user_id).first() else 0),
        'level': (UserXp.query.filter_by(user_id=user_id).first().level if UserXp.query.filter_by(user_id=user_id).first() else 1),
    }


# ============================================================
# NOTIFICATIONS
# ============================================================

def notify(user_id, actor_id, notification_type, message, forum_id=None, post_id=None):
    if not user_id:
        return None
    if actor_id and str(actor_id) == str(user_id):
        return None
    try:
        n = Notification(
            user_id=user_id, actor_id=actor_id, notification_type=notification_type,
            message=message, forum_id=forum_id, post_id=post_id,
        )
        db.session.add(n)
        db.session.commit()
        return n
    except Exception:
        db.session.rollback()
        return None


# ============================================================
# LEARNING EVENTS (integrated with existing analytics)
# ============================================================

def log_forum_event(user, forum, event_type, data=None):
    from src.services.learning_analytics_service import log_activity, ALLOWED_EVENT_TYPES
    if event_type not in FORUM_EVENT_TYPES:
        return None
    if not forum.material_id:
        return None
    if event_type not in ALLOWED_EVENT_TYPES:
        return None
    return log_activity(user.id, forum.material_id, event_type,
                        section_id=forum.lesson_id, data=data or {}, silent=True)


# ============================================================
# SERIALIZATION
# ============================================================

def forum_payload(forum, user):
    from src.models.forum import ForumPost, ForumQuestion, ForumReaction
    root_posts = [p for p in forum.posts if p.parent_id is None and p.deleted_at is None and p.post_type in ('post', 'question')]
    replies = [p for p in forum.posts if p.parent_id is not None and p.deleted_at is None]
    questions = [q for q in forum.questions if q.status == 'UNANSWERED']
    reactions_total = 0
    for p in forum.posts:
        reactions_total += len(p.reactions)
    last_activity = None
    for p in forum.posts:
        if p.deleted_at is None:
            ts = p.updated_at or p.created_at
            if last_activity is None or ts > last_activity:
                last_activity = ts
    presenters = [m for m in forum.members if m.role == 'presenter']
    return {
        'id': forum.id,
        'type': forum.type,
        'title': forum.title,
        'description': forum.description,
        'topic': forum.topic,
        'category': forum.category,
        'tags': (forum.tags or '').split(',') if forum.tags else [],
        'pinned_question': forum.pinned_question,
        'course_id': forum.course_id,
        'course_name': forum.course.name if forum.course else None,
        'material_id': forum.material_id,
        'material_title': forum.material.title if forum.material else None,
        'lesson_id': forum.lesson_id,
        'lesson_title': forum.lesson.title if forum.lesson else None,
        'created_by': forum.created_by,
        'author_name': forum.creator.name if forum.creator else 'Unknown',
        'visibility': forum.visibility,
        'status': forum.status,
        'start_at': forum.start_at.isoformat() + 'Z' if forum.start_at else None,
        'end_at': forum.end_at.isoformat() + 'Z' if forum.end_at else None,
        'is_pinned': forum.is_pinned,
        'created_at': forum.created_at.isoformat() + 'Z' if forum.created_at else None,
        'updated_at': forum.updated_at.isoformat() + 'Z' if forum.updated_at else None,
        # presentation
        'presentation_group_name': forum.presentation_group_name,
        'presenter_id': forum.presenter_id,
        'presenter_name': forum.presenter.name if forum.presenter else None,
        'presentation_file_url': storage_service.out_url(forum.presentation_file_url),
        'presentation_file_name': forum.presentation_file_name,
        'presentation_video_url': storage_service.out_url(forum.presentation_video_url),
        'presentation_video_name': forum.presentation_video_name,
        'presenter_question_enabled': forum.presenter_question_enabled,
        'presenters': [{'id': m.user_id, 'name': m.user.name} for m in presenters],
        # stats
        'posts_count': len(root_posts),
        'replies_count': len(replies),
        'questions_count': len(forum.questions),
        'unanswered_questions_count': len(questions),
        'reactions_count': reactions_total,
        'participants_count': len({p.author_id for p in forum.posts if p.deleted_at is None}),
        'last_activity': last_activity.isoformat() + 'Z' if last_activity else None,
        # perms
        'can_manage': can_manage_forum(forum, user),
        'can_post': can_post_in_forum(forum, user),
        'can_view': can_view_forum(forum, user),
        'is_presenter': is_presenter(forum, user),
        'is_teacher': is_teacher(user),
    }


def post_payload(post, user, include_replies=False, depth=0):
    my_reaction = next((r for r in post.reactions if r.user_id == user.id), None)
    feedback = ForumFeedback.query.filter_by(post_id=post.id).first() if include_replies or post.post_type != 'reply' else None
    question = ForumQuestion.query.filter_by(post_id=post.id).first()
    answer = None
    if question and question.answer:
        answer = question.answer
    is_deleted = post.deleted_at is not None
    base = {
        'id': post.id,
        'forum_id': post.forum_id,
        'author_id': post.author_id,
        'author_name': post.author.name if post.author else 'Unknown',
        'author_role': post.author.role if post.author else None,
        'parent_id': post.parent_id,
        'content': '' if is_deleted else post.content,
        'post_type': post.post_type,
        'quoted_post_id': post.quoted_post_id,
        'quoted_content': post.quoted_post.content if (post.quoted_post and not post.quoted_post.deleted_at and not is_deleted) else None,
        'is_pinned': post.is_pinned,
        'is_best_answer': post.is_best_answer,
        'is_deleted': is_deleted,
        'edited': post.edited_at is not None,
        'edited_at': post.edited_at.isoformat() + 'Z' if post.edited_at else None,
        'created_at': post.created_at.isoformat() + 'Z' if post.created_at else None,
        'reactions': {r.reaction_type: len([x for x in post.reactions if x.reaction_type == r.reaction_type]) for r in post.reactions},
        'my_reaction': my_reaction.reaction_type if my_reaction else None,
        'reaction_total': len(post.reactions),
        'mentions': [m.mentioned_user_id for m in post.mentions],
        'attachments': [{
            'id': a.id, 'original_name': a.original_name, 'file_name': a.file_name,
            'file_size': a.file_size, 'file_type': a.file_type,
            'file_url': storage_service.out_url(a.file_url),
        } for a in post.attachments],
        'feedback': {
            'teacher_id': feedback.teacher_id,
            'teacher_name': feedback.teacher.name if feedback and feedback.teacher else None,
            'feedback': feedback.feedback if feedback else None,
            'created_at': feedback.created_at.isoformat() + 'Z' if feedback and feedback.created_at else None,
        } if feedback else None,
        'question': {
            'id': question.id,
            'status': question.status,
            'answered_at': question.answered_at.isoformat() + 'Z' if question and question.answered_at else None,
            'answer': {
                'presenter_id': answer.presenter_id if answer else None,
                'presenter_name': answer.presenter.name if answer and answer.presenter else None,
                'answer_post_id': answer.answer_post_id if answer else None,
            } if answer else None,
        } if question else None,
        'can_edit': (not is_deleted) and str(post.author_id) == str(user.id) and
                    (not post.edited_at or (datetime.utcnow() - (post.edited_at or post.created_at)).total_seconds() < 900),
        'can_delete': (not is_deleted) and (str(post.author_id) == str(user.id) or can_manage_forum(post.forum, user)),
        'can_pin': (not is_deleted) and is_teacher(user) and can_manage_forum(post.forum, user),
        'can_feedback': (not is_deleted) and is_teacher(user) and can_manage_forum(post.forum, user),
        'can_best_answer': (not is_deleted) and is_teacher(user) and can_manage_forum(post.forum, user),
        'can_report': (not is_deleted) and str(post.author_id) != str(user.id),
        'children_count': len([c for c in post.children if c.deleted_at is None]),
    }
    if include_replies and depth < 2:
        replies = sorted([c for c in post.children if c.deleted_at is None], key=lambda x: x.created_at)
        base['replies'] = [post_payload(r, user, include_replies=True, depth=depth + 1) for r in replies]
    return base
