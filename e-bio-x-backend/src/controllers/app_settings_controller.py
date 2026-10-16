from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.services import app_settings_service as settings


def _current_user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


@jwt_required()
def get_app_settings():
    """Pengaturan global yang perlu dibaca semua peran (termasuk murid).

    Murid memakainya untuk menampilkan "Kata Pengantar" di halaman materi,
    jadi endpoint ini tidak dibatasi peran - hanya butuh login.
    """
    return jsonify({'foreword': settings.get_foreword()}), 200


@jwt_required()
def update_app_settings():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru atau admin yang dapat mengubah pengaturan'}), 403
    data = request.get_json(silent=True) or {}
    if 'foreword' in data:
        settings.set_foreword(data.get('foreword'))
    return jsonify({'message': 'Pengaturan aplikasi diperbarui',
                    'foreword': settings.get_foreword()}), 200
