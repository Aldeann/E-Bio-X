from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import User
from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.material_content import MaterialContent
from src.models.video_progress import VideoProgress
from src.models.student_content_track import StudentContentTrack
from src.controllers.material_controller import _can_student_access
from src.config.database import db
from src.services import learning_analytics_service as analytics
from src.ml import ml_config as ml_cfg
from datetime import datetime


def _user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _student_guard(material_id):
    user = _user()
    if not user:
        return None, None, jsonify({'error': 'User not found'}), 404
    if user.role != 'student':
        return None, None, jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    material = Material.query.get(material_id)
    if not material:
        return None, None, jsonify({'error': 'Material not found'}), 404
    if material.status != 'published':
        return None, None, jsonify({'error': 'Materi belum dipublikasikan'}), 403
    if not _can_student_access(material, user):
        return None, None, jsonify({'error': 'Materi hanya untuk kelas yang diikuti'}), 403
    return user, material, None, None


@jwt_required()
def ping_session(material_id):
    user, material, err, code = _student_guard(material_id)
    if err:
        return err, code

    data = request.get_json(silent=True) or {}
    session = analytics.open_session(user.id, material.id)
    db.session.commit()

    total = analytics.learning_seconds_for(user.id, material.id)
    return jsonify({
        'session_id': session.id,
        'active_seconds': analytics._active_seconds(session),
        'total_seconds': total,
        'last_seen_at': datetime.utcnow().isoformat() + 'Z',
    }), 200


@jwt_required()
def log_material_event(material_id):
    user, material, err, code = _student_guard(material_id)
    if err:
        return err, code

    data = request.get_json(silent=True) or {}
    event_type = data.get('event_type')
    if not event_type or event_type not in analytics.ALLOWED_EVENT_TYPES:
        return jsonify({'error': 'event_type tidak valid'}), 400

    section = None
    content = None
    section_id = data.get('section_id')
    content_id = data.get('content_id')

    if section_id is not None:
        try:
            section = MaterialSection.query.filter_by(id=int(section_id), material_id=material.id).first()
        except (TypeError, ValueError):
            section = None
        if not section:
            return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 404
    if content_id is not None:
        try:
            content = MaterialContent.query.get(int(content_id))
        except (TypeError, ValueError):
            content = None
        if not content or content.section.material_id != material.id:
            return jsonify({'error': 'Content tidak ditemukan pada materi ini'}), 404

    try:
        if event_type == 'content_viewed' and content:
            analytics.mark_content_viewed(user.id, material.id, content.id, silent=False)
        activity = analytics.log_activity(
            user.id, material.id, event_type,
            section_id=section.id if section else None,
            content_id=content.id if content else None,
            data=data.get('data'),
            silent=False,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Gagal mencatat aktivitas: {str(e)}'}), 500

    _maybe_auto_retrain()
    return jsonify({'message': 'Aktivitas tercatat', 'activity_id': activity.id}), 201


def _maybe_auto_retrain():
    """Trigger background ML retrain if enough new activities since last training."""
    import threading
    from src.models.learning_activity import LearningActivity
    from src.models.ml_model import MlModel

    last_model = MlModel.query.filter_by(
        model_type='decision_tree').order_by(MlModel.trained_at.desc()).first()
    since = last_model.trained_at if last_model else datetime.min
    new_count = LearningActivity.query.filter(
        LearningActivity.created_at > since).count()
    if new_count < ml_cfg.AUTO_RETRAIN_THRESHOLD:
        return

    def _bg_train():
        try:
            from src.controllers.ml_controller import _train_pipeline
            _train_pipeline()
        except Exception:
            pass

    threading.Thread(target=_bg_train, daemon=True).start()


@jwt_required()
def post_video_progress(material_id):
    user, material, err, code = _student_guard(material_id)
    if err:
        return err, code

    data = request.get_json(silent=True) or {}
    content_id = data.get('content_id')
    if content_id is None:
        return jsonify({'error': 'content_id wajib diisi'}), 400

    try:
        content = MaterialContent.query.get(int(content_id))
    except (TypeError, ValueError):
        content = None
    if not content or content.section.material_id != material.id:
        return jsonify({'error': 'Content tidak ditemukan pada materi ini'}), 404

    try:
        duration = float(data.get('video_duration') or 0)
        watched = float(data.get('watched_duration') or 0)
        position = float(data.get('last_position') or 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'Nilai video_progress tidak valid'}), 400
    if duration < 0 or watched < 0 or position < 0:
        return jsonify({'error': 'Nilai video_progress tidak valid'}), 400
    completed = bool(data.get('completed')) or (duration > 0 and watched >= duration * 0.9)

    video = VideoProgress.query.filter_by(student_id=user.id, content_id=content.id).first()
    if not video:
        video = VideoProgress(
            student_id=user.id, material_id=material.id, content_id=content.id,
            video_duration=duration, watched_duration=watched,
            last_position=position, completed=completed,
        )
        db.session.add(video)
    else:
        video.video_duration = max(video.video_duration or 0, duration)
        video.watched_duration = max(video.watched_duration or 0, watched)
        video.last_position = max(video.last_position or 0, position)
        video.completed = video.completed or completed or video.completed
        if completed:
            video.completed = True
        video.updated_at = datetime.utcnow()

    try:
        analytics.mark_content_viewed(user.id, material.id, content.id, silent=True)
        analytics.log_activity(
            user.id, material.id, 'video_played',
            section_id=content.section_id, content_id=content.id,
            data={'position': position, 'watched': watched, 'duration': duration},
            silent=True,
        )
        if completed:
            analytics.log_activity(
                user.id, material.id, 'video_completed',
                section_id=content.section_id, content_id=content.id,
                data={'watched': watched, 'duration': duration},
                silent=True,
            )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Gagal menyimpan progress video: {str(e)}'}), 500

    return jsonify({
        'message': 'Progress video tersimpan',
        'completed': video.completed,
        'watched_duration': video.watched_duration,
        'last_position': video.last_position,
    }), 200


@jwt_required()
def get_video_progress(material_id):
    user, material, err, code = _student_guard(material_id)
    if err:
        return err, code

    rows = VideoProgress.query.filter_by(student_id=user.id, material_id=material.id).all()
    result = [{
        'content_id': v.content_id,
        'video_duration': v.video_duration,
        'watched_duration': v.watched_duration,
        'last_position': v.last_position,
        'completed': v.completed,
        'updated_at': v.updated_at.isoformat() + 'Z' if v.updated_at else None,
    } for v in rows]
    return jsonify(result), 200


@jwt_required()
def get_content_track(material_id):
    user, material, err, code = _student_guard(material_id)
    if err:
        return err, code

    rows = StudentContentTrack.query.filter_by(student_id=user.id, material_id=material.id).all()
    return jsonify([{'content_id': r.content_id, 'viewed_at': r.viewed_at.isoformat() + 'Z' if r.viewed_at else None,
                     'view_count': r.view_count} for r in rows]), 200