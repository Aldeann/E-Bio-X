# ============================================================
# TAHAP 5 - ML & recommendation API controller.
#
# Privacy rules:
#   - student: only own profile / own recommendations.
#   - teacher/admin: ml analytics scoped to their own students.
#   - training/predict endpoints are teacher/admin protected; students
#     can never trigger training.
# ============================================================
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.enrollment import Enrollment
from src.config.database import db
from src.ml import ml_config as cfg
from src.ml import model_manager, feature_service, decision_tree, kmeans as kmeans_mod
from src.ml import cluster_interpreter, profile as profile_mod, recommendation as rec_service
from src.services import learning_analytics_service as analytics


def _user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _student():
    user = _user()
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    if user.role != 'student':
        return None, (jsonify({'error': 'Endpoint ini khusus siswa'}), 403)
    return user, None


def _teacher():
    user = _user()
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    if user.role not in ('teacher', 'admin'):
        return None, (jsonify({'error': 'Endpoint ini khusus guru'}), 403)
    return user, None


# ============================================================
# STUDENT: learning profile & recommendations
# ============================================================
@jwt_required()
def get_student_learning_profile():
    user, err = _student()
    if err:
        return err
    dt_artifact = model_manager.load_artifact('decision_tree')
    km_artifact = model_manager.load_artifact('kmeans')
    result = profile_mod.generate_profile(user, dt_artifact, km_artifact)
    return jsonify(result), 200


@jwt_required()
def get_student_recommendations():
    user, err = _student()
    if err:
        return err
    dt_artifact = model_manager.load_artifact('decision_tree')
    km_artifact = model_manager.load_artifact('kmeans')
    p = profile_mod.generate_profile(user, dt_artifact, km_artifact)

    if p['status'] == cfg.STATUS_READY and p.get('summary'):
        row = feature_service.aggregate_student_features(user) or {}
        recommended = rec_service.recommend_for_student(
            user, student_row=row, model_version=p.get('model_version'))
        return jsonify({'profile': p, 'status': cfg.STATUS_READY, 'recommendations': recommended}), 200

    fallback = rec_service.fallback_recommendations(user)
    return jsonify({'profile': p, 'status': p['status'],
                    'recommendations': fallback,
                    'mode': 'fallback'}), 200


@jwt_required()
def post_recommendation_click():
    user, err = _student()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    material_id = data.get('material_id')
    if not material_id:
        return jsonify({'error': 'material_id wajib diisi'}), 400
    from src.models.material import Material
    material = Material.query.get(int(material_id))
    if not material or material.status != 'published':
        return jsonify({'error': 'Materi tidak ditemukan atau belum dipublikasikan'}), 404
    try:
        rec_service.mark_clicked(user.id, material.id)
    except Exception:
        db.session.rollback()
    return jsonify({'message': 'Klik rekomendasi tercatat'}), 200


# ============================================================
# TEACHER/ADMIN: ML analytics (scoped to own students)
# ============================================================
def _ml_insights(teacher):
    students = analytics.teacher_student_users(teacher.id)
    if not students:
        empty = {'signals': 0, 'analyzed': 0, 'insufficient_data': 0,
                 'mastery_distribution': {}, 'profile_distribution': {},
                 'top_recommendations': [], 'topics_needing_reinforcement': [],
                 'model': None, 'clusters': None}
        return empty

    dt_artifact = model_manager.load_artifact('decision_tree')
    km_artifact = model_manager.load_artifact('kmeans')

    mastery_dist = {}
    profile_dist = {}
    insufficient = 0
    analyzed = 0

    for s in students:
        row = feature_service.aggregate_student_features(s)
        if row is None:
            insufficient += 1
            continue
        analyzed += 1
        if dt_artifact:
            label = decision_tree.predict_row(row, dt_artifact)[0]
            if label:
                mastery_dist[label] = mastery_dist.get(label, 0) + 1
        if km_artifact:
            cid = kmeans_mod.assign_cluster(row, km_artifact)
            if cid is not None:
                label_k = cluster_interpreter.interpret_clusters(km_artifact)
                for prof in label_k:
                    if prof['cluster_id'] == cid:
                        profile_dist[prof['label']] = profile_dist.get(prof['label'], 0) + 1
                        break

    model_info = _model_info()
    clusters_info = _clusters_info()
    top_recommendations = _top_recommendations(teacher)
    topics = [t for t in analytics.teacher_topics(teacher.id)
              if t['mastery']['label'] in ('Kurang', 'Cukup')]
    topics.sort(key=lambda t: t['average_progress'])
    topics_needing = [{'topic': t['topic'], 'average_progress': t['average_progress'],
                       'mastery_label': t['mastery']['label'],
                       'materials': t['materials']} for t in topics[:5]]

    return {
        'signals': analyzed + insufficient,
        'analyzed': analyzed,
        'insufficient_data': insufficient,
        'mastery_distribution': mastery_dist,
        'profile_distribution': profile_dist,
        'top_recommendations': top_recommendations,
        'topics_needing_reinforcement': topics_needing,
        'model': model_info,
        'clusters': clusters_info,
    }


def _model_info():
    record = model_manager.latest_record('decision_tree')
    if not record:
        return None
    return {
        'status': cfg.STATUS_READY,
        'model_type': 'decision_tree',
        'model_version': record.model_version,
        'feature_version': record.feature_version,
        'trained_at': record.trained_at.isoformat() + 'Z' if record.trained_at else None,
        'training_sample_count': record.training_sample_count,
        'metrics': record.metrics_json,
        'evaluation_note': (record.metrics_json or {}).get('evaluation_note'),
    }


def _clusters_info():
    info = model_manager.latest_record('kmeans')
    artifact = model_manager.load_artifact('kmeans')
    if not info or not artifact:
        return None
    profiles = cluster_interpreter.interpret_clusters(artifact)
    return {
        'status': cfg.STATUS_READY,
        'model_type': 'kmeans',
        'model_version': info.model_version,
        'trained_at': info.trained_at.isoformat() + 'Z' if info.trained_at else None,
        'k': artifact.get('k'),
        'silhouette': artifact.get('silhouette'),
        'silhouettes': artifact.get('silhouettes'),
        'n_samples': artifact.get('sample_count'),
        'profiles': profiles,
        'silhouette_note': 'Nilai silhouette digunakan untuk melihat seberapa baik data terpisah dalam cluster.',
    }


def _top_recommendations(teacher):
    from src.models.recommendation import Recommendation
    student_ids = analytics.teacher_student_ids(teacher.id)
    if not student_ids:
        return []
    rows = Recommendation.query.filter(Recommendation.student_id.in_(student_ids)).all()
    agg = {}
    for r in rows:
        if not r.material:
            continue
        bucket = agg.setdefault(r.material_id, {'count': 0, 'score_sum': 0.0,
                                                'title': r.material.title,
                                                'topic': r.material.topic})
        bucket['count'] += 1
        bucket['score_sum'] += (r.recommendation_score or 0.0)
    out = []
    for mid, b in agg.items():
        out.append({'material_id': mid, 'title': b['title'], 'topic': b['topic'],
                    'count': b['count'],
                    'average_score': round(b['score_sum'] / b['count'], 4)})
    out.sort(key=lambda x: (-x['count'], -x['average_score']))
    return out[:5]


@jwt_required()
def get_teacher_ml_analytics():
    teacher, err = _teacher()
    if err:
        return err
    result = _ml_insights(teacher)
    return jsonify(result), 200


# ============================================================
# TRAINING / PREDICTION (protected, teacher/admin)
# ============================================================
def _all_students():
    return User.query.filter_by(role='student').all()


def _train_pipeline():
    students = _all_students()
    rows = feature_service.build_dataset(students)
    result = {'analysis_students': len(students), 'dataset_rows': len(rows)}

    dt_payload = decision_tree.fit_from_rows(rows)
    km_payload = kmeans_mod.fit_from_rows(rows)

    if dt_payload.get('status') == cfg.STATUS_READY:
        meta = model_manager.save_artifact('decision_tree', dt_payload)
        result['decision_tree'] = {'status': cfg.STATUS_READY, 'model_version': meta['model_version'],
                                   'metrics': dt_payload.get('metrics'),
                                   'evaluation_note': dt_payload.get('evaluation_note'),
                                   'training_sample_count': dt_payload.get('sample_count')}
    else:
        result['decision_tree'] = {'status': dt_payload.get('status'),
                                   'message': dt_payload.get('message'),
                                   'samples': dt_payload.get('samples'),
                                   'min_required': dt_payload.get('min_required')}

    if km_payload.get('status') == cfg.STATUS_READY:
        meta = model_manager.save_artifact('kmeans', km_payload)
        result['kmeans'] = {'status': cfg.STATUS_READY, 'model_version': meta['model_version'],
                            'k': km_payload.get('k'), 'silhouette': km_payload.get('silhouette'),
                            'silhouettes': km_payload.get('silhouettes'),
                            'training_sample_count': km_payload.get('sample_count')}
    else:
        result['kmeans'] = {'status': km_payload.get('status'),
                            'message': km_payload.get('message'),
                            'samples': km_payload.get('samples'),
                            'min_required': km_payload.get('min_required')}
    return result


@jwt_required()
def train_ml():
    teacher, err = _teacher()
    if err:
        return err
    return jsonify(_train_pipeline()), 200


# ============================================================
# RETRAIN (alias of train — semantic re-use)
# ============================================================
@jwt_required()
def retrain_ml():
    teacher, err = _teacher()
    if err:
        return err
    return jsonify(_train_pipeline()), 200


# ============================================================
# PREDICT single student (teacher/admin, must share a course)
# ============================================================
@jwt_required()
def predict_student(student_id):
    teacher, err = _teacher()
    if err:
        return err
    student = User.query.get(int(student_id)) if str(student_id).isdigit() else None
    if not student or student.role != 'student':
        return jsonify({'error': 'Siswa tidak ditemukan'}), 404
    # ownership check: student must be among teacher's own students
    my_student_ids = set(analytics.teacher_student_ids(teacher.id))
    if student.id not in my_student_ids:
        return jsonify({'error': 'Anda tidak memiliki akses ke data siswa ini'}), 403
    dt_artifact = model_manager.load_artifact('decision_tree')
    km_artifact = model_manager.load_artifact('kmeans')
    result = profile_mod.generate_profile(student, dt_artifact, km_artifact)
    return jsonify(result), 200


# ============================================================
# TEACHER ML ANALYTICS — mastery breakdown
# ============================================================
@jwt_required()
def get_teacher_ml_mastery():
    teacher, err = _teacher()
    if err:
        return err
    insights = _ml_insights(teacher)
    return jsonify({
        'mastery_distribution': insights['mastery_distribution'],
        'analyzed': insights['analyzed'],
        'insufficient_data': insights['insufficient_data'],
    }), 200


# ============================================================
# TEACHER ML ANALYTICS — cluster breakdown
# ============================================================
@jwt_required()
def get_teacher_ml_clusters():
    teacher, err = _teacher()
    if err:
        return err
    clusters = _clusters_info()
    if not clusters:
        return jsonify({'status': cfg.STATUS_MODEL_UNAVAILABLE, 'message': 'Model belum tersedia'}), 200
    return jsonify(clusters), 200