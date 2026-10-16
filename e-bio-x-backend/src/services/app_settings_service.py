from datetime import datetime

from src.config.database import db
from src.models.app_setting import AppSetting

# Kunci pengaturan. Satu tempat supaya controller dan pemakaian lain tidak
# menulis string yang berbeda-beda.
FOREWORD_KEY = 'foreword'


def get_setting(key, default=None):
    row = AppSetting.query.filter_by(key=key).first()
    return row.value if row else default


def set_setting(key, value):
    row = AppSetting.query.filter_by(key=key).first()
    if not row:
        row = AppSetting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
    row.updated_at = datetime.utcnow()
    db.session.commit()
    return row


def get_foreword():
    """Kata pengantar global (alasan website dikembangkan)."""
    return get_setting(FOREWORD_KEY, '') or ''


def set_foreword(text):
    return set_setting(FOREWORD_KEY, text or '')
