from src.config.database import db
from datetime import datetime

class MaterialStudentState(db.Model):
    __tablename__ = 'material_student_state'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    last_section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=True)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    last_accessed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    material = db.relationship('Material', backref=db.backref('student_states', lazy=True, cascade="all, delete-orphan"))
    student = db.relationship('User', backref=db.backref('material_student_states', lazy=True))
    last_section = db.relationship('MaterialSection', backref=db.backref('student_states', lazy=True))

    __table_args__ = (db.UniqueConstraint('material_id', 'student_id', name='uq_student_material_state'),)

    def __repr__(self):
        return f'<MaterialStudentState {self.material_id} - {self.student_id}>'