from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from src.models.material import Material, material_courses
from src.models.material_section import MaterialSection
from src.models.material_content import MaterialContent
from src.models.material_file import MaterialFile
from src.models.material_progress import MaterialProgress
from src.models.material_student_state import MaterialStudentState
from src.models.material_bookmark import MaterialBookmark
from src.models.student_note import StudentNote
from src.models.student_answer import StudentAnswer
from src.models.user import User
from src.models.course import Course
from src.models.enrollment import Enrollment
from src.config.database import db
from src.services.learning_analytics_service import log_activity, mark_content_viewed
from datetime import datetime
from dotenv import load_dotenv
import traceback
import os
import uuid
import re

load_dotenv()

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt', 'jpg', 'jpeg', 'png', 'webp', 'mp4'}
MAX_FILE_SIZE = 40 * 1024 * 1024  # 40 MB per file

REQUIRED_FIELDS = ['title', 'description', 'phase', 'topic', 'learning_objectives']


def _get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id) if user_id else None


def _is_owner(material, user):
    return material.teacher_id == user.id


def _is_course_teacher(material, user):
    linked_ids = {c.id for c in (material.course_links or [])}
    if material.course_id:
        linked_ids.add(material.course_id)
    if not linked_ids:
        return False
    return Course.query.filter(
        Course.id.in_(linked_ids), Course.teacher_id == user.id
    ).first() is not None


def _can_manage(material, user):
    if user.role == 'admin' or _is_owner(material, user):
        return True
    return user.role == 'teacher' and _is_course_teacher(material, user)


def _can_view_detail(material, user):
    if user.role == 'student':
        return material.status == 'published'
    return True


def _can_student_access(material, user):
    if material.status != 'published':
        return False
    if material.course_links:
        enrolled_ids = {e.course_id for e in user.enrollments}
        return any(c.id in enrolled_ids for c in material.course_links)
    return True


def _is_enrolled(course, user):
    return Enrollment.query.filter_by(student_id=user.id, course_id=course.id).first() is not None


def _parse_course_ids(data):
    course_ids = data.get('course_ids')
    if course_ids is not None:
        if isinstance(course_ids, str):
            try:
                course_ids = [int(x) for x in course_ids.split(',') if x.strip()]
            except ValueError:
                return None
        elif isinstance(course_ids, list):
            course_ids = [int(x) for x in course_ids if str(x).isdigit()]
        else:
            return None
        return list(dict.fromkeys(course_ids))
    return None


def _resolve_owned_course_ids(user, course_ids):
    if course_ids is None:
        return None
    query = Course.query.filter(Course.id.in_(course_ids))
    if user.role != 'admin':
        query = query.filter(Course.teacher_id == user.id)
    return [c.id for c in query.all()]


def _student_course_ids(user):
    return [e.course_id for e in Enrollment.query.filter_by(student_id=user.id).all()]


def _allowed_file(filename):
    if not filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS


def _matches_signature(file, ext):
    """Verify the real file content matches the claimed extension (magic bytes)."""
    try:
        head = file.read(16)
        file.seek(0)
    except Exception:
        return False
    if not head:
        return False
    if ext == 'pdf':
        return head.startswith(b'%PDF')
    if ext in ('docx', 'doc'):
        # OOXML/ZIP container magic (doc, docx) or legacy OLE (doc)
        return head.startswith(b'PK\x03\x04') or head.startswith(b'\xd0\xcf\x11\xe0')
    if ext == 'txt':
        # allow any printable-ish text; reject binary nulls
        return b'\x00' not in head[:16]
    if ext == 'png':
        return head.startswith(b'\x89PNG\r\n\x1a\n')
    if ext in ('jpg', 'jpeg'):
        return head.startswith(b'\xff\xd8\xff')
    if ext == 'webp':
        return head.startswith(b'RIFF') and head[8:12] == b'WEBP'
    if ext == 'mp4':
        # MP4 boxes start with a 4-byte size followed by 'ftyp'
        return len(head) >= 12 and head[4:8] == b'ftyp'
    return False


def _upload_folder():
    folder = current_app.config.get('UPLOAD_FOLDER')
    if not folder:
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
    return folder


def _save_uploaded_file(file):
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if not _matches_signature(file, ext):
        return None, 'Konten file tidak sesuai dengan tipe yang diizinkan'
    original_name = secure_filename(file.filename)
    if not original_name:
        original_name = 'file'
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    unique_name = f"{uuid.uuid4().hex}_{original_name}" if ext else uuid.uuid4().hex
    upload_folder = _upload_folder()
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, unique_name)
    file.save(save_path)

    if os.path.getsize(save_path) > MAX_FILE_SIZE:
        os.remove(save_path)
        return None, f'Ukuran file melebihi batas maksimal 40MB'

    file_url = f"{request.host_url}uploads/{unique_name}"
    return {'name': unique_name, 'path': save_path, 'url': file_url}, None


def _student_progress_map(user, material_ids):
    if not material_ids:
        return {}
    rows = MaterialProgress.query.filter(
        MaterialProgress.student_id == user.id,
        MaterialProgress.material_id.in_(material_ids),
    ).all()
    result = {}
    for r in rows:
        result.setdefault(r.material_id, set()).add(r.section_id)
    return result


def _student_progress_info(material, done_section_ids):
    total = len(material.sections)
    done = len(done_section_ids)
    percentage = round((done / total) * 100) if total else 0
    return {
        'completed': done,
        'total': total,
        'percentage': percentage,
        'finished': total > 0 and done >= total,
    }


def _serialize_material_list(material, include_analytics=False, student_progress=None):
    description = material.description or material.content
    item = {
        'id': material.id,
        'title': material.title,
        'description': description,
        'file_url': material.file_url,
        'course': material.course.name if material.course else None,
        'course_id': material.course_id,
        'courses': [c.name for c in material.course_links],
        'course_ids': [c.id for c in material.course_links],
        'subject': material.subject,
        'phase': material.phase,
        'class_level': material.class_level,
        'topic': material.topic,
        'difficulty': material.difficulty,
        'estimated_time': material.estimated_time,
        'thumbnail_url': material.thumbnail_url,
        'status': material.status,
        'teacher_id': material.teacher_id,
        'uploaded_at': material.uploaded_at.isoformat() if material.uploaded_at else None,
        'created_at': material.uploaded_at.isoformat() if material.uploaded_at else None,
        'updated_at': material.updated_at.isoformat() if material.updated_at else None,
        'section_count': len(material.sections),
        'content_count': sum(len(s.contents) for s in material.sections),
    }
    if student_progress is not None:
        item['student_progress'] = student_progress
    if include_analytics:
        stats = _compute_analytics(material)
        item.update(stats)
    return item


def _serialize_content(content, include_answers=True):
    data = dict(content.data) if isinstance(content.data, dict) else {}
    if not include_answers:
        data.pop('correct_answer', None)
        if content.type == 'quiz' and isinstance(data.get('questions'), list):
            for q in data['questions']:
                if isinstance(q, dict):
                    q.pop('correct_answer', None)
    return {
        'id': content.id,
        'type': content.type,
        'data': data,
        'position': content.position,
    }


def _serialize_material_detail(material, include_answers=True, include_analytics=False):
    sections = []
    for section in material.sections:
        sections.append({
            'id': section.id,
            'title': section.title,
            'position': section.position,
            'contents': [_serialize_content(c, include_answers) for c in section.contents],
        })

    result = {
        'id': material.id,
        'title': material.title,
        'description': material.description or material.content,
        'content': material.content,
        'file_url': material.file_url,
        'subject': material.subject,
        'phase': material.phase,
        'class_level': material.class_level,
        'topic': material.topic,
        'learning_objectives': material.learning_objectives,
        'estimated_time': material.estimated_time,
        'difficulty': material.difficulty,
        'thumbnail_url': material.thumbnail_url,
        'status': material.status,
        'course_id': material.course_id,
        'courses': [c.name for c in material.course_links],
        'course_ids': [c.id for c in material.course_links],
        'teacher_id': material.teacher_id,
        'teacher_name': material.teacher.name if material.teacher else None,
        'uploaded_at': material.uploaded_at.isoformat() if material.uploaded_at else None,
        'created_at': material.uploaded_at.isoformat() if material.uploaded_at else None,
        'updated_at': material.updated_at.isoformat() if material.updated_at else None,
        'sections': sections,
        'files': [
            {
                'id': f.id,
                'original_name': f.original_name,
                'file_name': f.file_name,
                'file_size': f.file_size,
                'file_type': f.file_type,
                'file_url': f.file_url,
            }
            for f in material.files
        ],
    }
    if include_analytics:
        result['analytics'] = _compute_analytics(material)
    return result


def _compute_analytics(material):
    section_ids = [s.id for s in material.sections]
    total_sections = len(section_ids)
    rows = []
    if total_sections > 0:
        rows = MaterialProgress.query.filter(
            MaterialProgress.material_id == material.id
        ).all()

    students_map = {}
    for row in rows:
        if row.student_id not in students_map:
            students_map[row.student_id] = set()
        students_map[row.student_id].add(row.section_id)

    student_names = {}
    for sid in students_map:
        student = User.query.get(sid)
        student_names[sid] = student.name if student else 'Siswa'

    students_count = len(students_map)

    if total_sections == 0 or students_count == 0:
        completion = 0.0
    else:
        completion = sum(
            (len(secs) / total_sections) * 100 for secs in students_map.values()
        ) / students_count

    students_list = [
        {
            'student_id': sid,
            'name': student_names[sid],
            'completed': len(secs),
            'total': total_sections,
            'percentage': round((len(secs) / total_sections) * 100, 1) if total_sections else 0,
        }
        for sid, secs in students_map.items()
    ]

    return {
        'students': students_count,
        'completion_percentage': round(completion, 1),
        'students_list': students_list,
    }


# ============================================================
# CREATE MATERIAL
# ============================================================

@jwt_required()
def upload_material():
    if request.is_json:
        return _create_material_json()
    return _create_material_form()


def _create_material_json():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat membuat materi'}), 403

    data = request.get_json(silent=True) or {}
    for field in REQUIRED_FIELDS:
        if not data.get(field):
            return jsonify({'error': f'{field.replace("_", " ").capitalize()} wajib diisi'}), 400

    try:
        course_id = data.get('course_id')
        if course_id is not None:
            course_id = int(course_id)

        course_ids = _parse_course_ids(data)
        if 'course_ids' in data and course_ids is None:
            return jsonify({'error': 'course_ids harus berupa daftar id kelas'}), 400
        owned = _resolve_owned_course_ids(user, course_ids)
        if course_ids and not owned:
            return jsonify({'error': 'Kelas tidak ditemukan atau bukan milik Anda'}), 400

        if course_id is None and owned:
            course_id = owned[0]

        material = Material(
            title=data['title'].strip(),
            description=data.get('description', '').strip(),
            subject=data.get('subject') or None,
            phase=data['phase'].strip(),
            class_level=data.get('class_level') or None,
            topic=data['topic'].strip(),
            learning_objectives=data['learning_objectives'].strip(),
            estimated_time=data.get('estimated_time') or None,
            difficulty=data.get('difficulty') or None,
            thumbnail_url=data.get('thumbnail_url') or None,
            status=data.get('status') if data.get('status') in ('draft', 'published') else 'draft',
            course_id=course_id,
            teacher_id=user.id,
            content=data.get('description', '').strip(),
            updated_at=datetime.utcnow(),
        )
        db.session.add(material)
        db.session.flush()
        if owned:
            linked = Course.query.filter(Course.id.in_(owned)).all()
            material.course_links.extend(linked)
        db.session.commit()
        return jsonify({
            'message': 'Materi berhasil dibuat',
            'material': _serialize_material_detail(material, include_analytics=True),
        }), 201
    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': f'Gagal membuat materi: {str(e)}'}), 500


def _create_material_form():
    title = request.form.get('title')
    content = request.form.get('content')
    try:
        course_id = int(request.form.get('course_id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'course_id harus berupa angka'}), 400

    file = request.files.get('file')

    if not all([title, course_id, file]):
        return jsonify({'error': 'Title, course_id, and file are required'}), 400

    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat membuat materi'}), 403

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Kelas tidak ditemukan'}), 404
    if user.role != 'admin' and str(course.teacher_id) != str(user.id):
        return jsonify({'error': 'Kelas bukan milik Anda'}), 403

    if not _allowed_file(file.filename):
        return jsonify({'error': 'Tipe file tidak diizinkan'}), 400

    saved, err = _save_uploaded_file(file)
    if err:
        return jsonify({'error': err}), 400

    try:
        new_material = Material(
            title=title,
            content=content,
            course_id=course.id,
            file_url=saved['url'],
            teacher_id=user.id,
            status='published',
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_material)
        db.session.commit()

        db.session.add(MaterialFile(
            material_id=new_material.id,
            original_name=file.filename,
            file_name=saved['name'],
            file_size=os.path.getsize(saved['path']),
            file_type=file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else '',
            file_url=saved['url'],
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        if os.path.exists(saved['path']):
            os.remove(saved['path'])
        traceback.print_exc()
        return jsonify({"error": "Gagal menyimpan file"}), 500

    return jsonify({
        'message': 'Material uploaded',
        'material': {
            'id': new_material.id,
            'title': new_material.title,
            'file_url': new_material.file_url
        }
    }), 201


# ============================================================
# READ MATERIAL
# ============================================================

@jwt_required()
def get_all_material():
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role == 'admin':
        materials = Material.query.all()
        return jsonify([_serialize_material_list(m) for m in materials]), 200
    elif user.role == 'teacher':
        materials = Material.query.filter_by(teacher_id=user.id).all()
        return jsonify([_serialize_material_list(m, include_analytics=True) for m in materials]), 200
    else:
        enrolled_ids = _student_course_ids(user)
        materials = Material.query.filter_by(status='published').all()
        materials = [
            m for m in materials
            if not m.course_links or any(c.id in enrolled_ids for c in m.course_links)
        ]
        progress_map = _student_progress_map(user, [m.id for m in materials])
        return jsonify([
            _serialize_material_list(
                m,
                student_progress=_student_progress_info(m, progress_map.get(m.id, set())),
            )
            for m in materials
        ]), 200


@jwt_required()
def get_material_by_id(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_view_detail(material, user):
        return jsonify({'error': 'Materi belum dipublikasikan'}), 403

    if user.role == 'student':
        if not _can_student_access(material, user):
            return jsonify({'error': 'Materi hanya untuk kelas yang diikuti'}), 403
        return jsonify(_serialize_material_detail(material, include_answers=False)), 200

    include_answers = user.role == 'admin' or _is_owner(material, user)
    return jsonify(_serialize_material_detail(
        material,
        include_answers=include_answers,
        include_analytics=include_answers,
    )), 200


@jwt_required()
def get_material_by_course(course_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Kelas tidak ditemukan'}), 404

    if user.role == 'student':
        if not _is_enrolled(course, user):
            return jsonify({'error': 'Anda bukan anggota kelas ini'}), 403
    elif user.role == 'teacher':
        if str(course.teacher_id) != str(user.id):
            return jsonify({'error': 'Anda tidak berhak mengelola kelas ini'}), 403
    elif user.role != 'admin':
        return jsonify({'error': 'Akses ditolak'}), 403

    materials = Material.query.outerjoin(
        material_courses, Material.id == material_courses.c.material_id
    ).filter(
        or_(Material.course_id == course_id, material_courses.c.course_id == course_id)
    ).all()
    materials = list({m.id: m for m in materials}.values())

    if user.role == 'student':
        materials = [m for m in materials if m.status == 'published']

    result = []
    for material in materials:
        is_interactive = material.file_url is None
        result.append({
            'id': material.id,
            'title': material.title,
            'description': material.description or material.content,
            'file_url': material.file_url,
            'course_id': material.course_id,
            'category': 'interactive' if is_interactive else 'file',
            'status': material.status,
            'section_count': len(material.sections),
            'content_count': sum(len(s.contents) for s in material.sections),
            'uploaded_at': material.uploaded_at,
        })

    return jsonify({
        'message': 'Materials retrieved successfully',
        'data': result,
    }), 200


# DEPRECATED (audit 14.8): gunakan /api/teacher/analytics/materials/<id>
@jwt_required()
def get_material_analytics(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda tidak berhak mengakses materi ini'}), 403

    return jsonify({
        'id': material.id,
        'title': material.title,
        'analytics': _compute_analytics(material),
    }), 200


# ============================================================
# UPDATE / DELETE MATERIAL
# ============================================================

@jwt_required()
def update_material(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    data = request.get_json(silent=True) or {}
    editable = ['title', 'description', 'subject', 'phase', 'class_level', 'topic',
                'learning_objectives', 'estimated_time', 'difficulty', 'thumbnail_url']

    for field in editable:
        if field in data and data[field] is not None:
            setattr(material, field, str(data[field]).strip())

    if 'course_ids' in data:
        course_ids = _parse_course_ids(data)
        if course_ids is None:
            return jsonify({'error': 'course_ids harus berupa daftar id kelas'}), 400
        owned = _resolve_owned_course_ids(user, course_ids)
        if course_ids and not owned:
            return jsonify({'error': 'Kelas tidak ditemukan atau bukan milik Anda'}), 400
        material.course_links = Course.query.filter(Course.id.in_(owned)).all() if owned else []
        if 'course_id' not in data and material.course_links:
            material.course_id = material.course_links[0].id

    material.updated_at = datetime.utcnow()
    if not material.content:
        material.content = material.description

    db.session.commit()
    return jsonify({
        'message': 'Materi berhasil diperbarui',
        'material': _serialize_material_detail(material, include_analytics=True),
    }), 200


@jwt_required()
def delete_material(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda hanya dapat menghapus materi milik sendiri'}), 403

    upload_folder = _upload_folder()

    disk_files = []
    if material.file_url:
        disk_files.append(os.path.basename(material.file_url))
    for f in material.files:
        disk_files.append(f.file_name)

    db.session.delete(material)
    db.session.commit()

    for filename in disk_files:
        file_path = os.path.join(upload_folder, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print("Failed to delete file from disk:", e)

    return jsonify({'message': 'Material deleted successfully'}), 200


# ============================================================
# PUBLISH / UNPUBLISH
# ============================================================

@jwt_required()
def publish_material(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda tidak berhak mempublish materi ini'}), 403

    data = request.get_json(silent=True) or {}
    requested = data.get('status')
    if requested in ('draft', 'published'):
        material.status = requested
    else:
        material.status = 'draft' if material.status == 'published' else 'published'

    material.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'message': f'Materi berhasil {"dipublikasikan" if material.status == "published" else "disimpan sebagai draft"}',
        'status': material.status,
    }), 200


# ============================================================
# SECTIONS
# ============================================================

@jwt_required()
def create_section(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Judul section wajib diisi'}), 400

    max_pos = max([s.position for s in material.sections], default=-1)
    section = MaterialSection(
        material_id=material.id,
        title=title,
        position=max_pos + 1,
    )
    db.session.add(section)
    db.session.commit()

    return jsonify({'message': 'Section berhasil dibuat', 'section': {
        'id': section.id, 'title': section.title, 'position': section.position, 'contents': [],
    }}), 201


@jwt_required()
def update_section(section_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    section = MaterialSection.query.get(section_id)
    if not section:
        return jsonify({'error': 'Section not found'}), 404

    if not _can_manage(section.material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    data = request.get_json(silent=True) or {}
    if 'title' in data and data['title'] is not None:
        title = str(data['title']).strip()
        if not title:
            return jsonify({'error': 'Judul section wajib diisi'}), 400
        section.title = title
    if 'position' in data and data['position'] is not None:
        section.position = int(data['position'])

    db.session.commit()
    return jsonify({'message': 'Section berhasil diperbarui', 'section': {
        'id': section.id, 'title': section.title, 'position': section.position,
    }}), 200


@jwt_required()
def delete_section(section_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    section = MaterialSection.query.get(section_id)
    if not section:
        return jsonify({'error': 'Section not found'}), 404

    if not _can_manage(section.material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    material = section.material
    db.session.delete(section)
    db.session.commit()

    for i, s in enumerate(sorted(material.sections, key=lambda x: x.position)):
        s.position = i
    db.session.commit()

    return jsonify({'message': 'Section berhasil dihapus'}), 200


@jwt_required()
def reorder_sections(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    data = request.get_json(silent=True) or {}
    section_ids = data.get('section_ids') or []
    section_map = {s.id: s for s in material.sections}

    for i, sid in enumerate(section_ids):
        section = section_map.get(int(sid))
        if section:
            section.position = i

    db.session.commit()
    return jsonify({'message': 'Urutan section berhasil diperbarui'}), 200


# ============================================================
# CONTENT BLOCKS
# ============================================================

@jwt_required()
def create_content(section_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    section = MaterialSection.query.get(section_id)
    if not section:
        return jsonify({'error': 'Section not found'}), 404

    if not _can_manage(section.material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    data = request.get_json(silent=True) or {}
    block_type = data.get('type')
    block_data = data.get('data') or {}
    allowed_types = ['text', 'heading', 'image', 'video', 'pdf', 'link', 'box', 'question', 'quiz']

    if block_type not in allowed_types:
        return jsonify({'error': f'Tipe komponen "{block_type}" tidak dikenal'}), 400

    max_pos = max([c.position for c in section.contents], default=-1)
    content = MaterialContent(
        section_id=section.id,
        type=block_type,
        data=block_data,
        position=max_pos + 1,
    )
    db.session.add(content)
    db.session.commit()

    return jsonify({
        'message': 'Komponen berhasil ditambahkan',
        'content': _serialize_content(content),
    }), 201


@jwt_required()
def update_content(content_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    content = MaterialContent.query.get(content_id)
    if not content:
        return jsonify({'error': 'Content not found'}), 404

    if not _can_manage(content.section.material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    data = request.get_json(silent=True) or {}
    if 'type' in data and data['type']:
        allowed_types = ['text', 'heading', 'image', 'video', 'pdf', 'link', 'box', 'question', 'quiz']
        if data['type'] not in allowed_types:
            return jsonify({'error': f'Tipe komponen "{data["type"]}" tidak dikenal'}), 400
        content.type = data['type']
    if 'data' in data and isinstance(data['data'], dict):
        content.data = data['data']

    db.session.commit()
    return jsonify({
        'message': 'Komponen berhasil diperbarui',
        'content': _serialize_content(content),
    }), 200


@jwt_required()
def delete_content(content_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    content = MaterialContent.query.get(content_id)
    if not content:
        return jsonify({'error': 'Content not found'}), 404

    if not _can_manage(content.section.material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    section = content.section
    db.session.delete(content)
    db.session.commit()

    for i, c in enumerate(sorted(section.contents, key=lambda x: x.position)):
        c.position = i
    db.session.commit()

    return jsonify({'message': 'Komponen berhasil dihapus'}), 200


@jwt_required()
def reorder_contents(section_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    section = MaterialSection.query.get(section_id)
    if not section:
        return jsonify({'error': 'Section not found'}), 404

    if not _can_manage(section.material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    data = request.get_json(silent=True) or {}
    content_ids = data.get('content_ids') or []
    content_map = {c.id: c for c in section.contents}

    for i, cid in enumerate(content_ids):
        content = content_map.get(int(cid))
        if content:
            content.position = i

    db.session.commit()
    return jsonify({'message': 'Urutan komponen berhasil diperbarui'}), 200


# ============================================================
# FILES
# ============================================================

@jwt_required()
def upload_material_file(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'File tidak ditemukan'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'Tipe file tidak diizinkan (pdf, docx, doc, txt, jpg, jpeg, png, webp, mp4)'}), 400

    saved, err = _save_uploaded_file(file)
    if err:
        return jsonify({'error': err}), 400

    try:
        new_file = MaterialFile(
            material_id=material.id,
            original_name=file.filename,
            file_name=saved['name'],
            file_size=os.path.getsize(saved['path']),
            file_type=file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else '',
            file_url=saved['url'],
        )
        db.session.add(new_file)
        db.session.commit()
    except Exception as e:
        if os.path.exists(saved['path']):
            os.remove(saved['path'])
        db.session.rollback()
        traceback.print_exc()
        return jsonify({'error': 'Gagal menyimpan file'}), 500

    return jsonify({
        'message': 'File berhasil diunggah',
        'file': {
            'id': new_file.id,
            'original_name': new_file.original_name,
            'file_name': new_file.file_name,
            'file_size': new_file.file_size,
            'file_type': new_file.file_type,
            'file_url': new_file.file_url,
        },
    }), 201


@jwt_required()
def delete_material_file(material_id, file_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if not _can_manage(material, user):
        return jsonify({'error': 'Anda hanya dapat mengubah materi milik sendiri'}), 403

    material_file = MaterialFile.query.filter_by(id=file_id, material_id=material_id).first()
    if not material_file:
        return jsonify({'error': 'File not found'}), 404

    file_path = os.path.join(_upload_folder(), material_file.file_name)

    db.session.delete(material_file)
    db.session.commit()

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print("Failed to delete file from disk:", e)

    return jsonify({'message': 'File berhasil dihapus'}), 200


# ============================================================
# PROGRESS (siswa)
# ============================================================

@jwt_required()
def record_progress(material_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role != 'student':
        return jsonify({'error': 'Hanya siswa yang dapat mencatat progress'}), 403

    material = Material.query.get(material_id)
    if not material:
        return jsonify({'error': 'Material not found'}), 404

    if material.status != 'published':
        return jsonify({'error': 'Materi belum dipublikasikan'}), 403

    data = request.get_json(silent=True) or {}
    section_id = data.get('section_id')
    if not section_id:
        return jsonify({'error': 'section_id wajib diisi'}), 400

    section = MaterialSection.query.filter_by(id=section_id, material_id=material.id).first()
    if not section:
        return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 404

    existing = MaterialProgress.query.filter_by(
        material_id=material.id, section_id=section.id, student_id=user.id
    ).first()
    if existing:
        return jsonify({'message': 'Progress sudah tercatat', 'recorded': False}), 200

    try:
        db.session.add(MaterialProgress(
            material_id=material.id,
            section_id=section.id,
            student_id=user.id,
        ))
        db.session.commit()
        log_activity(user.id, material.id, 'section_opened', section_id=section.id, silent=True)
        log_activity(user.id, material.id, 'section_completed', section_id=section.id, silent=True)
        return jsonify({'message': 'Progress tercatat', 'recorded': True}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Gagal mencatat progress: {str(e)}'}), 500


# ============================================================
# STUDENT LEARNING (state, bookmark, note, answer)
# ============================================================

def _student_learning_guard(material_id):
    user = _get_current_user()
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


def _student_state_payload(material_id, user):
    done_ids = {
        r.section_id for r in MaterialProgress.query.filter_by(
            material_id=material_id, student_id=user.id
        ).all()
    }
    material = Material.query.get(material_id)
    progress = _student_progress_info(material, done_ids)
    state = MaterialStudentState.query.filter_by(
        material_id=material_id, student_id=user.id
    ).first()
    last_section = state.last_section if state and state.last_section_id else None
    return {
        'material_id': material_id,
        'student_progress': progress,
        'completed_section_ids': sorted(done_ids),
        'last_section_id': last_section.id if last_section else None,
        'last_section_title': last_section.title if last_section else None,
        'completed': bool(state.completed if state else False) or progress['finished'],
        'last_accessed': state.last_accessed.isoformat() if state and state.last_accessed else None,
    }


@jwt_required()
def get_material_student_state(material_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code
    return jsonify(_student_state_payload(material_id, user)), 200


@jwt_required()
def update_material_student_state(material_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code

    data = request.get_json(silent=True) or {}
    state = MaterialStudentState.query.filter_by(
        material_id=material.id, student_id=user.id
    ).first()
    if not state:
        state = MaterialStudentState(material_id=material.id, student_id=user.id, completed=False)
        db.session.add(state)

    section_id = data.get('section_id')
    if section_id is not None:
        section = MaterialSection.query.filter_by(id=int(section_id), material_id=material.id).first()
        if not section:
            return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 404
        state.last_section_id = section.id

    state.last_accessed = datetime.utcnow()

    if data.get('completed') is True:
        state.completed = True
        state.completed_at = state.completed_at or datetime.utcnow()

    done_ids = {
        r.section_id for r in MaterialProgress.query.filter_by(
            material_id=material.id, student_id=user.id
        ).all()
    }
    progress = _student_progress_info(material, done_ids)
    if progress['finished']:
        state.completed = True
        state.completed_at = state.completed_at or datetime.utcnow()

    try:
        db.session.commit()
        if state.completed:
            log_activity(user.id, material.id, 'material_completed',
                         section_id=state.last_section_id, silent=True)
            try:
                from src.ml.recommendation import mark_completed
                mark_completed(user.id, material.id)
            except Exception:
                db.session.rollback()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Gagal menyimpan posisi belajar: {str(e)}'}), 500

    return jsonify({'message': 'Posisi belajar tersimpan', 'state': _student_state_payload(material.id, user)}), 200


@jwt_required()
def submit_student_answer(material_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code

    data = request.get_json(silent=True) or {}
    section_id = data.get('section_id')
    content_id = data.get('content_id')
    selected_answer = data.get('selected_answer')

    if section_id is None or content_id is None or selected_answer is None:
        return jsonify({'error': 'section_id, content_id, dan selected_answer wajib diisi'}), 400

    try:
        section = MaterialSection.query.filter_by(id=int(section_id), material_id=material.id).first()
    except (TypeError, ValueError):
        section = None
    if not section:
        return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 404

    try:
        content = MaterialContent.query.filter_by(id=int(content_id), section_id=section.id).first()
    except (TypeError, ValueError):
        content = None
    if not content:
        return jsonify({'error': 'Content tidak ditemukan pada section ini'}), 404

    content_data = dict(content.data) if isinstance(content.data, dict) else {}
    expected = content_data.get('correct_answer')
    explanation = content_data.get('explanation')
    question_index = data.get('question_index')
    if expected is None and isinstance(content_data.get('questions'), list):
        questions = content_data['questions']
        try:
            qi = int(question_index) if question_index is not None else None
        except (TypeError, ValueError):
            qi = None
        if qi is not None and 0 <= qi < len(questions):
            expected = questions[qi].get('correct_answer')
            explanation = questions[qi].get('explanation')
        else:
            for q in questions:
                if isinstance(q, dict) and q.get('correct_answer') is not None:
                    expected = q.get('correct_answer')
                    explanation = q.get('explanation')
                    break

    try:
        selected = int(selected_answer)
    except (TypeError, ValueError):
        return jsonify({'error': 'selected_answer harus berupa angka'}), 400

    try:
        expected_int = int(expected) if expected is not None else None
    except (TypeError, ValueError):
        expected_int = None
    is_correct = (expected_int is not None and selected == expected_int)
    if expected_int is None:
        is_correct = bool(data.get('is_correct', False))

    try:
        db.session.add(StudentAnswer(
            student_id=user.id,
            material_id=material.id,
            section_id=section.id,
            content_id=content.id,
            selected_answer=selected,
            is_correct=is_correct,
            question_index=data.get('question_index'),
        ))
        db.session.commit()
        mark_content_viewed(user.id, material.id, content.id, silent=True)
        log_activity(user.id, material.id, 'question_answered', section_id=section.id, content_id=content.id,
                     data={'correct': is_correct, 'question_index': data.get('question_index')}, silent=True)
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Gagal menyimpan jawaban: {str(e)}'}), 500

    return jsonify({
        'message': 'Jawaban tersimpan',
        'correct': is_correct,
        'explanation': explanation or None,
    }), 201


@jwt_required()
def get_material_bookmarks(material_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code

    bookmarks = MaterialBookmark.query.filter_by(
        material_id=material.id, student_id=user.id
    ).all()
    result = [{
        'id': b.id,
        'section_id': b.section_id,
        'content_id': b.content_id,
        'section_title': b.section.title if b.section else None,
        'created_at': b.created_at.isoformat() if b.created_at else None,
    } for b in bookmarks]
    return jsonify(result), 200


@jwt_required()
def create_material_bookmark(material_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code

    data = request.get_json(silent=True) or {}
    section_id = data.get('section_id')
    content_id = data.get('content_id')

    if content_id is not None:
        content = MaterialContent.query.get(int(content_id))
        if not content:
            return jsonify({'error': 'Content tidak ditemukan'}), 404
        section_id = content.section_id
    elif section_id is not None:
        section = MaterialSection.query.filter_by(id=int(section_id), material_id=material.id).first()
        if not section:
            return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 404
    else:
        return jsonify({'error': 'section_id atau content_id wajib diisi'}), 400

    existing = MaterialBookmark.query.filter_by(
        student_id=user.id, material_id=material.id,
        section_id=section_id, content_id=content_id,
    ).first()
    if existing:
        return jsonify({'message': 'Bookmark sudah tersimpan', 'bookmark': {'id': existing.id}}), 200

    bookmark = MaterialBookmark(
        student_id=user.id, material_id=material.id,
        section_id=section_id, content_id=content_id,
    )
    db.session.add(bookmark)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Gagal menyimpan bookmark: {str(e)}'}), 500

    return jsonify({'message': 'Bookmark tersimpan', 'bookmark': {
        'id': bookmark.id, 'section_id': bookmark.section_id, 'content_id': bookmark.content_id,
    }}), 201


@jwt_required()
def delete_material_bookmark(material_id, bookmark_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code

    bookmark = MaterialBookmark.query.filter_by(id=bookmark_id, material_id=material.id, student_id=user.id).first()
    if not bookmark:
        return jsonify({'error': 'Bookmark tidak ditemukan'}), 404

    db.session.delete(bookmark)
    db.session.commit()
    return jsonify({'message': 'Bookmark dihapus'}), 200


@jwt_required()
def get_material_notes(material_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code

    notes = StudentNote.query.filter_by(
        material_id=material.id, student_id=user.id
    ).order_by(StudentNote.updated_at.desc()).all()
    result = [{
        'id': n.id,
        'section_id': n.section_id,
        'content_id': n.content_id,
        'section_title': n.section.title if n.section else None,
        'note': n.note,
        'created_at': n.created_at.isoformat() if n.created_at else None,
        'updated_at': n.updated_at.isoformat() if n.updated_at else None,
    } for n in notes]
    return jsonify(result), 200


@jwt_required()
def create_material_note(material_id):
    user, material, err, code = _student_learning_guard(material_id)
    if err:
        return err, code

    data = request.get_json(silent=True) or {}
    note_text = (data.get('note') or '').strip()
    if not note_text:
        return jsonify({'error': 'Isi catatan tidak boleh kosong'}), 400

    section_id = data.get('section_id')
    content_id = data.get('content_id')

    if content_id is not None:
        content = MaterialContent.query.get(int(content_id))
        if not content:
            return jsonify({'error': 'Content tidak ditemukan'}), 404
        section_id = content.section_id
    elif section_id is not None:
        section = MaterialSection.query.filter_by(id=int(section_id), material_id=material.id).first()
        if not section:
            return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 404

    existing = StudentNote.query.filter_by(
        student_id=user.id, material_id=material.id,
        section_id=section_id, content_id=content_id,
    ).first()
    try:
        if existing:
            existing.note = note_text
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({'message': 'Catatan diperbarui', 'note': {'id': existing.id}}), 200

        note = StudentNote(
            student_id=user.id, material_id=material.id,
            section_id=section_id, content_id=content_id, note=note_text,
        )
        db.session.add(note)
        db.session.commit()
        return jsonify({'message': 'Catatan tersimpan', 'note': {'id': note.id}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Gagal menyimpan catatan: {str(e)}'}), 500


@jwt_required()
def update_student_note(note_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403

    note = StudentNote.query.filter_by(id=note_id, student_id=user.id).first()
    if not note:
        return jsonify({'error': 'Catatan tidak ditemukan'}), 404

    data = request.get_json(silent=True) or {}
    note_text = (data.get('note') or '').strip()
    if not note_text:
        return jsonify({'error': 'Isi catatan tidak boleh kosong'}), 400

    note.note = note_text
    note.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Catatan diperbarui'}), 200


@jwt_required()
def delete_student_note(note_id):
    user = _get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403

    note = StudentNote.query.filter_by(id=note_id, student_id=user.id).first()
    if not note:
        return jsonify({'error': 'Catatan tidak ditemukan'}), 404

    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Catatan dihapus'}), 200
