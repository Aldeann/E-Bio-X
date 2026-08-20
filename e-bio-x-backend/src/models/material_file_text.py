from src.config.database import db
from datetime import datetime


class MaterialFileText(db.Model):
    __tablename__ = 'material_file_texts'

    id = db.Column(db.Integer, primary_key=True)
    material_file_id = db.Column(db.Integer, db.ForeignKey('material_files.id'), nullable=False, unique=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    content = db.Column(db.Text, nullable=True)
    chars = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<MaterialFileText file={self.material_file_id} chars={self.chars}>'