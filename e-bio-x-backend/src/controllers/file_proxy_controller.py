# ============================================================
# Authenticated file download proxy.
#
# Objects live in a PRIVATE bucket; this endpoint is the only
# browser-facing door. It requires a JWT, verifies the requested
# key is actually referenced by application metadata (no bucket
# enumeration) and applies material visibility rules when the
# object belongs to a material. Media tags that cannot send
# Authorization headers receive short-lived presigned URLs from
# the serializers instead of going through this proxy.
# ============================================================
import mimetypes

from flask import request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.config.database import db
from src.models.user import User
from src.models.material import Material
from src.models.material_file import MaterialFile
from src.models.enrollment import Enrollment
from src.models.forum import ForumAttachment
from src.services import storage_service


def _current_user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _material_readable(material, user):
    if user.role == 'admin':
        return True
    if material.teacher_id == user.id:
        return True
    enrolled_ids = [e.course_id for e in
                    Enrollment.query.filter_by(student_id=user.id).all()]
    linked = {c.id for c in material.course_links}
    if material.course_id:
        linked.add(material.course_id)
    if user.role == 'teacher':
        from src.models.course import Course
        if linked and Course.query.filter(
                Course.id.in_(linked), Course.teacher_id == user.id).count():
            return True
        return False
    # student: published + reachable through one of their classes
    if material.status != 'published':
        return False
    return not linked or bool(linked & set(enrolled_ids))


def _resolve_access(key, user):
    """Returns (allowed, owner_material_or_None)."""
    canonical = storage_service.URL_PREFIX + key

    mf = MaterialFile.query.filter_by(file_url=canonical).first()
    if not mf:
        mf = MaterialFile.query.filter(MaterialFile.file_url.endswith(key)).first()
    forum_hit = None
    if mf is None:
        fa = ForumAttachment.query.filter(ForumAttachment.file_url.endswith(key)).first()
        if fa is None:
            from src.models.forum import Forum
            col = getattr(Forum, 'presentation_file_url')
            fv = getattr(Forum, 'presentation_video_url')
            forum_hit = Forum.query.filter(
                (col.like(f'%{key}')) | (fv.like(f'%{key}'))).first()
    if mf is None and forum_hit is None:
        m_direct = Material.query.filter(
            (Material.file_url == canonical) |
            (Material.thumbnail_url == canonical) |
            (Material.file_url.like(f'%{key}')) |
            (Material.thumbnail_url.like(f'%{key}'))
        ).first()
    else:
        m_direct = None

    if mf is not None:
        material = Material.query.get(mf.material_id)
        return _material_readable(material, user), material
    if m_direct is not None:
        return _material_readable(m_direct, user), m_direct
    # forum attachments / presentation files: any authenticated member-level access
    if forum_hit is not None:
        return True, None
    # nothing matched — deny to prevent bucket enumeration
    return False, None


@jwt_required()
def download_file(key):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    allowed, _owner = _resolve_access(key, user)
    if not allowed:
        return jsonify({'error': 'Anda tidak memiliki akses ke file ini'}), 403

    try:
        data = storage_service.get_bytes(key)
    except storage_service.StorageError as e:
        print('Storage read failed:', e)
        return jsonify({'error': 'Storage tidak tersedia'}), 502
    if data is None:
        return jsonify({'error': 'File tidak ditemukan'}), 404

    filename = key.rsplit('/', 1)[-1]
    mime = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    return Response(
        data,
        mimetype=mime,
        headers={
            'Content-Disposition': f"inline; filename*=UTF-8''{filename}",
            'Cache-Control': 'private, max-age=3600',
        },
    )
