from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.config.database import db
from src.models.discussion import DiscussionThread, DiscussionReply
from src.models.course import Course
from src.models.enrollment import Enrollment
from src.models.user import User


def _is_admin(user_id):
    user = User.query.get(user_id)
    return bool(user and user.role == 'admin')


def _is_member(course, user_id):
    if _is_admin(user_id):
        return True
    if str(course.teacher_id) == str(user_id):
        return True
    enroll = Enrollment.query.filter_by(student_id=user_id, course_id=course.id).first()
    return enroll is not None

def _can_delete(author_id, course, user_id):
    if _is_admin(user_id):
        return True
    if str(author_id) == str(user_id):
        return True
    if str(course.teacher_id) == str(user_id):
        return True
    return False

@jwt_required()
def get_threads_by_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    user_id = get_jwt_identity()
    if not _is_member(course, user_id):
        return jsonify({"error": "You are not a member of this course"}), 403

    threads = DiscussionThread.query.filter_by(course_id=course_id).order_by(
        DiscussionThread.is_pinned.desc(), DiscussionThread.created_at.desc()
    ).all()

    result = [{
        "id": t.id,
        "title": t.title,
        "content": t.content,
        "is_pinned": t.is_pinned,
        "created_at": t.created_at.isoformat(),
        "author": t.author.name,
        "author_id": t.author.id,
        "replies_count": len(t.replies),
        "last_reply_at": t.replies[-1].created_at.isoformat() if t.replies else None,
        "can_delete": _can_delete(t.author.id, course, user_id),
    } for t in threads]

    return jsonify({"data": result}), 200

@jwt_required()
def create_thread(course_id):
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    user_id = get_jwt_identity()
    if not _is_member(course, user_id):
        return jsonify({"error": "You are not a member of this course"}), 403

    data = request.get_json()
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400

    thread = DiscussionThread(
        course_id=course_id,
        user_id=user_id,
        title=title,
        content=content,
    )
    db.session.add(thread)
    db.session.commit()

    return jsonify({
        "message": "Thread created successfully",
        "data": {
            "id": thread.id,
            "title": thread.title,
        }
    }), 201

@jwt_required()
def get_thread_by_id(thread_id):
    thread = DiscussionThread.query.get(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404

    user_id = get_jwt_identity()
    if not _is_member(thread.course, user_id):
        return jsonify({"error": "You are not a member of this course"}), 403

    replies = [{
        "id": r.id,
        "content": r.content,
        "created_at": r.created_at.isoformat(),
        "author": r.author.name,
        "author_id": r.author.id,
        "can_delete": _can_delete(r.author.id, thread.course, user_id),
    } for r in thread.replies]

    return jsonify({
        "id": thread.id,
        "title": thread.title,
        "content": thread.content,
        "is_pinned": thread.is_pinned,
        "created_at": thread.created_at.isoformat(),
        "course_id": thread.course_id,
        "course_name": thread.course.name,
        "author": thread.author.name,
        "author_id": thread.author.id,
        "can_delete": _can_delete(thread.author.id, thread.course, user_id),
        "replies": replies,
    }), 200

@jwt_required()
def create_reply(thread_id):
    thread = DiscussionThread.query.get(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404

    user_id = get_jwt_identity()
    if not _is_member(thread.course, user_id):
        return jsonify({"error": "You are not a member of this course"}), 403

    data = request.get_json()
    content = (data.get("content") or "").strip()

    if not content:
        return jsonify({"error": "Content is required"}), 400

    reply = DiscussionReply(
        thread_id=thread_id,
        user_id=user_id,
        content=content,
    )
    db.session.add(reply)
    db.session.commit()

    return jsonify({
        "message": "Reply created successfully",
        "data": {
            "id": reply.id,
            "content": reply.content,
        }
    }), 201

@jwt_required()
def delete_thread(thread_id):
    thread = DiscussionThread.query.get(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404

    user_id = get_jwt_identity()
    if not _can_delete(thread.author.id, thread.course, user_id):
        return jsonify({"error": "You are not allowed to delete this thread"}), 403

    db.session.delete(thread)
    db.session.commit()

    return jsonify({"message": "Thread deleted successfully"}), 200

@jwt_required()
def delete_reply(reply_id):
    reply = DiscussionReply.query.get(reply_id)
    if not reply:
        return jsonify({"error": "Reply not found"}), 404

    user_id = get_jwt_identity()
    if not _can_delete(reply.author.id, reply.thread.course, user_id):
        return jsonify({"error": "You are not allowed to delete this reply"}), 403

    db.session.delete(reply)
    db.session.commit()

    return jsonify({"message": "Reply deleted successfully"}), 200

@jwt_required()
def toggle_pin_thread(thread_id):
    thread = DiscussionThread.query.get(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404

    user_id = get_jwt_identity()
    if str(thread.course.teacher_id) != str(user_id):
        return jsonify({"error": "Only the course teacher can pin threads"}), 403

    thread.is_pinned = not thread.is_pinned
    db.session.commit()

    return jsonify({
        "message": "Thread pinned" if thread.is_pinned else "Thread unpinned",
        "is_pinned": thread.is_pinned,
    }), 200