from src.config.database import db
from datetime import datetime


class Forum(db.Model):
    __tablename__ = 'forums'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum('GENERAL_DISCUSSION', 'PRESENTATION', 'QUESTION_ANSWER', 'CASE_STUDY', name='forum_type'), nullable=False, default='GENERAL_DISCUSSION')
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    topic = db.Column(db.String(150), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.String(255), nullable=True)
    pinned_question = db.Column(db.Text, nullable=True)

    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    visibility = db.Column(db.Enum('PRIVATE', 'CLASS', 'COURSE', name='forum_visibility'), nullable=False, default='COURSE')
    status = db.Column(db.Enum('DRAFT', 'SCHEDULED', 'ACTIVE', 'CLOSED', 'ARCHIVED', name='forum_status'), nullable=False, default='DRAFT')

    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)

    # PRESENTATION fields
    presentation_group_name = db.Column(db.String(100), nullable=True)
    presenter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    presentation_file_url = db.Column(db.String(255), nullable=True)
    presentation_file_name = db.Column(db.String(255), nullable=True)
    presentation_video_url = db.Column(db.String(255), nullable=True)
    presentation_video_name = db.Column(db.String(255), nullable=True)
    presenter_question_enabled = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    creator = db.relationship('User', foreign_keys=[created_by], backref=db.backref('forums_created', lazy=True))
    presenter = db.relationship('User', foreign_keys=[presenter_id], backref=db.backref('forums_presented', lazy=True))
    course = db.relationship('Course', backref=db.backref('forums', lazy=True))
    material = db.relationship('Material', backref=db.backref('forums', lazy=True))
    lesson = db.relationship('MaterialSection', backref=db.backref('forums', lazy=True))
    members = db.relationship('ForumMember', backref='forum', lazy=True, cascade="all, delete-orphan")
    posts = db.relationship('ForumPost', backref='forum', lazy=True, cascade="all, delete-orphan", foreign_keys='ForumPost.forum_id')
    questions = db.relationship('ForumQuestion', backref='forum', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Forum {self.id} {self.title}>'


class ForumMember(db.Model):
    __tablename__ = 'forum_members'
    __table_args__ = (db.UniqueConstraint('forum_id', 'user_id', name='uq_forum_member'),)

    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.Enum('presenter', 'member', name='forum_member_role'), nullable=False, default='member')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('forum_memberships', lazy=True))


class ForumPost(db.Model):
    __tablename__ = 'forum_posts'

    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    post_type = db.Column(db.Enum('post', 'reply', 'question', 'answer', 'system', name='forum_post_type'), nullable=False, default='post')
    quoted_post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)
    is_best_answer = db.Column(db.Boolean, nullable=False, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    edited_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    author = db.relationship('User', foreign_keys=[author_id], backref=db.backref('forum_posts', lazy=True))
    parent = db.relationship('ForumPost', remote_side=[id], foreign_keys='ForumPost.parent_id', backref=db.backref('children', lazy=True))
    quoted_post = db.relationship('ForumPost', remote_side=[id], foreign_keys=[quoted_post_id])
    reactions = db.relationship('ForumReaction', backref='post', lazy=True, cascade="all, delete-orphan")
    mentions = db.relationship('ForumMention', backref='post', lazy=True, cascade="all, delete-orphan")
    attachments = db.relationship('ForumAttachment', backref='post', lazy=True, cascade="all, delete-orphan")

    __table_args__ = (
        db.Index('ix_forum_posts_forum_id', 'forum_id'),
        db.Index('ix_forum_posts_author_id', 'author_id'),
        db.Index('ix_forum_posts_parent_id', 'parent_id'),
        db.Index('ix_forum_posts_created_at', 'created_at'),
    )

    def __repr__(self):
        return f'<ForumPost {self.id}>'


class ForumReaction(db.Model):
    __tablename__ = 'forum_reactions'
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='uq_forum_reaction'),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reaction_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('forum_reactions', lazy=True))


class ForumMention(db.Model):
    __tablename__ = 'forum_mentions'
    __table_args__ = (db.UniqueConstraint('post_id', 'mentioned_user_id', name='uq_forum_mention'),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    mentioned_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    mentioned_user = db.relationship('User', backref=db.backref('forum_mentions', lazy=True))


class ForumAttachment(db.Model):
    __tablename__ = 'forum_attachments'

    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    file_type = db.Column(db.String(50), nullable=True)
    file_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    author = db.relationship('User', backref=db.backref('forum_attachments', lazy=True))


class ForumQuestion(db.Model):
    __tablename__ = 'forum_questions'
    __table_args__ = (db.UniqueConstraint('post_id', name='uq_forum_question_post'),)

    id = db.Column(db.Integer, primary_key=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    questioner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    presenter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.Enum('UNANSWERED', 'ANSWERED', name='forum_question_status'), nullable=False, default='UNANSWERED')
    answered_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    post = db.relationship('ForumPost', backref=db.backref('question_link', uselist=False))
    questioner = db.relationship('User', foreign_keys=[questioner_id], backref=db.backref('forum_questions', lazy=True))
    presenter = db.relationship('User', foreign_keys=[presenter_id])
    answer = db.relationship('ForumAnswer', backref='question', uselist=False, cascade="all, delete-orphan")


class ForumAnswer(db.Model):
    __tablename__ = 'forum_answers'
    __table_args__ = (db.UniqueConstraint('question_id', name='uq_forum_answer_question'),)

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('forum_questions.id'), nullable=False)
    presenter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    answer_post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    presenter = db.relationship('User', backref=db.backref('forum_answers', lazy=True))
    answer_post = db.relationship('ForumPost', backref=db.backref('answer_link', uselist=False))


class ForumFeedback(db.Model):
    __tablename__ = 'forum_feedback'
    __table_args__ = (db.UniqueConstraint('post_id', name='uq_forum_feedback_post'),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    teacher = db.relationship('User', backref=db.backref('forum_feedback', lazy=True))


class ForumReport(db.Model):
    __tablename__ = 'forum_reports'
    __table_args__ = (db.UniqueConstraint('post_id', 'reported_by', name='uq_forum_report'),)

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum('PENDING', 'REVIEWED', 'DISMISSED', 'ACTION_TAKEN', name='forum_report_status'), nullable=False, default='PENDING')
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    post = db.relationship('ForumPost', backref=db.backref('reports', lazy=True))
    reporter = db.relationship('User', foreign_keys=[reported_by], backref=db.backref('forum_reports', lazy=True))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])


class ForumModerationLog(db.Model):
    __tablename__ = 'forum_moderation_logs'

    id = db.Column(db.Integer, primary_key=True)
    moderator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    moderator = db.relationship('User', backref=db.backref('forum_moderation_logs', lazy=True))


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notification_type = db.Column(db.String(40), nullable=False)
    forum_id = db.Column(db.Integer, db.ForeignKey('forums.id'), nullable=True)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', lazy=True))
    actor = db.relationship('User', foreign_keys=[actor_id])

    __table_args__ = (
        db.Index('ix_notifications_user', 'user_id'),
    )


class UserXp(db.Model):
    __tablename__ = 'user_xp'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    xp = db.Column(db.Integer, nullable=False, default=0)
    level = db.Column(db.Integer, nullable=False, default=1)
    updated_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('xp', uselist=False))


class XpLog(db.Model):
    __tablename__ = 'xp_logs'
    __table_args__ = (db.UniqueConstraint('source', 'ref_type', 'ref_id', name='uq_xp_log'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    source = db.Column(db.String(40), nullable=False)
    points = db.Column(db.Integer, nullable=False, default=0)
    ref_type = db.Column(db.String(40), nullable=False)
    ref_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('xp_logs', lazy=True))


class Achievement(db.Model):
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(60), nullable=False, unique=True)
    label = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(60), nullable=True)


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    awarded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('achievements', lazy=True))
    achievement = db.relationship('Achievement')


class ForumSetting(db.Model):
    __tablename__ = 'forum_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
