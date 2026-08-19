from src.config.database import db
from datetime import datetime


class MlModel(db.Model):
    __tablename__ = 'ml_models'

    id = db.Column(db.Integer, primary_key=True)
    model_type = db.Column(db.String(30), nullable=False)
    model_version = db.Column(db.String(20), nullable=False)
    feature_version = db.Column(db.String(20), nullable=False, default='1.0')
    trained_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    training_sample_count = db.Column(db.Integer, nullable=False, default=0)
    metrics_json = db.Column(db.JSON, nullable=True)
    model_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<MlModel {self.model_type} v{self.model_version}>'