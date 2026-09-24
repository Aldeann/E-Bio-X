import os
from src import app
from src.config.database import db
from flask import send_from_directory

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


@app.errorhandler(413)
def too_large(_e):
    from flask import jsonify
    return jsonify({'error': 'Ukuran file melebihi batas maksimal 40MB'}), 413


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/')
def hello_world():
    return 'Server is running!'


def _ensure_schema_compat():
    """Dev-only helper: create_all() tidak mengubah tabel yang sudah ada.
    Bila kolom baru (mis. student_answers.answer_data) belum ada di DB lama,
    tambahkan lewat ALTER yang idempotent (aman dijalankan ulang)."""
    from sqlalchemy import text
    statements = [
        'ALTER TABLE student_answers MODIFY selected_answer INT NULL',
        'ALTER TABLE student_answers ADD COLUMN answer_data TEXT NULL',
    ]
    for stmt in statements:
        try:
            db.session.execute(text(stmt))
            db.session.commit()
        except Exception:
            db.session.rollback()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        _ensure_schema_compat()
    app.run(host='0.0.0.0', port=5000, debug=True)
