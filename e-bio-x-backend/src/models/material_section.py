from src.config.database import db
from datetime import datetime

class MaterialSection(db.Model):
    __tablename__ = 'material_sections'

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    contents = db.relationship('MaterialContent', backref='section', lazy=True, cascade="all, delete-orphan", order_by="MaterialContent.position")

    def __repr__(self):
        return f'<MaterialSection {self.title}>'