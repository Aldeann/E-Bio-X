from src.config.database import db
from datetime import datetime

# Practice-question lifecycle (Fase 3).
#
# source = who wrote it. status = whether a teacher has reviewed it.
# Only APPROVED rows may ever be served to students as practice, so an AI
# draft stays invisible until a teacher decides otherwise.
BANK_SOURCES = ('teacher', 'ai')
BANK_STATUSES = ('DRAFT', 'APPROVED', 'REJECTED')


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

    # Material section this question practices (Fase 3). NULL = not tagged.
    # Set explicitly by the teacher, never inferred from the topic string.
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=True)

    # Review trail for AI drafts.
    source = db.Column(db.String(20), nullable=False, default='teacher')
    status = db.Column(db.String(20), nullable=False, default='APPROVED')
    generated_by = db.Column(db.String(20), nullable=True)
    model_name = db.Column(db.String(100), nullable=True)
    prompt_version = db.Column(db.String(20), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    misconception = db.Column(db.Text, nullable=True)

    teacher = db.relationship(
        'User',
        foreign_keys=[teacher_id],
        backref=db.backref('question_bank', lazy=True),
    )
    section = db.relationship('MaterialSection', backref=db.backref('bank_questions', lazy=True))
    reviewer = db.relationship(
        'User',
        foreign_keys=[reviewed_by],
        backref=db.backref('reviewed_bank_questions', lazy=True),
    )
    options = db.relationship('QuestionBankOption', backref='bank_question', lazy=True, cascade="all, delete-orphan", order_by="QuestionBankOption.order_index")

    def __repr__(self):
        return f'<QuestionBank {self.id}>'