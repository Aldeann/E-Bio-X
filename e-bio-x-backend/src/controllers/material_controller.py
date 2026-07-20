from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from src.models.material import Material
from src.config.database import db
from datetime import datetime
from dotenv import load_dotenv
import traceback
import os
import uuid
import re

load_dotenv()

@jwt_required()
def upload_material():
    title = request.form.get('title')
    content = request.form.get('content')
    try:
        course_id = int(request.form.get('course_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'course_id harus berupa angka'}), 400

    file = request.files.get('file')

    if not all([title, course_id, file]):
        return jsonify({'error': 'Title, course_id, and file are required'}), 400

    upload_folder = current_app.config['UPLOAD_FOLDER']

    original_name = secure_filename(file.filename)
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    unique_name = f"{uuid.uuid4().hex}_{original_name}" if ext else uuid.uuid4().hex
    save_path = os.path.join(upload_folder, unique_name)

    try:
        file.save(save_path)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Gagal menyimpan file"}), 500

    file_url = f"{request.host_url}uploads/{unique_name}"

    new_material = Material(
        title=title,
        content=content,
        course_id=course_id,
        file_url=file_url,
        uploaded_at=datetime.utcnow()
    )
    db.session.add(new_material)
    db.session.commit()

    return jsonify({
        'message': 'Material uploaded',
        'material': {
            'id': new_material.id,
            'title': new_material.title,
            'file_url': new_material.file_url
        }
    }), 201

@jwt_required()
def get_material_by_id(material_id):
    material = Material.query.get(material_id)

    if not material:
        return jsonify({'error': 'Material not found'}), 404

    return jsonify({
        'id': material.id,
        'title': material.title,
        'description': material.content,
        'file_url': material.file_url,
        'course_id': material.course_id,
        'uploaded_at': material.uploaded_at,
    }), 200

@jwt_required()
def get_material_by_course(course_id):
    materials = Material.query.filter_by(course_id=course_id).all()

    result = []
    for material in materials:
        result.append({
            'id': material.id,
            'title': material.title,
            'description': material.content,
            'file_url': material.file_url,
            'course_id': material.course_id,
            'uploaded_at': material.uploaded_at,
        })

    return jsonify({
        'message': 'Materials retrieved successfully',
        'data': result,
    }), 200

@jwt_required()
def get_all_material():
    materials = Material.query.all()

    return jsonify([{
            'id': material.id,
            'title': material.title,
            'description': material.content,
            'file_url': material.file_url,
            'course': material.course.name,
            'uploaded_at': material.uploaded_at,
        } for material in materials
    ]), 200

@jwt_required()
def delete_material(material_id):
    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    upload_folder = current_app.config['UPLOAD_FOLDER']
    filename = os.path.basename(material.file_url)
    file_path = os.path.join(upload_folder, filename)

    db.session.delete(material)
    db.session.commit()

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print("Failed to delete file from disk:", e)

    return jsonify({'message': 'Material deleted successfully'}), 200