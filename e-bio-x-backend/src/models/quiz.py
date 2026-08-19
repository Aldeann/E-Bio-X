from src.config.database import db
from datetime import datetime

class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=True)
    duration = db.Column(db.Integer, nullable=True)
    passing_grade = db.Column(db.Integer, nullable=False, default=75)
    max_attempts = db.Column(db.Integer, nullable=False, default=1)
    shuffle_questions = db.Column(db.Boolean, nullable=False, default=False)
    shuffle_options = db.Column(db.Boolean, nullable=False, default=False)
    show_explanation = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_closed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    course = db.relationship('Course', backref=db.backref('quizzes', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('quizzes', lazy=True, cascade="all, delete-orphan"))
    section = db.relationship('MaterialSection', backref=db.backref('quizzes', lazy=True))
    creator = db.relationship('User', foreign_keys=[created_by], backref=db.backref('created_quizzes', lazy=True))
    submissions = db.relationship('Submission', backref='quiz', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Quiz {self.title}>'
