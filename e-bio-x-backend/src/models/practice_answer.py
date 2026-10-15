from src.config.database import db
from datetime import datetime

# Jawaban siswa terhadap soal latihan per bagian (Fase 3d).
#
# Tabel TERPISA dari `student_answers` dengan sengaja. `student_answers`
# menempel pada `material_contents` (kolom content_id NOT NULL): barisnya
# berarti "siswa menjawab blok interaktif milik materi ini". Jawaban latihan
# menunjuk ke `question_bank`, bukan ke blok materi, jadi memaksanya masuk ke
# sana berarti mengarang pemetaan yang tidak ada. Pemisahan ini juga membuat
# sumber data tidak pernah tercampur diam-diam: hitungan kuis/interaktif dan
# hitungan latihan dibaca dari tabel berbeda dan dilaporkan terpisah.


class PracticeAnswer(db.Model):
    __tablename__ = 'practice_answers'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('material_sections.id'), nullable=False)
    bank_question_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=False)
    # order_index opsi yang dipilih. Bukan indeks kiriman klien: server memuat
    # ulang soalnya dan mencocokkan dengan order_index yang tersimpan, sehingga
    # klien tidak bisa menebak atau memalsukan kunci jawaban.
    selected_option = db.Column(db.Integer, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    # Soal boleh diulang sebagai latihan. Yang dihitung untuk diagnosis adalah jawaban
    # TERAKHIR per soal, jadi mencoba berkali-kali tidak menambah jumlah
    # soal yang "terjawab" (lihat student_practice_service.practice_stats).
    attempt_no = db.Column(db.Integer, nullable=False, default=1)
    # Teks soal seperti tampil saat dijawab. Kalau guru menyunting soalnya
    # kemudian, catatan ini tetap bisa dibaca apa adanya yang dinilai siswa.
    question_snapshot = db.Column(db.Text, nullable=True)
    # Jalur tempat jawaban ini dibuat: 'practice' (latihan adaptif) atau
    # 'diagnostic' (Asesmen Diagnostik). INI penanda yang sah; `purpose` pada
    # soal bukan. Sebab sebuah soal boleh guru ubah purpose-nya (latihan ->
    # diagnostik) setelah lama dipakai latihan. Kalau pengukuran tingkat materi
    # hanya menyaring "soal yang purpose-nya diagnostic", jawaban-jawaban lama
    # dari latihan adaptif ikut terhitung dan sampelnya jadi terbias mesin
    # 60/30/10 - persis yang ingin dihindari. Dengan kolom ini, bukti diagnostik
    # hanya berasal dari jawaban yang memang dibuat lewat endpoint diagnostik,
    # dan mengubah purpose soal tidak pernah menghitung ulang masa lalunya.
    mode = db.Column(db.String(16), nullable=False, default='practice',
                     server_default='practice')
    answered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship('User', backref=db.backref('practice_answers', lazy=True))
    material = db.relationship('Material', backref=db.backref('practice_answers', lazy=True))
    section = db.relationship('MaterialSection', backref=db.backref('practice_answers', lazy=True))
    bank_question = db.relationship('QuestionBank', backref=db.backref('practice_answers', lazy=True))

    def __repr__(self):
        return f'<PracticeAnswer {self.section_id} - {self.student_id}>'