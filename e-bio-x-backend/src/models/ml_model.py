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

    # Which class this model belongs to.
    #
    # NULL = pooled model trained from every student in the system. It is
    # only a fallback for classes too small to train their own, and any
    # readout that uses it says so explicitly.
    #
    # A teacher id = the model was trained from that teacher's students
    # only, so their class numbers describe their own class.
    #
    # No foreign key: ml_models rows outlive teacher accounts in practice,
    # and a hard FK would block deleting a teacher. Intentionally a plain
    # integer.
    teacher_id = db.Column(db.Integer, nullable=True, index=True)

    @property
    def is_pooled(self):
        return self.teacher_id is None

    def __repr__(self):
        scope = 'pooled' if self.is_pooled else f'teacher={self.teacher_id}'
        return f'<MlModel {self.model_type} v{self.model_version} {scope}>'