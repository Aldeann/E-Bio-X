from src.config.database import db
from datetime import datetime

class DiscussionThread(db.Model):
    __tablename__ = 'discussion_threads'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    course = db.relationship('Course', backref=db.backref('discussion_threads', lazy=True, cascade="all, delete-orphan"))
    author = db.relationship('User', backref=db.backref('discussion_threads', lazy=True, cascade="all, delete-orphan"))
    replies = db.relationship('DiscussionReply', backref='thread', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<DiscussionThread {self.title}>'

class DiscussionReply(db.Model):
    __tablename__ = 'discussion_replies'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('discussion_threads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    author = db.relationship('User', backref=db.backref('discussion_replies', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<DiscussionReply {self.id}>'
