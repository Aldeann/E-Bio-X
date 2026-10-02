from src.config.database import db
from datetime import datetime


class Recommendation(db.Model):
    __tablename__ = 'recommendations'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    recommendation_score = db.Column(db.Float, nullable=False, default=0.0)
    reason_json = db.Column(db.JSON, nullable=True)
    # 'rule'   = ranked by the transparent REC_WEIGHTS rules (the only
    #            ranker that exists today; no trained model is consulted).
    # 'fallback' = cold-start ordering for students without a profile.
    # 'ml' would only be correct for a genuinely model-driven ranker.
    recommendation_type = db.Column(db.String(20), nullable=False, default='rule')
    # Only meaningful for a model-driven ranker. The rule-based ranker
    # never consults the Decision Tree, so it leaves this NULL instead of
    # implying the tree produced the ordering.
    model_version = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    clicked_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship('User', backref=db.backref('recommendations', lazy=True, cascade="all, delete-orphan"))
    material = db.relationship('Material', backref=db.backref('recommendations', lazy=True))

    def __repr__(self):
        return f'<Recommendation student={self.student_id} material={self.material_id}>'