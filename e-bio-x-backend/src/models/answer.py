from src.config.database import db
from datetime import datetime

class Answer(db.Model):
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    option_id = db.Column(db.Integer, db.ForeignKey('options.id'), nullable=True)
    answer_text = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)
    points_earned = db.Column(db.Float, nullable=False, default=0)
    answered_at = db.Column(db.DateTime, nullable=True)

    question = db.relationship('Question', backref=db.backref('answers', lazy=True, cascade="all, delete-orphan"))
    option = db.relationship('Option', backref=db.backref('answers', lazy=True, cascade="all, delete-orphan"))
    student = db.relationship('User', backref=db.backref('answers', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Answer {self.id}>'