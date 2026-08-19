from src.config.database import db
from datetime import datetime


class StudentLearningProfile(db.Model):
    __tablename__ = 'student_learning_profiles'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mastery_level = db.Column(db.String(30), nullable=True)
    cluster_id = db.Column(db.Integer, nullable=True)
    cluster_label = db.Column(db.String(50), nullable=True)
    profile_data_json = db.Column(db.JSON, nullable=True)
    model_version = db.Column(db.String(20), nullable=True)
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('learning_profiles', lazy=True))

    __table_args__ = (db.UniqueConstraint('student_id', name='uq_student_learning_profile'),)

    def __repr__(self):
        return f'<StudentLearningProfile student={self.student_id} {self.mastery_level}>'