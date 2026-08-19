import pymysql
pymysql.install_as_MySQLdb()
from flask import Flask, request
from flask_migrate import Migrate
from src.config.database import init_db, db
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)

    # JWT
    app.config['JWT_SECRET_KEY'] = os.getenv("SECRET_KEY")
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=3)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)
    JWTManager(app)
    
    # Database & Migration
    init_db(app)
    Migrate(app, db)

    # CORS
    CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_URL")}})
    
    # Import routes
    from src.controllers.user_controller import google_login, login, get_all_users, create_user, update_user, update_user_me, delete_user
    from src.controllers.course_controller import create_course, get_courses, get_teacher_courses, get_student_courses, delete_course, enroll, out, get_course_by_id, kick
    from src.controllers.material_controller import (
        upload_material, get_all_material, get_material_by_id, get_material_by_course, delete_material,
        update_material, publish_material, get_material_analytics,
        create_section, update_section, delete_section, reorder_sections,
        create_content, update_content, delete_content, reorder_contents,
        upload_material_file, delete_material_file, record_progress,
        get_material_student_state, update_material_student_state, submit_student_answer,
        get_material_bookmarks, create_material_bookmark, delete_material_bookmark,
        get_material_notes, create_material_note, update_student_note, delete_student_note,
    )
    from src.controllers.quiz_controller import create_quiz, get_quiz_by_id, delete_quiz, get_quizzes_by_course, submit_quiz, remove_sumbission, get_submission_by_quiz, toggle_open_quiz, edit_quiz_title, edit_question, edit_option
    from src.controllers.quiz_controller import (
        get_teacher_quizzes, create_quiz_teacher, get_teacher_quiz, update_quiz_teacher,
        set_quiz_status, delete_quiz_teacher, add_quiz_question, update_quiz_question,
        delete_quiz_question, duplicate_quiz_question, reorder_quiz_questions,
        get_question_bank, create_question_bank, update_question_bank, delete_question_bank,
        get_quiz_analytics,
        get_student_quizzes, get_student_quiz, start_student_attempt, get_student_attempt,
        save_student_answer, submit_student_attempt, get_student_attempt_result, get_student_quiz_result,
    )
    from src.controllers.analysis_controller import analyze_quiz, get_analyze
    from src.controllers.discussion_controller import get_threads_by_course, create_thread, get_thread_by_id, create_reply, delete_thread, delete_reply, toggle_pin_thread
    
    # Register routes
    app.add_url_rule('/api/google-login', view_func=google_login, methods=['POST'])
    app.add_url_rule('/api/login', view_func=login, methods=['POST'])
    
    app.add_url_rule('/api/users', view_func=get_all_users, methods=['GET'])
    app.add_url_rule('/api/users', view_func=create_user, methods=['POST'])
    app.add_url_rule('/api/users/<user_id>', view_func=update_user, methods=['PUT'])
    app.add_url_rule('/api/users/<user_id>', view_func=delete_user, methods=['DELETE'])
    app.add_url_rule('/api/user/me', view_func=update_user_me, methods=['PUT'])
    
    app.add_url_rule('/api/courses', view_func=create_course, methods=['POST'])
    app.add_url_rule('/api/courses', view_func=get_courses, methods=['GET'])
    app.add_url_rule('/api/courses/<course_id>', view_func=get_course_by_id, methods=['GET'])
    app.add_url_rule('/api/courses/<course_id>', view_func=delete_course, methods=['DELETE'])
    app.add_url_rule('/api/courses/teacher', view_func=get_teacher_courses, methods=['GET'])
    app.add_url_rule('/api/courses/student', view_func=get_student_courses, methods=['GET'])
    app.add_url_rule('/api/courses/enroll/<course_id>', view_func=enroll, methods=['GET'])
    app.add_url_rule('/api/courses/out/<course_id>', view_func=out, methods=['GET'])
    app.add_url_rule('/api/courses/<course_id>/students/<student_id>', view_func=kick, methods=['DELETE'])
    app.add_url_rule('/api/courses/materials/<course_id>', view_func=get_material_by_course, methods=['GET'])
    app.add_url_rule('/api/course/quiz/<course_id>', view_func=get_quizzes_by_course, methods=['GET'])
    
    app.add_url_rule('/api/materials', view_func=upload_material, methods=['POST'])
    app.add_url_rule('/api/materials', view_func=get_all_material, methods=['GET'])
    app.add_url_rule('/api/materials/<material_id>', view_func=get_material_by_id, methods=['GET'])
    app.add_url_rule('/api/materials/<material_id>', view_func=update_material, methods=['PUT'])
    app.add_url_rule('/api/materials/<material_id>', view_func=delete_material, methods=['DELETE'])
    app.add_url_rule('/api/materials/<material_id>/publish', view_func=publish_material, methods=['PATCH'])
    app.add_url_rule('/api/materials/<material_id>/analytics', view_func=get_material_analytics, methods=['GET'])
    app.add_url_rule('/api/materials/<material_id>/sections', view_func=create_section, methods=['POST'])
    app.add_url_rule('/api/materials/<material_id>/sections/reorder', view_func=reorder_sections, methods=['POST'])
    app.add_url_rule('/api/sections/<section_id>', view_func=update_section, methods=['PUT'])
    app.add_url_rule('/api/sections/<section_id>', view_func=delete_section, methods=['DELETE'])
    app.add_url_rule('/api/sections/<section_id>/contents', view_func=create_content, methods=['POST'])
    app.add_url_rule('/api/sections/<section_id>/contents/reorder', view_func=reorder_contents, methods=['POST'])
    app.add_url_rule('/api/contents/<content_id>', view_func=update_content, methods=['PUT'])
    app.add_url_rule('/api/contents/<content_id>', view_func=delete_content, methods=['DELETE'])
    app.add_url_rule('/api/materials/<material_id>/files', view_func=upload_material_file, methods=['POST'])
    app.add_url_rule('/api/materials/<material_id>/files/<file_id>', view_func=delete_material_file, methods=['DELETE'])
    app.add_url_rule('/api/materials/<material_id>/progress', view_func=record_progress, methods=['POST'])
    app.add_url_rule('/api/materials/<material_id>/state', view_func=get_material_student_state, methods=['GET'])
    app.add_url_rule('/api/materials/<material_id>/state', view_func=update_material_student_state, methods=['POST'])
    app.add_url_rule('/api/materials/<material_id>/answers', view_func=submit_student_answer, methods=['POST'])
    app.add_url_rule('/api/materials/<material_id>/bookmarks', view_func=get_material_bookmarks, methods=['GET'])
    app.add_url_rule('/api/materials/<material_id>/bookmarks', view_func=create_material_bookmark, methods=['POST'])
    app.add_url_rule('/api/materials/<material_id>/bookmarks/<bookmark_id>', view_func=delete_material_bookmark, methods=['DELETE'])
    app.add_url_rule('/api/materials/<material_id>/notes', view_func=get_material_notes, methods=['GET'])
    app.add_url_rule('/api/materials/<material_id>/notes', view_func=create_material_note, methods=['POST'])
    app.add_url_rule('/api/notes/<note_id>', view_func=update_student_note, methods=['PUT'])
    app.add_url_rule('/api/notes/<note_id>', view_func=delete_student_note, methods=['DELETE'])
    
    app.add_url_rule('/api/quiz', view_func=create_quiz, methods=['POST'])
    app.add_url_rule('/api/quiz/<quiz_id>', view_func=get_quiz_by_id, methods=['GET'])
    app.add_url_rule('/api/quiz/<quiz_id>', view_func=toggle_open_quiz, methods=['PUT'])
    app.add_url_rule('/api/quiz/<quiz_id>', view_func=delete_quiz, methods=['DELETE'])
    app.add_url_rule('/api/quiz/<quiz_id>/submit', view_func=submit_quiz, methods=['POST'])
    app.add_url_rule('/api/quiz/submission/<quiz_id>', view_func=get_submission_by_quiz, methods=['GET'])
    app.add_url_rule('/api/quiz/submission/<quiz_id>', view_func=remove_sumbission, methods=['DELETE'])
    
    app.add_url_rule('/api/quiz/<quiz_id>/edit_title', view_func=edit_quiz_title, methods=['PATCH'])
    app.add_url_rule('/api/quiz/<question_id>/edit_question', view_func=edit_question, methods=['PATCH'])
    app.add_url_rule('/api/quiz/<option_id>/edit_option', view_func=edit_option, methods=['PATCH'])
    
    app.add_url_rule('/api/analysis/<quiz_id>', view_func=get_analyze, methods=['GET'])
    app.add_url_rule('/api/analysis/<quiz_id>', view_func=analyze_quiz, methods=['POST'])

    # ===== Interactive quiz system (materials-linked) =====
    app.add_url_rule('/api/teacher/quizzes', view_func=get_teacher_quizzes, methods=['GET'])
    app.add_url_rule('/api/teacher/quizzes', view_func=create_quiz_teacher, methods=['POST'])
    app.add_url_rule('/api/teacher/quizzes/<quiz_id>', view_func=get_teacher_quiz, methods=['GET'])
    app.add_url_rule('/api/teacher/quizzes/<quiz_id>', view_func=update_quiz_teacher, methods=['PUT'])
    app.add_url_rule('/api/teacher/quizzes/<quiz_id>', view_func=delete_quiz_teacher, methods=['DELETE'])
    app.add_url_rule('/api/teacher/quizzes/<quiz_id>/publish', view_func=set_quiz_status, methods=['POST'])
    app.add_url_rule('/api/teacher/quizzes/<quiz_id>/questions', view_func=add_quiz_question, methods=['POST'])
    app.add_url_rule('/api/teacher/quizzes/<quiz_id>/questions/reorder', view_func=reorder_quiz_questions, methods=['POST'])
    app.add_url_rule('/api/teacher/quizzes/<quiz_id>/analytics', view_func=get_quiz_analytics, methods=['GET'])
    app.add_url_rule('/api/questions/<question_id>', view_func=update_quiz_question, methods=['PUT'])
    app.add_url_rule('/api/questions/<question_id>', view_func=delete_quiz_question, methods=['DELETE'])
    app.add_url_rule('/api/questions/<question_id>/duplicate', view_func=duplicate_quiz_question, methods=['POST'])
    app.add_url_rule('/api/teacher/question-bank', view_func=get_question_bank, methods=['GET'])
    app.add_url_rule('/api/teacher/question-bank', view_func=create_question_bank, methods=['POST'])
    app.add_url_rule('/api/teacher/question-bank/<bank_id>', view_func=update_question_bank, methods=['PUT'])
    app.add_url_rule('/api/teacher/question-bank/<bank_id>', view_func=delete_question_bank, methods=['DELETE'])

    app.add_url_rule('/api/student/quizzes', view_func=get_student_quizzes, methods=['GET'])
    app.add_url_rule('/api/student/quizzes/<quiz_id>', view_func=get_student_quiz, methods=['GET'])
    app.add_url_rule('/api/student/quizzes/<quiz_id>/start', view_func=start_student_attempt, methods=['POST'])
    app.add_url_rule('/api/student/quizzes/<quiz_id>/result', view_func=get_student_quiz_result, methods=['GET'])
    app.add_url_rule('/api/student/attempts/<attempt_id>', view_func=get_student_attempt, methods=['GET'])
    app.add_url_rule('/api/student/attempts/<attempt_id>/answer', view_func=save_student_answer, methods=['POST'])
    app.add_url_rule('/api/student/attempts/<attempt_id>/submit', view_func=submit_student_attempt, methods=['POST'])
    app.add_url_rule('/api/student/attempts/<attempt_id>/result', view_func=get_student_attempt_result, methods=['GET'])
    
    app.add_url_rule('/api/discussions/<course_id>', view_func=get_threads_by_course, methods=['GET'])
    app.add_url_rule('/api/discussions/<course_id>', view_func=create_thread, methods=['POST'])
    app.add_url_rule('/api/discussions/thread/<thread_id>', view_func=get_thread_by_id, methods=['GET'])
    app.add_url_rule('/api/discussions/thread/<thread_id>', view_func=delete_thread, methods=['DELETE'])
    app.add_url_rule('/api/discussions/thread/<thread_id>/pin', view_func=toggle_pin_thread, methods=['PUT'])
    app.add_url_rule('/api/discussions/thread/<thread_id>/reply', view_func=create_reply, methods=['POST'])
    app.add_url_rule('/api/discussions/reply/<reply_id>', view_func=delete_reply, methods=['DELETE'])
    
    return app

app = create_app() 