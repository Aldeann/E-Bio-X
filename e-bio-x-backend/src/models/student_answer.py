from src.config.database import db
from datetime import datetime

class StudentAnswer(db.Model):
    __tablename__ = 'student_answers'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=False)
    content_id = db.Column(db.Integer, db.ForeignKey('material_contents.id'), nullable=False)
    selected_answer = db.Column(db.Integer, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    question_index = db.Column(db.Integer, nullable=True)
    answered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('material_answers', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('student_answers', lazy=True, cascade="all, delete-orphan"))
    section = db.relationship('MaterialSection', backref=db.backref('student_answers', lazy=True))
    content = db.relationship('MaterialContent', backref=db.backref('student_answers', lazy=True))

    def __repr__(self):
        return f'<StudentAnswer {self.material_id} - {self.student_id}>'