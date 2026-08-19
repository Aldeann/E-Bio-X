from src.config.database import db
from datetime import datetime

class StudentNote(db.Model):
    __tablename__ = 'student_notes'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=True)
    content_id = db.Column(db.Integer, db.ForeignKey('material_contents.id'), nullable=True)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('student_notes', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('student_notes', lazy=True, cascade="all, delete-orphan"))
    section = db.relationship('MaterialSection', backref=db.backref('student_notes', lazy=True))
    content = db.relationship('MaterialContent', backref=db.backref('student_notes', lazy=True))

    def __repr__(self):
        return f'<StudentNote {self.material_id} - {self.student_id}>'