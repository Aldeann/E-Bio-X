from src.config.database import db
from datetime import datetime


class LearningSession(db.Model):
    __tablename__ = 'learning_sessions'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=True)
    ended_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='active')

    student = db.relationship('User', backref=db.backref('learning_sessions', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('learning_sessions', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<LearningSession {self.id} - student {self.student_id} material {self.material_id}>'