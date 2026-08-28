from src.config.database import db
from datetime import datetime


class StudentContentTrack(db.Model):
    __tablename__ = 'student_content_track'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('material_contents.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    view_count = db.Column(db.Integer, nullable=False, default=1)

    student = db.relationship('User', backref=db.backref('content_tracks', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('content_tracks', lazy=True, cascade="all, delete-orphan"))
    content = db.relationship('MaterialContent', backref=db.backref('content_tracks', lazy=True, cascade="all, delete-orphan"))

    __table_args__ = (db.UniqueConstraint('student_id', 'content_id', name='uq_student_content_track'),)

    def __repr__(self):
        return f'<StudentContentTrack {self.student_id} - content {self.content_id}>'