from src.config.database import db
from datetime import datetime

class QuestionBank(db.Model):
    __tablename__ = 'question_bank'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), nullable=False, default='multiple_choice')
    topic = db.Column(db.String(150), nullable=True)
    difficulty = db.Column(db.String(10), nullable=False, default='medium')
    explanation = db.Column(db.Text, nullable=True)
    points = db.Column(db.Integer, nullable=False, default=10)
    image_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    teacher = db.relationship('User', backref=db.backref('question_bank', lazy=True))
    options = db.relationship('QuestionBankOption', backref='bank_question', lazy=True, cascade="all, delete-orphan", order_by="QuestionBankOption.order_index")

    def __repr__(self):
        return f'<QuestionBank {self.id}>'