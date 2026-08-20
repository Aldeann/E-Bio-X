from src.config.database import db
from datetime import datetime


class TopicKnowledge(db.Model):
    __tablename__ = 'topic_knowledge'

    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(150), nullable=False, default='umum')
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    subject = db.Column(db.String(100), nullable=True)

    # aggregated knowledge "brain" content
    key_concept = db.Column(db.Text, nullable=True)
    correct_answer_explanation = db.Column(db.Text, nullable=True)
    misconception = db.Column(db.Text, nullable=True)
    recommended_material = db.Column(db.Text, nullable=True)

    # provenance
    source_material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=True)
    source_count = db.Column(db.Integer, nullable=False, default=1)
    approved_count = db.Column(db.Integer, nullable=False, default=0)
    usage_count = db.Column(db.Integer, nullable=False, default=0)
    last_used_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('ix_tk_topic', 'topic', 'course_id'),
        db.Index('ix_tk_course', 'course_id'),
    )

    def __repr__(self):
        return f'<TopicKnowledge {self.topic} course={self.course_id}>'