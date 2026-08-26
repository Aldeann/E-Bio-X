from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from src.models.user import User
from src.models.quiz import Quiz
from src.models.question import Question
from src.models.option import Option
from src.models.submission import Submission
from src.models.answer import Answer
from src.models.enrollment import Enrollment
from src.models.course import Course
from src.config.database import db


def _legacy_user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _legacy_can_manage_quiz(quiz, user):
    if user.role == 'admin':
        return True
    if user.role != 'teacher':
        return False
    if quiz.course_id and quiz.course:
        return str(quiz.course.teacher_id) == str(user.id)
    return False


def _legacy_student_enrolled(course_id, user):
    return Enrollment.query.filter_by(student_id=user.id, course_id=course_id).first() is not None

@jwt_required()
def create_quiz():
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({"error": "Akses khusus guru"}), 403

    data = request.get_json() or {}
    course_id = data.get('course_id')
    title = data.get('title')

    if not course_id or not title:
        return jsonify({"error": "Course ID and title are required"}), 400

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    if user.role != 'admin' and str(course.teacher_id) != str(user.id):
        return jsonify({"error": "Anda tidak berhak membuat kuis di kelas ini"}), 403

    if Quiz.query.filter_by(title=title, course_id=course_id).first():
        return jsonify({"error": "Quiz with this title already exists"}), 400

    try:
        quiz = Quiz(title=title, course_id=course_id, is_closed=True)
        db.session.add(quiz)

        questions = data.get('questions', [])
        for q in questions:
            question_text = q.get('question_text')
            new_question = Question(quiz=quiz, text=question_text)
            db.session.add(new_question)

            options = q.get('options', [])
            for o in options:
                option_text = o.get('option_text')
                is_correct = o.get('is_correct', False)
                new_option = Option(
                    question=new_question,
                    option_text=option_text,
                    is_correct=is_correct
                )
                db.session.add(new_option)

        db.session.commit()
        return jsonify({"message": "Quiz created successfully", "quiz_id": quiz.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error creating quiz: {str(e)}"}), 500


# DEPRECATED (audit 14.8): gunakan API kanonik /api/teacher/quizzes*
@jwt_required()
def toggle_open_quiz(quiz_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    if not _legacy_can_manage_quiz(quiz, user):
        return jsonify({"error": "Anda tidak berhak mengelola kuis ini"}), 403
    
    try:
        quiz.is_closed = not quiz.is_closed
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error toggling quiz: {str(e)}"}), 500

    status = 'closed' if quiz.is_closed else 'opened'
    return jsonify({"message": f"Quiz {status} successfully"}), 200

@jwt_required()
def edit_quiz_title(quiz_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    if not _legacy_can_manage_quiz(quiz, user):
        return jsonify({"error": "Anda tidak berhak mengelola kuis ini"}), 403
    
    try:
        title = request.get_json().get('title')
        if not title:
            return jsonify({"error": "Title is required"}), 400
        quiz.title = title
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error editing quiz: {str(e)}"}), 500
    
    return jsonify({"message": "Quiz edited successfully"}), 200

@jwt_required()
def edit_question(question_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404
    if not question.quiz_id or not _legacy_can_manage_quiz(question.quiz, user):
        return jsonify({"error": "Anda tidak berhak mengelola soal ini"}), 403
    
    try:
        question_text = request.get_json().get('question_text')
        if not question_text:
            return jsonify({"error": "Question text is required"}), 400
        question.text = question_text
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error editing quiz: {str(e)}"}), 500
    
    return jsonify({"message": "Question edited successfully"}), 200

@jwt_required()
def edit_option(option_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    option = Option.query.get(option_id)
    if not option:
        return jsonify({"error": "Option not found"}), 404
    question = Question.query.get(option.question_id)
    if not question or not question.quiz_id or not _legacy_can_manage_quiz(question.quiz, user):
        return jsonify({"error": "Anda tidak berhak mengelola opsi ini"}), 403
    
    try:
        data = request.get_json()
        option_text = data.get('option_text')
        is_correct = data.get('is_correct')

        if option_text:
            option.text = option_text

        if is_correct is not None:
            question = Question.query.get(option.question_id)
            other_options = Option.query.filter_by(question_id=question.id).all()

            if is_correct is True:
                for o in other_options:
                    o.is_correct = (o.id == option.id)
            else:
                option.is_correct = False

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error editing quiz: {str(e)}"}), 500
    
    return jsonify({"message": "Option edited successfully"}), 200

# DEPRECATED (audit 14.8): gunakan API kanonik /api/teacher/quizzes*
@jwt_required()
def get_quiz_by_id(quiz_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    if user.role == 'student':
        permitted = False
        if quiz.course_id:
            permitted = _legacy_student_enrolled(quiz.course_id, user)
        elif quiz.material_id and quiz.material:
            from src.controllers.material_controller import _can_student_access
            permitted = quiz.material.status == 'published' and _can_student_access(quiz.material, user)
        if not permitted:
            return jsonify({"error": "Anda bukan anggota kelas kuis ini"}), 403
        access = False
    elif user.role in ('teacher', 'admin'):
        if user.role == 'teacher' and quiz.course_id and str(quiz.course.teacher_id) != str(user.id):
            return jsonify({"error": "Anda tidak berhak mengakses kuis ini"}), 403
        access = True
    else:
        return jsonify({"error": "Akses ditolak"}), 403

    return jsonify({
        "quiz_id": quiz.id,
        "course_id": quiz.course_id,
        "title": quiz.title,
        "is_closed": quiz.is_closed,
        "created_at": quiz.created_at,
        "questions": [
            {
                "question_id": q.id,
                "question_text": q.text,
                "options": [
                    {
                        "option_id": o.id,
                        "option_text": o.option_text,
                        "is_correct": o.is_correct if access else 'hidden'
                    }
                    for o in q.options
                ],
            }
            for q in quiz.questions
        ],
    }), 200

# DEPRECATED (audit 14.8): gunakan API kanonik /api/teacher/quizzes*
@jwt_required()
def get_quizzes_by_course(course_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    if user.role == 'student':
        if not _legacy_student_enrolled(course_id, user):
            return jsonify({"error": "Anda bukan anggota kelas ini"}), 403
    elif user.role not in ('teacher', 'admin'):
        return jsonify({"error": "Akses ditolak"}), 403
    elif user.role == 'teacher' and str(course.teacher_id) != str(user.id):
        return jsonify({"error": "Anda tidak berhak mengakses kelas ini"}), 403

    quizzes = Quiz.query.filter_by(course_id=course_id).all()
    if user.role == 'student':
        quizzes = [q for q in quizzes if q.status == 'published']

    student_id = user.id
    result = []
    for quiz in quizzes:
        entry = {
            "quiz_id": quiz.id,
            "title": quiz.title,
            "is_closed": quiz.is_closed,
            "questions": len(quiz.questions),
            "created_at": quiz.created_at,
        }
        if user.role == 'student':
            done = Submission.query.filter(
                Submission.student_id == student_id,
                Submission.quiz_id == quiz.id,
                Submission.status.in_(['submitted', 'timeout']),
            ).all()
            inprog = Submission.query.filter_by(
                student_id=student_id, quiz_id=quiz.id, status='in_progress'
            ).first()
            best = max([
                s.percentage if s.percentage is not None else s.score
                for s in done
            ], default=None)
            passing_grade = quiz.passing_grade or 75
            max_attempts = quiz.max_attempts or 1
            entry.update({
                "is_submited": bool(done),
                "score": best if best is not None else 0,
                "work_time": None,
                "student_status": 'in_progress' if inprog else ('completed' if done else 'not_started'),
                "attempts_used": len(done),
                "max_attempts": max_attempts,
                "best_percentage": best,
                "passed": best is not None and best >= passing_grade,
                "passing_grade": passing_grade,
            })
        result.append(entry)

    return (
        jsonify(
            {
                "quizzes": result,
            }
        ),
        200,
    )

# DEPRECATED (audit 14.8): gunakan API kanonik /api/teacher/quizzes*
@jwt_required()
def delete_quiz(quiz_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    if not _legacy_can_manage_quiz(quiz, user):
        return jsonify({"error": "Anda tidak berhak menghapus kuis ini"}), 403

    try:
        db.session.delete(quiz)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting quiz: {str(e)}")
        return jsonify({"error": f"Error deleting quiz: {str(e)}"}), 500

    return jsonify({"message": "Quiz deleted successfully"}), 200

@jwt_required()
def submit_quiz(quiz_id):
    try:
        quiz_id = int(quiz_id)
    except (TypeError, ValueError):
        quiz_id = None
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role != 'student':
        return jsonify({"error": "Endpoint ini khusus siswa"}), 403
    
    student_id = user.id
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    
    submission = Submission.query.filter_by(student_id=student_id, quiz_id=quiz_id).first()
    if submission:
        return jsonify({"error": "You have already submitted this quiz"}), 400
    
    data = request.get_json() or {}
    submited_answers = data.get('answers')
    
    if not submited_answers:
        return jsonify({"error": "Answers required"}), 400
    
    try:
        new_submission = Submission(
            student_id=student_id,
            quiz_id=quiz_id,
            work_time=data.get("work_time")
        )

        db.session.add(new_submission)
        db.session.flush()

        correct_answers = 0
        for ans in submited_answers:
            option = Option.query.get(ans.get('option_id'))
            question = Question.query.get(ans.get('question_id'))
            if not question or question.quiz_id != quiz_id or not option or option.question_id != question.id:
                db.session.rollback()
                return jsonify({"error": "Data jawaban tidak valid"}), 400
            if option.is_correct:
                correct_answers += 1
            
            answer = Answer(
                submission_id=new_submission.id,
                question_id=question.id,
                student_id=student_id,
                option_id=option.id
            )
            db.session.add(answer)
            
        total_questions = len(quiz.questions)
        
        if total_questions == 0:
            score = 0
        else:
            score = (correct_answers / total_questions) * 100

        new_submission.score = score
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error submitting quiz: {str(e)}"}), 500

    return jsonify({
        "message": "Quiz submitted successfully",
        "data": {
            "student": new_submission.student.name,
            "work_time": new_submission.work_time.strftime('%H:%M:%S'),
            "score": new_submission.score
        }
    }), 201

@jwt_required()
def remove_sumbission(quiz_id):
    student_id = get_jwt_identity()
    if not student_id:
        return jsonify({"error": "Student not authenticated"}), 401
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    
    submission = Submission.query.filter_by(student_id=student_id, quiz_id=quiz_id).first()
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    try:
        db.session.delete(submission)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error deleting submission: {str(e)}"}), 500
    
    return jsonify({"message": "Submission deleted successfully"}), 200
 
@jwt_required()
def get_submission_by_quiz(quiz_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    if not _legacy_can_manage_quiz(quiz, user):
        return jsonify({"error": "Anda tidak berhak melihat submission kuis ini"}), 403
    
    submissions = Submission.query.filter_by(quiz_id=quiz_id).all()
    if not submissions:
        return jsonify({"error": "Not submissions found"}), 404
    
    return (
        jsonify(
            {
                "quiz_id": quiz.id,
                "quiz_title": quiz.title,
                "submissions": [
                    {
                        "student": submission.student.name,
                        "student_id": submission.student.id,
                        "work_time": submission.work_time.strftime('%H:%M:%S'),
                        "score": submission.score,
                    } for submission in submissions
                ]
            }
        ),
        200,
    )

@jwt_required()
def get_my_submission_by_id(quiz_id):
    user = _legacy_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.role != 'student':
        return jsonify({"error": "Endpoint ini khusus siswa"}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    
    submission = Submission.query.filter_by(student_id=user.id, quiz_id=quiz_id).first()
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    answers = Answer.query.filter_by(submission_id=submission.id).all()
    
    return (
        jsonify(
            {
                "quiz_title": quiz.title,
                "submission": {
                    "student": submission.student.name,
                    "work_time": submission.work_time.strftime('%H:%M:%S'),
                    "score": submission.score,
                    "answers": [
                        {
                            "question_id": ans.question.id,
                            "option_id": ans.option.id,
                            "option_text": ans.option.option_text,
                            "is_correct": ans.option.is_correct
                        }
                        for ans in answers
                    ]
                }
            }
        ),
        200,
    )


# ============================================================
# INTERACTIVE QUIZ SYSTEM (materials-linked quizzes)
# ============================================================
from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.question_bank import QuestionBank
from src.models.question_bank_option import QuestionBankOption
from datetime import datetime, timedelta
from datetime import time as _dtime
import random

VALID_QUESTION_TYPES = ('multiple_choice', 'true_false')
VALID_DIFFICULTIES = ('easy', 'medium', 'hard')
VALID_QUIZ_STATUS = ('draft', 'published', 'archived')


def _cur_user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _is_teacher(user):
    return user and user.role in ('teacher', 'admin')


def _can_manage_quiz(quiz, user):
    if not user:
        return False
    if user.role == 'admin':
        return True
    if quiz.created_by:
        return quiz.created_by == user.id
    return quiz.course_id is not None and quiz.course and quiz.course.teacher_id == user.id


def _teacher_owns_material(user, material):
    return user.role == 'admin' or (material and material.teacher_id == user.id)


def _student_can_take(quiz, user):
    if not user or user.role != 'student':
        return False
    if quiz.status != 'published':
        return False
    if quiz.material_id:
        material = quiz.material
        if not material or material.status != 'published':
            return False
        if material.course_links:
            enrolled = {e.course_id for e in user.enrollments}
            return any(c.id in enrolled for c in material.course_links)
    return True


def _quiz_stats(quiz):
    subs = [s for s in quiz.submissions if s.status in ('submitted', 'timeout')]
    percentages = [s.percentage for s in subs if s.percentage is not None]
    n = len(percentages)
    return {
        'participants': len({s.student_id for s in subs}),
        'attempts': len(subs),
        'avg_percentage': round(sum(percentages) / n, 1) if n else 0,
        'highest': max(percentages) if n else 0,
        'lowest': min(percentages) if n else 0,
        'pass_rate': round(sum(1 for p in percentages if p >= (quiz.passing_grade or 75)) / n * 100, 1) if n else 0,
    }


def _serialize_quiz_teacher(quiz):
    material = quiz.material
    section = quiz.section
    return {
        'id': quiz.id,
        'title': quiz.title,
        'description': quiz.description,
        'course_id': quiz.course_id,
        'material_id': quiz.material_id,
        'material_title': material.title if material else None,
        'material_topic': material.topic if material else None,
        'section_id': quiz.section_id,
        'section_title': section.title if section else None,
        'duration': quiz.duration,
        'passing_grade': quiz.passing_grade,
        'max_attempts': quiz.max_attempts,
        'shuffle_questions': quiz.shuffle_questions,
        'shuffle_options': quiz.shuffle_options,
        'show_explanation': quiz.show_explanation,
        'status': quiz.status,
        'question_count': len(quiz.questions),
        'total_points': sum(q.points or 0 for q in quiz.questions),
        'created_at': quiz.created_at.isoformat() if quiz.created_at else None,
        'updated_at': quiz.updated_at.isoformat() if quiz.updated_at else None,
    }


def _serialize_question_teacher(q):
    options = [{
        'option_id': o.id,
        'option_text': o.option_text,
        'is_correct': o.is_correct,
        'order_index': o.order_index,
    } for o in sorted(q.options, key=lambda x: x.order_index)]
    return {
        'question_id': q.id,
        'question_text': q.text,
        'question_type': q.question_type,
        'difficulty': q.difficulty,
        'explanation': q.explanation,
        'points': q.points,
        'order_index': q.order_index,
        'bank_question_id': q.bank_question_id,
        'options': options,
    }


def _validate_question_payload(data, bank=False):
    qtype = (data.get('question_type') or 'multiple_choice')
    if qtype not in VALID_QUESTION_TYPES:
        return None, 'Tipe soal tidak didukung'
    question_text = (data.get('question_text') or '').strip()
    if not question_text:
        return None, 'Pertanyaan wajib diisi'
    difficulty = (data.get('difficulty') or 'medium')
    if difficulty not in VALID_DIFFICULTIES:
        return None, 'Tingkat kesulitan tidak valid'
    try:
        points = int(data.get('points') or 10)
    except (TypeError, ValueError):
        return None, 'Bobot soal tidak valid'
    if points < 0:
        return None, 'Bobot soal tidak boleh negatif'

    options = data.get('options') or []
    if qtype == 'multiple_choice':
        if len(options) < 2:
            return None, 'Soal pilihan ganda wajib memiliki minimal 2 pilihan'
    elif qtype == 'true_false':
        if len(options) == 0:
            options = [
                {'option_text': 'Benar', 'is_correct': False},
                {'option_text': 'Salah', 'is_correct': False},
            ]
            data = dict(data)
            data['options'] = options
        if len(options) != 2:
            return None, 'Soal benar/salah wajib memiliki 2 pilihan (Benar/Salah)'

    correct_count = 0
    seen_text = set()
    for o in options:
        text = (o.get('option_text') or '').strip()
        if not text:
            return None, 'Isi pilihan jawaban tidak boleh kosong'
        if text.lower() in seen_text:
            return None, 'Terdapat pilihan jawaban yang duplikat'
        seen_text.add(text.lower())
        if bool(o.get('is_correct')):
            correct_count += 1
    if correct_count != 1:
        return None, 'Setiap soal wajib memiliki tepat 1 jawaban benar'

    return {
        'question_type': qtype,
        'question_text': question_text,
        'difficulty': difficulty,
        'explanation': (data.get('explanation') or '').strip() or None,
        'points': points,
        'options': options,
    }, None


def _apply_options(question, options):
    for old in list(question.options):
        db.session.delete(old)
    for idx, o in enumerate(options):
        db.session.add(Option(
            question=question,
            option_text=(o.get('option_text') or '').strip(),
            is_correct=bool(o.get('is_correct')),
            order_index=idx,
        ))


# ---------------- TEACHER: quiz management ----------------

@jwt_required()
def get_teacher_quizzes():
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    if user.role == 'admin':
        quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    else:
        owned_course_ids = [c.id for c in user.courses] if hasattr(user, 'courses') else []
        quizzes = Quiz.query.filter(
            (Quiz.created_by == user.id) | ((Quiz.created_by.is_(None)) & (Quiz.course_id.in_(owned_course_ids)) if owned_course_ids else Quiz.created_by == user.id)
        ).order_by(Quiz.created_at.desc()).all()

    result = []
    for q in quizzes:
        item = _serialize_quiz_teacher(q)
        item['stats'] = _quiz_stats(q)
        result.append(item)
    return jsonify(result), 200


@jwt_required()
def create_quiz_teacher():
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Judul kuis wajib diisi'}), 400
    material_id = data.get('material_id')
    if not material_id:
        return jsonify({'error': 'Materi terkait wajib diisi'}), 400
    material = Material.query.get(int(material_id))
    if not material:
        return jsonify({'error': 'Materi tidak ditemukan'}), 404
    if not _teacher_owns_material(user, material):
        return jsonify({'error': 'Materi bukan milik Anda'}), 403

    section = None
    if data.get('section_id'):
        section = MaterialSection.query.filter_by(id=int(data['section_id']), material_id=material.id).first()
        if not section:
            return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 400

    status = data.get('status') or 'draft'
    if status not in VALID_QUIZ_STATUS:
        status = 'draft'

    if status == 'published':
        return jsonify({'error': 'Tambahkan soal terlebih dahulu di halaman builder, lalu publikasikan'}), 400

    try:
        passing_grade = int(data.get('passing_grade') or 75)
        max_attempts = int(data.get('max_attempts') or 1)
        duration = int(data['duration']) if data.get('duration') else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Nilai durasi/pass/lolos/kesempatan tidak valid'}), 400
    if not (0 <= passing_grade <= 100):
        return jsonify({'error': 'Passing grade harus antara 0-100'}), 400
    if max_attempts < 1:
        return jsonify({'error': 'Kesempatan minimal 1'}), 400

    quiz = Quiz(
        title=title,
        description=(data.get('description') or '').strip() or None,
        course_id=material.course_id,
        material_id=material.id,
        section_id=section.id if section else None,
        duration=duration,
        passing_grade=passing_grade,
        max_attempts=max_attempts,
        shuffle_questions=bool(data.get('shuffle_questions')),
        shuffle_options=bool(data.get('shuffle_options')),
        show_explanation=bool(data.get('show_explanation', True)),
        status=status,
        created_by=user.id,
        created_at=datetime.utcnow(),
    )
    db.session.add(quiz)
    db.session.commit()
    return jsonify({'message': 'Kuis berhasil dibuat', 'quiz': _serialize_quiz_teacher(quiz)}), 201


@jwt_required()
def get_teacher_quiz(quiz_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola kuis ini'}), 403

    item = _serialize_quiz_teacher(quiz)
    item['questions'] = [_serialize_question_teacher(q) for q in sorted(quiz.questions, key=lambda x: x.order_index)]
    item['stats'] = _quiz_stats(quiz)
    return jsonify(item), 200


@jwt_required()
def update_quiz_teacher(quiz_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola kuis ini'}), 403

    data = request.get_json(silent=True) or {}
    if 'title' in data and data.get('title'):
        quiz.title = (data['title'] or '').strip()
    if 'description' in data:
        quiz.description = (data.get('description') or '').strip() or None

    if 'material_id' in data and data.get('material_id'):
        material = Material.query.get(int(data['material_id']))
        if not material or not _teacher_owns_material(user, material):
            return jsonify({'error': 'Materi tidak valid'}), 400
        quiz.material_id = material.id
        quiz.course_id = material.course_id

    if 'section_id' in data:
        if data.get('section_id'):
            section = MaterialSection.query.filter_by(id=int(data['section_id']), material_id=quiz.material_id).first()
            if not section:
                return jsonify({'error': 'Section tidak ditemukan pada materi ini'}), 400
            quiz.section_id = section.id
        else:
            quiz.section_id = None

    try:
        if 'duration' in data:
            quiz.duration = int(data['duration']) if data.get('duration') else None
        if 'passing_grade' in data:
            quiz.passing_grade = int(data['passing_grade'])
        if 'max_attempts' in data:
            quiz.max_attempts = int(data['max_attempts'])
    except (TypeError, ValueError):
        return jsonify({'error': 'Nilai numerik tidak valid'}), 400
    if not (0 <= quiz.passing_grade <= 100):
        return jsonify({'error': 'Passing grade harus antara 0-100'}), 400
    if quiz.max_attempts < 1:
        return jsonify({'error': 'Kesempatan minimal 1'}), 400

    if 'shuffle_questions' in data:
        quiz.shuffle_questions = bool(data['shuffle_questions'])
    if 'shuffle_options' in data:
        quiz.shuffle_options = bool(data['shuffle_options'])
    if 'show_explanation' in data:
        quiz.show_explanation = bool(data['show_explanation'])
    if 'status' in data and data['status'] in VALID_QUIZ_STATUS:
        quiz.status = data['status']

    quiz.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Kuis berhasil diperbarui', 'quiz': _serialize_quiz_teacher(quiz)}), 200


@jwt_required()
def set_quiz_status(quiz_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola kuis ini'}), 403

    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if status not in VALID_QUIZ_STATUS:
        return jsonify({'error': 'Status tidak valid'}), 400
    if status == 'published' and len(quiz.questions) == 0:
        return jsonify({'error': 'Tambahkan minimal 1 soal sebelum mempublikasikan kuis'}), 400
    quiz.status = status
    quiz.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': f'Status kuis diperbarui menjadi {status}', 'quiz': _serialize_quiz_teacher(quiz)}), 200


@jwt_required()
def delete_quiz_teacher(quiz_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola kuis ini'}), 403
    db.session.delete(quiz)
    db.session.commit()
    return jsonify({'message': 'Kuis berhasil dihapus'}), 200


# ---------------- TEACHER: questions ----------------

@jwt_required()
def add_quiz_question(quiz_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola kuis ini'}), 403

    data = request.get_json(silent=True) or {}
    next_order = max([q.order_index for q in quiz.questions] or [-1]) + 1
    question_obj = None

    if data.get('bank_question_id'):
        bank = QuestionBank.query.get(int(data['bank_question_id']))
        if not bank:
            return jsonify({'error': 'Soal bank tidak ditemukan'}), 404
        if bank.teacher_id != user.id and user.role != 'admin':
            return jsonify({'error': 'Anda tidak berhak menggunakan soal bank tersebut'}), 403
        question_obj = Question(
            quiz_id=quiz.id,
            text=bank.question_text,
            question_type=bank.question_type,
            difficulty=bank.difficulty,
            explanation=bank.explanation,
            points=bank.points,
            order_index=next_order,
            bank_question_id=bank.id,
            created_at=datetime.utcnow(),
        )
        db.session.add(question_obj)
        db.session.flush()
        for idx, bo in enumerate(sorted(bank.options, key=lambda x: x.order_index)):
            db.session.add(Option(
                question=question_obj,
                option_text=bo.option_text,
                is_correct=bo.is_correct,
                order_index=idx,
            ))
    else:
        validated, err = _validate_question_payload(data)
        if err:
            return jsonify({'error': err}), 400
        question_obj = Question(
            quiz_id=quiz.id,
            text=validated['question_text'],
            question_type=validated['question_type'],
            difficulty=validated['difficulty'],
            explanation=validated['explanation'],
            points=validated['points'],
            order_index=next_order,
            created_at=datetime.utcnow(),
        )
        db.session.add(question_obj)
        db.session.flush()
        _apply_options(question_obj, validated['options'])

    quiz.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Soal berhasil ditambahkan', 'question': _serialize_question_teacher(question_obj)}), 201


@jwt_required()
def update_quiz_question(question_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    question = Question.query.get(question_id)
    if not question or not question.quiz_id:
        return jsonify({'error': 'Soal tidak ditemukan'}), 404
    if not _can_manage_quiz(question.quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola soal ini'}), 403

    data = request.get_json(silent=True) or {}
    validated, err = _validate_question_payload(data)
    if err:
        return jsonify({'error': err}), 400

    question.text = validated['question_text']
    question.question_type = validated['question_type']
    question.difficulty = validated['difficulty']
    question.explanation = validated['explanation']
    question.points = validated['points']
    question.updated_at = datetime.utcnow()
    _apply_options(question, validated['options'])
    question.quiz.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Soal berhasil diperbarui', 'question': _serialize_question_teacher(question)}), 200


@jwt_required()
def delete_quiz_question(question_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    question = Question.query.get(question_id)
    if not question or not question.quiz_id:
        return jsonify({'error': 'Soal tidak ditemukan'}), 404
    if not _can_manage_quiz(question.quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola soal ini'}), 403
    quiz = question.quiz
    db.session.delete(question)
    for idx, q in enumerate(sorted([x for x in quiz.questions], key=lambda x: x.order_index)):
        q.order_index = idx
    quiz.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Soal berhasil dihapus'}), 200


@jwt_required()
def duplicate_quiz_question(question_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    source = Question.query.get(question_id)
    if not source or not source.quiz_id:
        return jsonify({'error': 'Soal tidak ditemukan'}), 404
    if not _can_manage_quiz(source.quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola soal ini'}), 403
    quiz = source.quiz
    next_order = max([q.order_index for q in quiz.questions] or [-1]) + 1
    clone = Question(
        quiz_id=quiz.id,
        text=source.text,
        question_type=source.question_type,
        difficulty=source.difficulty,
        explanation=source.explanation,
        points=source.points,
        order_index=next_order,
        bank_question_id=source.bank_question_id,
        created_at=datetime.utcnow(),
    )
    db.session.add(clone)
    db.session.flush()
    for idx, o in enumerate(sorted(source.options, key=lambda x: x.order_index)):
        db.session.add(Option(question=clone, option_text=o.option_text, is_correct=o.is_correct, order_index=idx))
    quiz.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Soal berhasil diduplikasi', 'question': _serialize_question_teacher(clone)}), 201


@jwt_required()
def reorder_quiz_questions(quiz_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Anda tidak berhak mengelola kuis ini'}), 403
    data = request.get_json(silent=True) or {}
    ordered_ids = data.get('question_ids') or []
    by_id = {q.id: q for q in quiz.questions}
    for idx, qid in enumerate(ordered_ids):
        q = by_id.get(int(qid))
        if q:
            q.order_index = idx
    quiz.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Urutan soal diperbarui'}), 200


# ---------------- TEACHER: question bank ----------------

def _serialize_bank(bq, times_used=None):
    return {
        'id': bq.id,
        'question_text': bq.question_text,
        'question_type': bq.question_type,
        'topic': bq.topic,
        'difficulty': bq.difficulty,
        'explanation': bq.explanation,
        'points': bq.points,
        'times_used': times_used if times_used is not None else len(bq.quiz_questions),
        'created_at': bq.created_at.isoformat() if bq.created_at else None,
        'updated_at': bq.updated_at.isoformat() if bq.updated_at else None,
        'options': [{
            'option_id': o.id,
            'option_text': o.option_text,
            'is_correct': o.is_correct,
            'order_index': o.order_index,
        } for o in sorted(bq.options, key=lambda x: x.order_index)],
    }


@jwt_required()
def get_question_bank():
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    query = QuestionBank.query
    if user.role != 'admin':
        query = query.filter_by(teacher_id=user.id)
    data = request.args
    keyword = (data.get('q') or '').strip().lower()
    topic = (data.get('topic') or '').strip()
    difficulty = (data.get('difficulty') or '').strip()
    qtype = (data.get('type') or '').strip()
    if keyword:
        query = query.filter(QuestionBank.question_text.ilike(f'%{keyword}%'))
    if topic:
        query = query.filter(QuestionBank.topic == topic)
    if difficulty:
        query = query.filter(QuestionBank.difficulty == difficulty)
    if qtype:
        query = query.filter(QuestionBank.question_type == qtype)
    items = query.order_by(QuestionBank.created_at.desc()).all()
    usage_counts = {}
    if items:
        rows = (
            db.session.query(Question.bank_question_id, func.count(Question.id))
            .filter(Question.bank_question_id.in_([b.id for b in items]))
            .group_by(Question.bank_question_id)
            .all()
        )
        usage_counts = {bid: cnt for bid, cnt in rows}
    topics = sorted({b.topic for b in QuestionBank.query.filter_by(teacher_id=user.id).all() if b.topic})
    return jsonify({
        'data': [_serialize_bank(b, usage_counts.get(b.id, 0)) for b in items],
        'topics': topics,
    }), 200


@jwt_required()
def create_question_bank():
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    data = request.get_json(silent=True) or {}
    validated, err = _validate_question_payload(data, bank=True)
    if err:
        return jsonify({'error': err}), 400
    bq = QuestionBank(
        teacher_id=user.id,
        question_text=validated['question_text'],
        question_type=validated['question_type'],
        topic=(data.get('topic') or '').strip() or None,
        difficulty=validated['difficulty'],
        explanation=validated['explanation'],
        points=validated['points'],
        created_at=datetime.utcnow(),
    )
    db.session.add(bq)
    db.session.flush()
    for idx, o in enumerate(validated['options']):
        db.session.add(QuestionBankOption(
            bank_question_id=bq.id,
            option_text=(o.get('option_text') or '').strip(),
            is_correct=bool(o.get('is_correct')),
            order_index=idx,
        ))
    db.session.commit()
    return jsonify({'message': 'Soal bank berhasil ditambahkan', 'question': _serialize_bank(bq)}), 201


@jwt_required()
def update_question_bank(bank_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    bq = QuestionBank.query.get(bank_id)
    if not bq:
        return jsonify({'error': 'Soal bank tidak ditemukan'}), 404
    if bq.teacher_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Anda tidak berhak mengubah soal bank ini'}), 403
    data = request.get_json(silent=True) or {}
    validated, err = _validate_question_payload(data, bank=True)
    if err:
        return jsonify({'error': err}), 400
    bq.question_text = validated['question_text']
    bq.question_type = validated['question_type']
    bq.topic = (data.get('topic') or '').strip() or None
    bq.difficulty = validated['difficulty']
    bq.explanation = validated['explanation']
    bq.points = validated['points']
    bq.updated_at = datetime.utcnow()
    for old in list(bq.options):
        db.session.delete(old)
    for idx, o in enumerate(validated['options']):
        db.session.add(QuestionBankOption(
            bank_question_id=bq.id,
            option_text=(o.get('option_text') or '').strip(),
            is_correct=bool(o.get('is_correct')),
            order_index=idx,
        ))
    db.session.commit()
    return jsonify({'message': 'Soal bank berhasil diperbarui', 'question': _serialize_bank(bq)}), 200


@jwt_required()
def delete_question_bank(bank_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    bq = QuestionBank.query.get(bank_id)
    if not bq:
        return jsonify({'error': 'Soal bank tidak ditemukan'}), 404
    if bq.teacher_id != user.id and user.role != 'admin':
        return jsonify({'error': 'Anda tidak berhak menghapus soal bank ini'}), 403
    db.session.delete(bq)
    db.session.commit()
    return jsonify({'message': 'Soal bank berhasil dihapus'}), 200


# ---------------- TEACHER: analytics ----------------

@jwt_required()
def get_quiz_analytics(quiz_id):
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _can_manage_quiz(quiz, user):
        return jsonify({'error': 'Anda tidak berhak melihat analitik ini'}), 403

    subs = [s for s in quiz.submissions if s.status in ('submitted', 'timeout')]
    sub_ids = [s.id for s in subs]
    percentages = [s.percentage for s in subs if s.percentage is not None]
    n = len(percentages)
    passed = sum(1 for p in percentages if p >= (quiz.passing_grade or 75))

    question_analysis = []
    for q in sorted(quiz.questions, key=lambda x: x.order_index):
        answered = 0
        correct = 0
        if sub_ids:
            rows = Answer.query.filter(Answer.question_id == q.id, Answer.submission_id.in_(sub_ids)).all()
            answered = sum(1 for a in rows if a.option_id is not None)
            correct = sum(1 for a in rows if a.is_correct)
        attempts = len(subs)
        question_analysis.append({
            'question_id': q.id,
            'text': q.text,
            'question_type': q.question_type,
            'difficulty': q.difficulty,
            'points': q.points,
            'correct_rate': round(correct / attempts * 100, 1) if attempts else 0,
            'wrong_rate': round((answered - correct) / attempts * 100, 1) if attempts else 0,
            'unanswered': attempts - answered,
            'correct_count': correct,
            'wrong_count': answered - correct,
        })

    return jsonify({
        'quiz_id': quiz.id,
        'title': quiz.title,
        'passing_grade': quiz.passing_grade,
        'summary': {
            'participants': len({s.student_id for s in subs}),
            'attempts': n,
            'avg_percentage': round(sum(percentages) / n, 1) if n else 0,
            'highest': max(percentages) if n else 0,
            'lowest': min(percentages) if n else 0,
            'pass_rate': round(passed / n * 100, 1) if n else 0,
            'fail_rate': round((n - passed) / n * 100, 1) if n else 0,
            'passed': passed,
            'not_passed': n - passed,
        },
        'questions': question_analysis,
        'attempts_by_student': sorted([{
            'student_id': s.student_id,
            'student_name': s.student.name if s.student else None,
            'attempt_number': s.attempt_number,
            'percentage': s.percentage,
            'passed': (s.percentage or 0) >= (quiz.passing_grade or 75),
            'status': s.status,
            'submitted_at': s.completed_at.isoformat() if s.completed_at else None,
        } for s in subs], key=lambda x: (x['student_id'], x['attempt_number'])),
    }), 200


# ---------------- STUDENT ----------------

def _question_for_student(q, shuffle_options=False):
    opts = list(q.options)
    if shuffle_options:
        random.shuffle(opts)
    return {
        'question_id': q.id,
        'question_type': q.question_type,
        'text': q.text,
        'difficulty': q.difficulty,
        'points': q.points,
        'options': [{'option_id': o.id, 'option_text': o.option_text} for o in opts],
    }


def _deadline_for(quiz, submission):
    if not quiz.duration or not submission.started_at:
        return None
    return submission.started_at + timedelta(minutes=quiz.duration)


def _remaining_seconds(quiz, submission, now=None):
    dl = _deadline_for(quiz, submission)
    if dl is None:
        return None
    now = now or datetime.utcnow()
    return max(0, int((dl - now).total_seconds()))


def _attempt_payload(quiz, submission, include_answers=False):
    qs = list(quiz.questions)
    if quiz.shuffle_questions and len(qs) > 1:
        random.shuffle(qs)
    payload = {
        'attempt_id': submission.id,
        'attempt_number': submission.attempt_number,
        'quiz_id': quiz.id,
        'title': quiz.title,
        'description': quiz.description,
        'duration': quiz.duration,
        'passing_grade': quiz.passing_grade,
        'max_attempts': quiz.max_attempts,
        'remaining_seconds': _remaining_seconds(quiz, submission),
        'status': submission.status,
        'questions': [_question_for_student(q, quiz.shuffle_options) for q in qs],
    }
    if include_answers:
        payload['answers'] = {a.question_id: a.option_id for a in submission.answers if a.option_id is not None}
    return payload


def _result_payload(quiz, submission, include_detail=False):
    passed = (submission.percentage or 0) >= (quiz.passing_grade or 75)
    result = {
        'attempt_id': submission.id,
        'attempt_number': submission.attempt_number,
        'quiz_id': quiz.id,
        'title': quiz.title,
        'material_id': quiz.material_id,
        'material_title': quiz.material.title if quiz.material else None,
        'score': submission.score,
        'percentage': submission.percentage,
        'passing_grade': quiz.passing_grade,
        'passed': bool(passed),
        'correct_count': submission.correct_count,
        'wrong_count': submission.wrong_count,
        'unanswered_count': submission.unanswered_count,
        'max_attempts': quiz.max_attempts,
        'status': submission.status,
        'show_explanation': quiz.show_explanation,
        'submitted_at': (submission.completed_at or submission.submitted_at).isoformat() if (submission.completed_at or submission.submitted_at) else None,
    }
    if include_detail:
        show = quiz.show_explanation
        details = []
        for q in sorted(quiz.questions, key=lambda x: x.order_index):
            ans = next((a for a in submission.answers if a.question_id == q.id), None)
            correct_opt = next((o for o in q.options if o.is_correct), None)
            details.append({
                'question_id': q.id,
                'question_type': q.question_type,
                'text': q.text,
                'difficulty': q.difficulty,
                'points': q.points,
                'selected_option_id': ans.option_id if ans else None,
                'is_correct': bool(ans and ans.is_correct),
                'points_earned': ans.points_earned if ans else 0,
                'options': [{
                    'option_id': o.id,
                    'option_text': o.option_text,
                    'selected': bool(ans and ans.option_id == o.id),
                    'correct': o.is_correct if show else False,
                } for o in sorted(q.options, key=lambda x: x.order_index)],
                'explanation': q.explanation if show else None,
                'correct_option_id': correct_opt.id if (show and correct_opt) else None,
            })
        result['questions'] = details
    return result


def _grade_submission(submission, status='submitted'):
    quiz = submission.quiz
    questions = list(quiz.questions)
    total_points = sum(q.points or 0 for q in questions)
    earned = 0.0
    correct = 0
    wrong = 0
    unanswered = 0
    for q in questions:
        ans = Answer.query.filter_by(submission_id=submission.id, question_id=q.id).first()
        if ans and ans.option_id is not None:
            opt = Option.query.get(ans.option_id)
            is_correct = bool(opt and opt.is_correct)
            pts = (q.points or 0) if is_correct else 0
            ans.is_correct = is_correct
            ans.points_earned = pts
            ans.answered_at = ans.answered_at or datetime.utcnow()
            earned += pts
            if is_correct:
                correct += 1
            else:
                wrong += 1
        else:
            unanswered += 1
            if ans is None:
                db.session.add(Answer(
                    submission_id=submission.id,
                    question_id=q.id,
                    student_id=submission.student_id,
                    is_correct=False,
                    points_earned=0,
                    answered_at=datetime.utcnow(),
                ))
    submission.score = earned
    submission.percentage = round(earned / total_points * 100, 1) if total_points else 0
    submission.correct_count = correct
    submission.wrong_count = wrong
    submission.unanswered_count = unanswered
    submission.status = status
    submission.completed_at = datetime.utcnow()
    if submission.started_at:
        secs = int(max(0, (submission.completed_at - submission.started_at).total_seconds()))
        hours = (secs // 3600) % 24
        minutes = (secs % 3600) // 60
        seconds = secs % 60
        submission.work_time = _dtime(hours, minutes, seconds)
    db.session.commit()
    return submission


@jwt_required()
def get_student_quizzes():
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403

    material_id = request.args.get('material_id')
    quizzes = Quiz.query.filter_by(status='published').order_by(Quiz.created_at.desc()).all()
    result = []
    for q in quizzes:
        if material_id:
            try:
                if q.material_id != int(material_id):
                    continue
            except (TypeError, ValueError):
                return jsonify({'error': 'material_id tidak valid'}), 400
        if not _student_can_take(q, user):
            continue
        subs = [s for s in q.submissions if s.student_id == user.id]
        done = [s for s in subs if s.status in ('submitted', 'timeout')]
        inprog = next((s for s in subs if s.status == 'in_progress'), None)
        best = max((s.percentage for s in done if s.percentage is not None), default=None)
        status = 'in_progress' if inprog else ('completed' if done else 'not_started')
        result.append({
            'id': q.id,
            'title': q.title,
            'description': q.description,
            'material_id': q.material_id,
            'material_title': q.material.title if q.material else None,
            'material_topic': q.material.topic if q.material else None,
            'section_title': q.section.title if q.section else None,
            'question_count': len(q.questions),
            'duration': q.duration,
            'passing_grade': q.passing_grade,
            'max_attempts': q.max_attempts,
            'student_status': status,
            'attempts_used': len(done),
            'best_percentage': best,
            'passed': best is not None and best >= (q.passing_grade or 75),
            'attempts': [{
                'attempt_id': s.id,
                'attempt_number': s.attempt_number,
                'percentage': s.percentage,
                'status': s.status,
                'passed': (s.percentage or 0) >= (q.passing_grade or 75),
                'submitted_at': (s.completed_at or s.submitted_at).isoformat() if (s.completed_at or s.submitted_at) else None,
            } for s in sorted(done, key=lambda x: x.attempt_number)],
        })
    return jsonify(result), 200


@jwt_required()
def get_student_quiz(quiz_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _student_can_take(quiz, user):
        return jsonify({'error': 'Kuis tidak tersedia'}), 403

    done = [s for s in quiz.submissions if s.student_id == user.id and s.status in ('submitted', 'timeout')]
    inprog = next((s for s in quiz.submissions if s.student_id == user.id and s.status == 'in_progress'), None)
    best = max((s.percentage for s in done if s.percentage is not None), default=None)
    result = {
        'id': quiz.id,
        'title': quiz.title,
        'description': quiz.description,
        'material_id': quiz.material_id,
        'material_title': quiz.material.title if quiz.material else None,
        'material_topic': quiz.material.topic if quiz.material else None,
        'section_title': quiz.section.title if quiz.section else None,
        'question_count': len(quiz.questions),
        'duration': quiz.duration,
        'passing_grade': quiz.passing_grade,
        'max_attempts': quiz.max_attempts,
        'show_explanation': quiz.show_explanation,
        'student_status': 'in_progress' if inprog else ('completed' if done else 'not_started'),
        'attempts_used': len(done),
        'best_percentage': best,
        'passed': best is not None and best >= (quiz.passing_grade or 75),
        'attempts': [{
            'attempt_id': s.id,
            'attempt_number': s.attempt_number,
            'percentage': s.percentage,
            'status': s.status,
            'passed': (s.percentage or 0) >= (quiz.passing_grade or 75),
            'submitted_at': (s.completed_at or s.submitted_at).isoformat() if (s.completed_at or s.submitted_at) else None,
        } for s in sorted(done, key=lambda x: x.attempt_number)],
    }
    return jsonify(result), 200


@jwt_required()
def start_student_attempt(quiz_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    if not _student_can_take(quiz, user):
        return jsonify({'error': 'Kuis tidak tersedia'}), 403

    inprog = Submission.query.filter_by(quiz_id=quiz.id, student_id=user.id, status='in_progress').first()
    if inprog:
        deadline = _deadline_for(quiz, inprog)
        if deadline is None or datetime.utcnow() < deadline:
            return jsonify(_attempt_payload(quiz, inprog, include_answers=True)), 200
        _grade_submission(inprog, status='timeout')

    done_count = Submission.query.filter(
        Submission.quiz_id == quiz.id,
        Submission.student_id == user.id,
        Submission.status.in_(['submitted', 'timeout']),
    ).count()
    if done_count >= (quiz.max_attempts or 1):
        return jsonify({'error': 'Kesempatan mengerjakan kuis sudah habis'}), 403

    now = datetime.utcnow()
    sub = Submission(
        quiz_id=quiz.id,
        student_id=user.id,
        attempt_number=done_count + 1,
        started_at=now,
        submitted_at=now,
        status='in_progress',
    )
    db.session.add(sub)
    db.session.commit()
    from src.services.learning_analytics_service import log_activity
    if quiz.material_id:
        log_activity(user.id, quiz.material_id, 'quiz_started',
                     section_id=quiz.section_id, data={'quiz_id': quiz.id}, silent=True)
    return jsonify(_attempt_payload(quiz, sub, include_answers=True)), 201


@jwt_required()
def get_student_attempt(attempt_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    sub = Submission.query.get(attempt_id)
    if not sub or sub.student_id != user.id:
        return jsonify({'error': 'Attempt tidak ditemukan'}), 404
    quiz = sub.quiz
    if not _student_can_take(quiz, user):
        return jsonify({'error': 'Kuis tidak tersedia'}), 403

    if sub.status == 'in_progress':
        deadline = _deadline_for(quiz, sub)
        if deadline is not None and datetime.utcnow() > deadline:
            _grade_submission(sub, status='timeout')

    if sub.status == 'in_progress':
        return jsonify(_attempt_payload(quiz, sub, include_answers=True)), 200
    return jsonify(_result_payload(quiz, sub, include_detail=True)), 200


@jwt_required()
def save_student_answer(attempt_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    sub = Submission.query.get(attempt_id)
    if not sub or sub.student_id != user.id:
        return jsonify({'error': 'Attempt tidak ditemukan'}), 404
    quiz = sub.quiz
    if sub.status != 'in_progress':
        return jsonify({'error': 'Attempt sudah dikumpulkan'}), 400

    deadline = _deadline_for(quiz, sub)
    if deadline is not None and datetime.utcnow() > deadline:
        _grade_submission(sub, status='timeout')
        return jsonify({'error': 'Waktu habis, kuis dikumpulkan otomatis', 'result': _result_payload(quiz, sub)}), 400

    data = request.get_json(silent=True) or {}
    question_id = data.get('question_id')
    selected_option_id = data.get('selected_option_id')
    if question_id is None:
        return jsonify({'error': 'question_id wajib diisi'}), 400
    try:
        question_id = int(question_id)
        question = Question.query.filter_by(id=question_id, quiz_id=quiz.id).first()
    except (TypeError, ValueError):
        question = None
    if not question:
        return jsonify({'error': 'Soal tidak ditemukan pada kuis ini'}), 404

    option = None
    if selected_option_id is not None:
        try:
            option = Option.query.filter_by(id=int(selected_option_id), question_id=question.id).first()
        except (TypeError, ValueError):
            option = None
        if not option:
            return jsonify({'error': 'Pilihan jawaban tidak valid'}), 400

    ans = Answer.query.filter_by(submission_id=sub.id, question_id=question.id).first()
    if not ans:
        ans = Answer(submission_id=sub.id, question_id=question.id, student_id=user.id)
        db.session.add(ans)
    ans.option_id = option.id if option else None
    ans.answer_text = None
    ans.is_correct = None
    ans.points_earned = 0
    ans.answered_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Jawaban tersimpan'}), 200


@jwt_required()
def submit_student_attempt(attempt_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    sub = Submission.query.get(attempt_id)
    if not sub or sub.student_id != user.id:
        return jsonify({'error': 'Attempt tidak ditemukan'}), 404
    quiz = sub.quiz
    if sub.status != 'in_progress':
        return jsonify({'error': 'Attempt sudah dikumpulkan'}), 400

    deadline = _deadline_for(quiz, sub)
    status = 'timeout' if (deadline is not None and datetime.utcnow() > deadline) else 'submitted'
    _grade_submission(sub, status=status)
    from src.services.learning_analytics_service import log_activity
    if quiz.material_id:
        log_activity(user.id, quiz.material_id, 'quiz_submitted',
                     section_id=quiz.section_id, data={'quiz_id': quiz.id, 'status': status,
                                                        'percentage': sub.percentage}, silent=True)
    import threading
    from src.controllers.ai_explanation_controller import auto_generate_for_quiz
    threading.Thread(target=auto_generate_for_quiz, args=(quiz.id,), daemon=True).start()
    return jsonify({'message': 'Kuis berhasil dikumpulkan', 'result': _result_payload(quiz, sub, include_detail=True)}), 200


@jwt_required()
def get_student_attempt_result(attempt_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    sub = Submission.query.get(attempt_id)
    if not sub or sub.student_id != user.id:
        return jsonify({'error': 'Result tidak ditemukan'}), 404
    quiz = sub.quiz
    if sub.status not in ('submitted', 'timeout'):
        return jsonify({'error': 'Attempt belum dikumpulkan'}), 400
    return jsonify(_result_payload(quiz, sub, include_detail=True)), 200


@jwt_required()
def get_student_quiz_result(quiz_id):
    user = _cur_user()
    if not user or user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Kuis tidak ditemukan'}), 404
    subs = [s for s in quiz.submissions if s.student_id == user.id and s.status in ('submitted', 'timeout')]
    if not subs:
        return jsonify({'error': 'Belum ada hasil kuis'}), 404
    best = max(subs, key=lambda s: (s.percentage or 0))
    return jsonify(_result_payload(quiz, best, include_detail=True)), 200