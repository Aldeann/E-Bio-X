from src.config.database import db
from datetime import datetime


class QuizExplanation(db.Model):
    __tablename__ = 'quiz_explanations'

    id = db.Column(db.Integer, primary_key=True)

    # target: quiz question (questions.id) and/or bank question (question_bank.id)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=True)
    bank_question_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=True)

    # personal variant support (nullable = global explanation)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    student_answer = db.Column(db.String(10), nullable=True)

    # structured explanation fields (BAGIAN F)
    summary = db.Column(db.Text, nullable=True)
    correct_answer_explanation = db.Column(db.Text, nullable=True)
    student_answer_analysis = db.Column(db.Text, nullable=True)
    option_explanations = db.Column(db.JSON, nullable=True)
    key_concept = db.Column(db.Text, nullable=True)
    misconception = db.Column(db.Text, nullable=True)
    recommended_material = db.Column(db.Text, nullable=True)

    # material linking (BAGIAN E/Y/AF)
    recommended_material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=True)
    source_material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=True)
    source_chunk_id = db.Column(db.Integer, nullable=True)
    material_version = db.Column(db.String(60), nullable=True)

    # lifecycle (BAGIAN K/L/M/N)
    status = db.Column(db.String(30), nullable=False, default='MISSING')
    generated_by = db.Column(db.String(20), nullable=True)  # ai | rule_based | teacher
    model_name = db.Column(db.String(100), nullable=True)
    prompt_version = db.Column(db.String(20), nullable=True)
    explanation_version = db.Column(db.Integer, nullable=False, default=1)
    version_history = db.Column(db.JSON, nullable=True)
    edited_by_teacher = db.Column(db.Boolean, nullable=False, default=False)

    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    # student feedback aggregate (BAGIAN BC/BD)
    feedback_summary = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    question = db.relationship('Question', backref=db.backref('quiz_explanations', lazy=True))
    bank_question = db.relationship('QuestionBank', backref=db.backref('explanations', lazy=True))
    student = db.relationship('User', foreign_keys=[student_id])
    approver = db.relationship('User', foreign_keys=[approved_by])
    recommended_material_rel = db.relationship('Material', foreign_keys=[recommended_material_id])
    source_material_rel = db.relationship('Material', foreign_keys=[source_material_id])

    __table_args__ = (
        db.Index('ix_qe_question', 'question_id'),
        db.Index('ix_qe_bank', 'bank_question_id'),
        db.Index('ix_qe_status', 'status'),
    )

    def snapshot(self):
        return {
            'version': self.explanation_version,
            'status': self.status,
            'generated_by': self.generated_by,
            'edited_by_teacher': self.edited_by_teacher,
            'summary': self.summary,
            'correct_answer_explanation': self.correct_answer_explanation,
            'student_answer_analysis': self.student_answer_analysis,
            'option_explanations': self.option_explanations,
            'key_concept': self.key_concept,
            'misconception': self.misconception,
            'recommended_material': self.recommended_material,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<QuizExplanation {self.id} {self.status}>'
