from src.config.database import db
from datetime import datetime

class MaterialProgress(db.Model):
    __tablename__ = 'material_progress'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    completed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    material = db.relationship('Material', backref=db.backref('progress', lazy=True, cascade="all, delete-orphan"))
    section = db.relationship('MaterialSection', backref=db.backref('progress', lazy=True, cascade="all, delete-orphan"))
    student = db.relationship('User', backref=db.backref('material_progress', lazy=True))

    __table_args__ = (db.UniqueConstraint('material_id', 'section_id', 'student_id', name='uq_material_section_student'),)

    def __repr__(self):
        return f'<MaterialProgress {self.material_id} - {self.student_id}>'