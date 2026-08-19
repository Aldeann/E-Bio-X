from src.config.database import db
from datetime import datetime

class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=True)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), nullable=False, default='multiple_choice')
    difficulty = db.Column(db.String(10), nullable=False, default='medium')
    explanation = db.Column(db.Text, nullable=True)
    points = db.Column(db.Integer, nullable=False, default=10)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    bank_question_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    quiz = db.relationship('Quiz', backref=db.backref('questions', lazy=True, cascade="all, delete-orphan", order_by="Question.order_index"))
    bank_question = db.relationship('QuestionBank', backref=db.backref('quiz_questions', lazy=True))

    def __repr__(self):
        return f'<Question {self.id}>'
