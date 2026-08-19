from src.config.database import db
from datetime import datetime

class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
    started_at = db.Column(db.DateTime, nullable=True)
    work_time = db.Column(db.Time, nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=True)
    percentage = db.Column(db.Float, nullable=True)
    correct_count = db.Column(db.Integer, nullable=False, default=0)
    wrong_count = db.Column(db.Integer, nullable=False, default=0)
    unanswered_count = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='in_progress')
    cluster = db.Column(db.Integer, nullable=True)

    student = db.relationship('User', backref=db.backref('quiz_results', lazy=True, cascade="all, delete-orphan"))
    answers = db.relationship('Answer', backref='submission', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Submission {self.student_id} - {self.score}>'