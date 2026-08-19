from src.config.database import db
from datetime import datetime
import json

class MaterialContent(db.Model):
    __tablename__ = 'material_contents'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    data = db.Column(db.JSON, nullable=True)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<MaterialContent {self.type}>'