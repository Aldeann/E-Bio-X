from datetime import datetime

from src.config.database import db


class AppSetting(db.Model):
    """Pengaturan aplikasi lintas halaman (key/value).

    Dipakai untuk teks yang berlaku sama di semua materi, misalnya "Kata
    Pengantar" (alasan website ini dikembangkan). Dibuat terpisah dari
    `materials` supaya tidak perlu diisi ulang di setiap materi.
    """
    __tablename__ = 'app_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
