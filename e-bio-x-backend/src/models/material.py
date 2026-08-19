from src.config.database import db
from datetime import datetime

material_courses = db.Table(
    'material_courses',
    db.Column('material_id', db.Integer, db.ForeignKey('materials.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
)

class Material(db.Model):
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(255), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    description = db.Column(db.Text, nullable=True)
    subject = db.Column(db.String(100), nullable=True)
    phase = db.Column(db.String(20), nullable=True)
    class_level = db.Column(db.String(50), nullable=True)
    topic = db.Column(db.String(150), nullable=True)
    learning_objectives = db.Column(db.Text, nullable=True)
    estimated_time = db.Column(db.String(50), nullable=True)
    difficulty = db.Column(db.String(20), nullable=True)
    thumbnail_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='draft')
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)

    course = db.relationship('Course', backref=db.backref('materials', lazy=True, cascade="all, delete-orphan"))
    course_links = db.relationship('Course', secondary=material_courses, backref=db.backref('linked_materials', lazy=True))
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref=db.backref('teacher_materials', lazy=True))
    sections = db.relationship('MaterialSection', backref='material', lazy=True, cascade="all, delete-orphan", order_by="MaterialSection.position")
    files = db.relationship('MaterialFile', backref='material', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Material {self.title}>'