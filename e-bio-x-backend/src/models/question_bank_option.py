from src.config.database import db

class QuestionBankOption(db.Model):
    __tablename__ = 'question_bank_options'

    id = db.Column(db.Integer, primary_key=True)
    bank_question_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=False)
    option_text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f'<QuestionBankOption {self.id}>'