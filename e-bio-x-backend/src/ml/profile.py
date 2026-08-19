# ============================================================
# TAHAP 5 - Student learning profile.
#
# Combines Decision Tree mastery classification + K-Means group into
# ONE profile for a student. Never exposes raw cluster numbers to the
# student UI unnecessarily.
# ============================================================
from datetime import datetime

from src.config.database import db
from src.models.student_learning_profile import StudentLearningProfile
from src.ml import ml_config as cfg
from src.ml import feature_service
from src.ml import decision_tree
from src.ml import kmeans as kmeans_mod
from src.ml import cluster_interpreter


def _readable_summary(row):
    return {
        'progress_percent': round((row.get('material_completion_rate') or 0.0) * 100, 1),
        'quiz_average': round((row.get('quiz_average') or 0.0) * 100, 1),
        'quiz_best': round((row.get('quiz_best_score') or 0.0) * 100, 1),
        'accuracy': round((row.get('interactive_accuracy') or 0.0) * 100, 1),
        'learning_minutes': round(row.get('learning_minutes') or 0.0, 1),
        'quiz_attempts': row.get('quiz_attempts') or 0,
        'correct_rate': round((row.get('correct_rate') or 0.0) * 100, 1),
        'section_completion': round((row.get('section_completion_rate') or 0.0) * 100, 1),
    }


def generate_profile(student, dt_artifact=None, km_artifact=None):
    """Generate + persist the student learning profile.

    Returns a dict with status READY / INSUFFICIENT_DATA / MODEL_UNAVAILABLE.
    """
    row = feature_service.aggregate_student_features(student)
    if row is None:
        return {'status': cfg.STATUS_INSUFFICIENT,
                'message': 'Belum cukup data untuk menentukan profil belajar.',
                'hint': 'Mulai belajar untuk mendapatkan rekomendasi yang lebih sesuai.'}

    if dt_artifact is None or dt_artifact.get('model') is None:
        return {'status': cfg.STATUS_MODEL_UNAVAILABLE,
                'message': 'Model penguasaan belum tersedia.',
                'hint': 'Rekomendasi personal sedang tidak tersedia.'}

    label = decision_tree.predict_row(row, dt_artifact)[0]
    if label is None:
        return {'status': cfg.STATUS_MODEL_UNAVAILABLE,
                'message': 'Model penguasaan belum tersedia.',
                'hint': 'Rekomendasi personal sedang tidak tersedia.'}

    factors = decision_tree.explain(row, dt_artifact, label)
    cluster_id = kmeans_mod.assign_cluster(row, km_artifact) if km_artifact else None
    cluster_label = None
    if cluster_id is not None and km_artifact:
        for prof in cluster_interpreter.interpret_clusters(km_artifact):
            if prof['cluster_id'] == cluster_id:
                cluster_label = prof['label']
                break

    profile = {
        'status': cfg.STATUS_READY,
        'mastery_level': label,
        'mastery_label': cfg.MASTERY_UI.get(label, label),
        'cluster_id': cluster_id,
        'cluster_label': cluster_label,
        'factors': factors,
        'summary': _readable_summary(row),
        'model_version': (dt_artifact.get('_meta') or {}).get('model_version'),
        'message': _profile_message(cluster_label),
    }
    _persist(student.id, profile, row)
    return profile


def _persist(student_id, profile, row):
    record = StudentLearningProfile.query.filter_by(student_id=student_id).first()
    if record is None:
        record = StudentLearningProfile(student_id=student_id)
        db.session.add(record)
    record.mastery_level = profile['mastery_level']
    record.cluster_id = profile['cluster_id']
    record.cluster_label = profile['cluster_label']
    record.profile_data_json = {
        'summary': profile['summary'],
        'factors': profile['factors'],
        'features': row,
    }
    record.model_version = profile.get('model_version')
    record.generated_at = datetime.utcnow()
    record.updated_at = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def _profile_message(cluster_label):
    friendly = {
        'High Achievement': 'Profil belajar Anda menunjukkan pemahaman yang baik dan konsisten.',
        'Active Learner': 'Profil belajar Anda menunjukkan pola belajar aktif.',
        'Moderate Learner': 'Profil belajar Anda berada pada tingkat menengah — terus tingkatkan.',
        'Needs Support': 'Profil belajar Anda menunjukkan bahwa Anda masih membutuhkan penguatan.',
        'Low Activity': 'Mulai belajar secara rutin agar profil belajar Anda semakin jelas.',
    }
    return friendly.get(cluster_label, '')