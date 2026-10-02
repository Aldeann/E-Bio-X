from flask_sqlalchemy import SQLAlchemy
from os import environ
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql://{environ.get('MYSQL_USER')}:{environ.get('MYSQL_PASSWORD')}@{environ.get('MYSQL_HOST')}:3306/{environ.get('MYSQL_DATABASE')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
    
    db.init_app(app) 


# Columns added after the first release. create_all() never touches a
# table that already exists, so an existing database needs these applied
# explicitly.
#
# The check goes through INFORMATION_SCHEMA rather than catching the
# "duplicate column" error, so running this repeatedly is quiet and does
# not leave a poisoned transaction behind.
_COMPAT_COLUMNS = [
    ('student_answers', 'selected_answer', 'ALTER TABLE student_answers MODIFY selected_answer INT NULL'),
    ('student_answers', 'answer_data', 'ALTER TABLE student_answers ADD COLUMN answer_data TEXT NULL'),
    # Per-class models: NULL means pooled, a value means that teacher.
    ('ml_models', 'teacher_id', 'ALTER TABLE ml_models ADD COLUMN teacher_id INT NULL'),
    # Subtopic tag on quiz questions: NULL = not tagged. Lets wrong answers
    # be attributed to a material section (Fase 1 per-section diagnosis).
    ('questions', 'section_id', 'ALTER TABLE questions ADD COLUMN section_id INT NULL'),
    # Practice questions per material section (Fase 3). section_id is only set
    # from a section the teacher explicitly chose. source/status carry the
    # review trail: only APPROVED questions may be served as practice.
    ('question_bank', 'section_id', 'ALTER TABLE question_bank ADD COLUMN section_id INT NULL'),
    ('question_bank', 'source', "ALTER TABLE question_bank ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'teacher'"),
    ('question_bank', 'status', "ALTER TABLE question_bank ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'APPROVED'"),
    ('question_bank', 'generated_by', 'ALTER TABLE question_bank ADD COLUMN generated_by VARCHAR(20) NULL'),
    ('question_bank', 'model_name', 'ALTER TABLE question_bank ADD COLUMN model_name VARCHAR(100) NULL'),
    ('question_bank', 'prompt_version', 'ALTER TABLE question_bank ADD COLUMN prompt_version VARCHAR(20) NULL'),
    ('question_bank', 'reviewed_by', 'ALTER TABLE question_bank ADD COLUMN reviewed_by INT NULL'),
    ('question_bank', 'reviewed_at', 'ALTER TABLE question_bank ADD COLUMN reviewed_at DATETIME NULL'),
    ('question_bank', 'misconception', 'ALTER TABLE question_bank ADD COLUMN misconception TEXT NULL'),
    ('question_bank_options', 'feedback', 'ALTER TABLE question_bank_options ADD COLUMN feedback TEXT NULL'),
]


def ensure_schema_compat():
    """Apply idempotent ALTERs for columns added after the first release."""
    from sqlalchemy import text
    applied, skipped, failed = [], [], []
    for table, column, statement in _COMPAT_COLUMNS:
        try:
            row = db.session.execute(text(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                "AND COLUMN_NAME = :c"),
                {'t': table, 'c': column}).scalar()
        except Exception:
            db.session.rollback()
            failed.append(f'{table}.{column}')
            continue
        if row:
            skipped.append(f'{table}.{column}')
            continue
        try:
            db.session.execute(text(statement))
            db.session.commit()
            applied.append(f'{table}.{column}')
        except Exception:
            db.session.rollback()
            failed.append(f'{table}.{column}')
    return {'applied': applied, 'already_present': skipped, 'failed': failed}
