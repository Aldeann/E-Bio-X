from src.config.database import db
from datetime import datetime


class LearningActivity(db.Model):
    __tablename__ = 'learning_activities'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=True)
    content_id = db.Column(db.Integer, db.ForeignKey('material_contents.id'), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    data = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('learning_activities', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('learning_activities', lazy=True, cascade="all, delete-orphan"))
    section = db.relationship('MaterialSection', backref=db.backref('learning_activities', lazy=True))
    content = db.relationship('MaterialContent', backref=db.backref('learning_activities', lazy=True))

    def __repr__(self):
        return f'<LearningActivity {self.id} {self.event_type} - {self.student_id}>'