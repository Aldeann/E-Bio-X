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
    # Practice pool vs diagnostic set (Fase 4 level materi). Diagnostic
    # questions are answered WITHOUT adaptation and are the only thing the
    # measured difficulty of a material may be computed from; practice
    # questions keep their old meaning, and the default below keeps every
    # existing row where it already was.
    ('question_bank', 'purpose', "ALTER TABLE question_bank ADD COLUMN purpose VARCHAR(20) NOT NULL DEFAULT 'practice'"),
    ('question_bank_options', 'feedback', 'ALTER TABLE question_bank_options ADD COLUMN feedback TEXT NULL'),
    # Which lane an answer was written in: 'practice' (adaptive) or
    # 'diagnostic' (Asesmen Diagnostik). A question's `purpose` cannot serve as
    # this marker because a teacher may flip a question from practice to
    # diagnostic after years of adaptive answers; without this column those
    # old answers would silently become "diagnostic evidence" and bias the
    # measured material level (see material_level_observed).
    ('practice_answers', 'mode', "ALTER TABLE practice_answers ADD COLUMN mode VARCHAR(16) NOT NULL DEFAULT 'practice'"),
    # Per-section recommendation (Fase 3e). section_id IS NULL -> the row is
    # a material-level recommendation (unchanged behaviour); a value -> the
    # row recommends that one section. material_id stays NOT NULL on
    # purpose: a section always belongs to a material, so relaxing it would
    # only throw away a foreign key we always know.
    ('recommendations', 'section_id', 'ALTER TABLE recommendations ADD COLUMN section_id INT NULL'),
]

# Foreign keys for the columns added above. `ADD COLUMN section_id INT NULL`
# does NOT bring a REFERENCES clause with it, so every column added after
# the first release was referencing sections with no referential integrity
# at all: deleting a section left rows pointing at a section that no longer
# existed, and nothing complained. For `recommendations` that meant a
# persisted suggestion to a section the student could not open any more.
#
# The models already declared `db.ForeignKey('material_sections.id')` from
# the start, so a fresh `create_all()` got the constraint and only existing
# databases were left without it. The gap was in the migration path alone.
#
# These are checked separately from _COMPAT_COLUMNS because by the time
# this runs the column is already there - what is missing is the
# CONSTRAINT.
#
# No ON DELETE clause on purpose. If a section is ever deleted with rows
# still attached, MySQL refuses the delete instead of quietly erasing the
# record that a student was pointed at that section. Losing that history
# silently would be worse than a delete that needs a decision first.
_COMPAT_FOREIGN_KEYS = [
    ('questions', 'section_id', 'material_sections', 'fk_questions_section'),
    ('question_bank', 'section_id', 'material_sections',
     'fk_question_bank_section'),
    ('recommendations', 'section_id', 'material_sections',
     'fk_recommendations_section'),
]


def _has_foreign_key(table, column, ref_table):
    from sqlalchemy import text
    return bool(db.session.execute(text(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = :t "
        "AND COLUMN_NAME = :c AND REFERENCED_TABLE_NAME = :r"),
        {'t': table, 'c': column, 'r': ref_table}).scalar())


def _orphan_count(table, column, ref_table):
    from sqlalchemy import text
    return db.session.execute(text(
        f"SELECT COUNT(*) FROM `{table}` c "
        f"LEFT JOIN `{ref_table}` r ON r.id = c.`{column}` "
        f"WHERE c.`{column}` IS NOT NULL AND r.id IS NULL")).scalar()


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

    fk_applied, fk_skipped, fk_failed = [], [], []
    for table, column, ref_table, name in _COMPAT_FOREIGN_KEYS:
        label = f'{table}.{column} -> {ref_table}'
        try:
            if _has_foreign_key(table, column, ref_table):
                fk_skipped.append(label)
                continue
            orphans = _orphan_count(table, column, ref_table)
            if orphans:
                # Reported, NOT deleted. A row pointing at a section that
                # no longer exists is garbage, but throwing away a table's
                # data is a decision for a person - not for a function that
                # runs on every boot.
                fk_failed.append(f'{label} ({orphans} baris yatim belum '
                                 f'dibersihkan manual)')
                continue
            db.session.execute(text(
                f'ALTER TABLE `{table}` ADD CONSTRAINT `{name}` '
                f'FOREIGN KEY (`{column}`) REFERENCES `{ref_table}` (`id`)'))
            db.session.commit()
            fk_applied.append(label)
        except Exception:
            db.session.rollback()
            fk_failed.append(label)

    return {'applied': applied, 'already_present': skipped, 'failed': failed,
            'foreign_keys_applied': fk_applied,
            'foreign_keys_already_present': fk_skipped,
            'foreign_keys_failed': fk_failed}
