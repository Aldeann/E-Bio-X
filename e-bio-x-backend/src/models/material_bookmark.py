from src.config.database import db
from datetime import datetime

class MaterialBookmark(db.Model):
    __tablename__ = 'material_bookmarks'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=True)
    content_id = db.Column(db.Integer, db.ForeignKey('material_contents.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('material_bookmarks', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('bookmarks', lazy=True, cascade="all, delete-orphan"))
    section = db.relationship('MaterialSection', backref=db.backref('bookmarks', lazy=True))
    content = db.relationship('MaterialContent', backref=db.backref('bookmarks', lazy=True))

    __table_args__ = (db.UniqueConstraint('student_id', 'material_id', 'section_id', 'content_id', name='uq_student_material_section_content_bookmark'),)

    def __repr__(self):
        return f'<MaterialBookmark {self.material_id} - {self.student_id}>'