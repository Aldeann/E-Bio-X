from src.config.database import db
from datetime import datetime


class VideoProgress(db.Model):
    __tablename__ = 'video_progress'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('material_contents.id'), nullable=False)
    video_duration = db.Column(db.Float, nullable=False, default=0)
    watched_duration = db.Column(db.Float, nullable=False, default=0)
    last_position = db.Column(db.Float, nullable=False, default=0)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('video_progress', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('video_progress', lazy=True, cascade="all, delete-orphan"))
    content = db.relationship('MaterialContent', backref=db.backref('video_progress', lazy=True))

    __table_args__ = (db.UniqueConstraint('student_id', 'content_id', name='uq_student_video_progress'),)

    def __repr__(self):
        return f'<VideoProgress {self.student_id} - content {self.content_id}>'