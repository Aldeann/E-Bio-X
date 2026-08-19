from src.config.database import db

class Option(db.Model):
    __tablename__ = 'options'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    option_text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False, default=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)

    question = db.relationship('Question', backref=db.backref('options', lazy=True, cascade="all, delete-orphan", order_by="Option.order_index"))

    def __repr__(self):
        return f'<Option {self.id}>'
