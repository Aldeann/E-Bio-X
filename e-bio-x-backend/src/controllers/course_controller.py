from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.course import Course
from src.models.enrollment import Enrollment
from src.models.user import User
from src.config.database import db


def _user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _is_course_owner(course, user):
    return str(course.teacher_id) == str(user.id)


def _can_manage_course(course, user):
    return user.role == 'admin' or _is_course_owner(course, user)


def _is_enrolled(course, user):
    return Enrollment.query.filter_by(student_id=user.id, course_id=course.id).first() is not None

@jwt_required()
def create_course():
    user = _user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({"error": "Akses khusus guru"}), 403

    data = request.get_json(silent=True) or {}
    name = data.get('name')
    
    if not name:
        return jsonify({"error": "Course's name required"}), 400
    
    new_course = Course(
        name=name,
        teacher_id=user.id
    )
    db.session.add(new_course)
    db.session.commit()

    return jsonify({
        "message": "Course created successfully",
        "data": {
            "id": new_course.id,
            "name": new_course.name,
            "created_at": new_course.created_at.isoformat()
        }
    }), 201

@jwt_required()
def get_courses():
    user = _user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role not in ('admin', 'teacher'):
        return jsonify({"error": "Akses khusus admin/guru"}), 403
    courses = Course.query.all()

    result = []
    for course in courses:
        result.append({
            "id": course.id,
            "name": course.name,
            "teacher": course.teacher.name,
            "created_at": course.created_at.isoformat(),
            "code": f"KLS{course.id:03d}", 
            "students": len(course.enrollments)
        })

    return jsonify(result), 200

@jwt_required()
def get_teacher_courses():
    teacher_id = get_jwt_identity()
    courses = Course.query.filter_by(teacher_id=teacher_id).all()

    result = []
    for course in courses:
        result.append({
            "id": course.id,
            "name": course.name,
            "created_at": course.created_at.isoformat(),
            "code": f"KLS{course.id:03d}",
            "students": len(course.enrollments)
        })

    return jsonify(result), 200

@jwt_required()
def get_student_courses():
    student_id = get_jwt_identity()

    enrollments = Enrollment.query.filter_by(student_id=student_id).all()

    result = []
    for enrollment in enrollments:
        course = enrollment.course
        result.append({
            "id": course.id,
            "name": course.name,
            "teacher": course.teacher.name,
            "created_at": course.created_at.isoformat(),
            "code": f"KLS{course.id:03d}",
            "students": len(course.enrollments)
        })

    return jsonify(result), 200

@jwt_required()
def enroll(course_id):
    user = _user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role != 'student':
        return jsonify({"error": "Endpoint ini khusus siswa"}), 403
    if course_id.startswith("KLS") and course_id[3:].isdigit():
        course_id = int(course_id[3:])
    else:
        return jsonify({"error": "Invalid course code format"}), 400
    course = Course.query.get(course_id)
    
    if not course:
        return jsonify({"error": "Course not found"}), 404
    
    student_id = user.id
    
    enroll = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if enroll:
        return jsonify({"error": f"You already enrolled in {course.name}"}), 400
    
    enroll = Enrollment(
        student_id=student_id,
        course_id=course_id
    )
    db.session.add(enroll)
    db.session.commit()

    return jsonify({
        "message": f"Enroll successfully to {course.name}",
    }), 200

@jwt_required()
def out(course_id):
    user = _user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role != 'student':
        return jsonify({"error": "Endpoint ini khusus siswa"}), 403
    if course_id.startswith("KLS") and course_id[3:].isdigit():
        course_id = int(course_id[3:])

    course = Course.query.get(course_id)
    
    if not course:
        return jsonify({"error": "Course not found"}), 404
    
    student_id = user.id
    
    enroll = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if not enroll:
        return jsonify({"error": f"You are not enrolled in {course.name}"}), 400
    
    db.session.delete(enroll)
    db.session.commit()

    return jsonify({
        "message": f"Successfully out from {course.name}",
    }), 200

@jwt_required()
def kick(course_id, student_id):
    user = _user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if course_id.startswith("KLS") and course_id[3:].isdigit():
        course_id = int(course_id[3:])
    course = Course.query.get(course_id)
    
    if not course:
        return jsonify({"error": "Course not found"}), 404
    
    if not _can_manage_course(course, user):
        return jsonify({"error": "Anda tidak berhak mengelola kelas ini"}), 403
    
    enroll = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
    if not enroll:
        return jsonify({"error": f"You are not enrolled in {course.name}"}), 400
    
    db.session.delete(enroll)
    db.session.commit()

    return jsonify({
        "message": f"Successfully out from {course.name}",
    }), 200

@jwt_required()
def get_course_by_id(course_id):
    user = _user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    if user.role == 'student':
        if not _is_enrolled(course, user):
            return jsonify({"error": "Anda bukan anggota kelas ini"}), 403
    elif user.role not in ('teacher', 'admin'):
        return jsonify({"error": "Akses ditolak"}), 403

    if user.role != 'admin' and user.role == 'teacher' and not _can_manage_course(course, user):
        return jsonify({"error": "Anda tidak berhak mengelola kelas ini"}), 403

    students = []
    for enrollment in course.enrollments:
        quiz_rows = [{
            "title": submission.quiz.title,
            "score": submission.score,
            "cluster": submission.cluster,
        } for submission in enrollment.student.quiz_results if submission.quiz.course_id == course.id] if user.role != 'student' else []
        students.append({
            "id": enrollment.student.id,
            "name": enrollment.student.name,
            "email": enrollment.student.email,
            "quizes": quiz_rows,
        })
        
    return jsonify({
        "name": course.name,
        "created_at": course.created_at.isoformat(),
        "code": f"KLS{course.id:03d}",
        "teacher": course.teacher.name,
        "students_count": len(course.enrollments),
        "students": students
    }), 200

@jwt_required()
def delete_course(course_id):
    user = _user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    if not _can_manage_course(course, user):
        return jsonify({"error": "Anda tidak berhak menghapus kelas ini"}), 403

    try:
        for enrollment in course.enrollments:
            db.session.delete(enrollment)
        
        db.session.delete(course)
    except Exception:
        db.session.rollback()
        return jsonify({
            "message": f"Failed to delete {course.name}" 
        }), 500
        
    db.session.commit()
        
    return jsonify({
        "message":"Course deleted successfully" 
    }), 200

