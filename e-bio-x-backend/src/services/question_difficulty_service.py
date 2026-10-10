"""Analisis tingkatan soal otomatis dari performa nyata (Fase 3f).

Tingkat kesulitan soal TIDAK ditebak dari teksnya dan TIDAK menunggu
label guru: diukur dari jawaban nyata (p-value = fraksi benar di antara
siswa yang mengerjakan). Semua angka yang keluar menyebut sumbernya.

Kontrak kejujuran yang dijaga di sini:

1. Sebuah soal hanya diukur bila >= MIN_DIFFICULTY_SAMPLE siswa BERBEDA
   menjawabnya. Di bawah itu statusnya INSUFFICIENT_DATA dan TIDAK ada
   label yang diklaim - lebih baik diam daripada menebak dari 1-2 orang.
2. Tiap siswa dihitung SEKALI dan memakai jawaban PERTAMA. Jawaban ulang
   sudah "dibantu" umpan balik, jadi memakai yang terakhir akan membuat
   soal tampak lebih mudah daripada kenyataannya.
3. Saat menilai seorang siswa, jawabannya SENDIRI dikeluarkan dari
   hitungan (leave-one-out). Kalau tidak, siswa yang salah ikut menurunkan
   p soal lalu soal itu dipakai menyebut dia lemah - hakim merangkap
   terdakwa.
4. Margin (selisih 95%, aproksimasi normal) selalu ikut dilaporkan; bila
   rentang p +/- margin memotong garis batas 0.40/0.70, label ditandai
   "dekat batas" - bukan dianggap pasti.
5. Label terukur hidup BERSAMA label guru/deklarasi dan tidak pernah
   menimpanya.
"""
from datetime import datetime

from src.ml import ml_config as cfg
from src.models.practice_answer import PracticeAnswer
from src.models.student_answer import StudentAnswer

# Tingkat terukur -> kunci label Indonesia untuk tampilan.
LABEL_TEXT = {'easy': 'mudah', 'medium': 'sedang', 'hard': 'sulit'}


def margin(p, n):
    """Setengah lebar selang kepercayaan 95% untuk proporsi p dengan n siswa."""
    if p is None or not n:
        return None
    return cfg.DIFFICULTY_MARGIN_Z * (p * (1.0 - p) / float(n)) ** 0.5


def classify(total, correct, min_sample=None):
    """Ubah (p-value) -> label tingkat + status, murni tanpa database.

    `min_sample` default MIN_DIFFICULTY_SAMPLE. Diparameterkan supaya uji
    unit bisa memakai sampel kecil tanpa menurunkan ambang produksi.
    """
    min_sample = cfg.MIN_DIFFICULTY_SAMPLE if min_sample is None else min_sample
    total = int(total or 0)
    correct = int(correct or 0)
    base = {'n': total, 'correct': correct, 'basis': 'observed'}
    if total < min_sample:
        base.update({
            'status': 'INSUFFICIENT_DATA',
            'p': None,
            'label': None,
            'margin': None,
            'near_boundary': False,
        })
        return base

    p = correct / float(total)
    if p >= cfg.DIFFICULTY_P_EASY:
        label = 'easy'
    elif p < cfg.DIFFICULTY_P_HARD:
        label = 'hard'
    else:
        label = 'medium'

    m = margin(p, total)
    near = False
    if m is not None:
        lo, hi = p - m, p + m
        near = any(lo < cut < hi
                   for cut in (cfg.DIFFICULTY_P_EASY, cfg.DIFFICULTY_P_HARD))
    base.update({
        'status': 'READY',
        'p': round(p, 3),
        'label': label,
        'margin': round(m, 3) if m is not None else None,
        'near_boundary': bool(near),
    })
    return base


def _empty(slot):
    return {
        'slot': slot,
        'status': 'INSUFFICIENT_DATA',
        'n': 0,
        'correct': 0,
        'p': None,
        'label': None,
        'margin': None,
        'near_boundary': False,
        'basis': 'observed',
    }


def interactive_slot_key(row):
    """Kunci satu soal interaktif: (section_id, content_id, question_index)."""
    return (
        int(row.section_id) if row.section_id is not None else None,
        int(row.content_id) if row.content_id is not None else None,
        int(row.question_index) if row.question_index is not None else None,
    )


def _slot_of(row):
    if hasattr(row, 'question_index'):
        return interactive_slot_key(row)
    return int(row.bank_question_id)


def aggregate_rows(rows, exclude_student_id=None, min_sample=None, key_fn=None):
    """Ukur tingkat tiap soal dari sekumpulan baris jawaban.

    Satu siswa dihitung sekali per soal memakai jawaban PERTAMA (paling
    awal `answered_at`). Baris milik `exclude_student_id` dilewati lebih
    dulu, jadi leave-one-out mengubah count sebelum ambang diperiksa.
    """
    key_fn = key_fn or _slot_of
    exclude = int(exclude_student_id) if exclude_student_id is not None else None

    ordered = sorted(rows, key=lambda r: (
        getattr(r, 'answered_at', None) or datetime.min,
        getattr(r, 'id', 0) or 0,
    ))

    seen = set()
    counts = {}
    for r in ordered:
        student_id = int(getattr(r, 'student_id'))
        if exclude is not None and student_id == exclude:
            continue
        slot = key_fn(r)
        marker = (slot, student_id)
        if marker in seen:
            continue
        seen.add(marker)
        bucket = counts.setdefault(slot, {'students': set(), 'correct': 0})
        bucket['students'].add(student_id)
        if bool(getattr(r, 'is_correct')):
            bucket['correct'] += 1

    result = {}
    for slot, bucket in counts.items():
        result[slot] = classify(len(bucket['students']), bucket['correct'],
                                min_sample=min_sample)
        result[slot]['slot'] = slot
    return result


def observed_for_bank_question(bank_question_id, exclude_student_id=None):
    """Hasil terukur satu soal bank (opsional leave-one-out satu siswa)."""
    rows = PracticeAnswer.query.filter_by(
        bank_question_id=bank_question_id).all()
    result = aggregate_rows(rows, exclude_student_id=exclude_student_id)
    return result.get(int(bank_question_id), _empty(int(bank_question_id)))


def observed_bank_batch(bank_ids, exclude_student_id=None):
    """Hasil terukur sekumpulan soal bank sekaligus (satu query)."""
    ids = [int(i) for i in bank_ids]
    if not ids:
        return {}
    rows = PracticeAnswer.query.filter(
        PracticeAnswer.bank_question_id.in_(ids)).all()
    return aggregate_rows(rows, exclude_student_id=exclude_student_id)


def interactive_batch(rows, exclude_student_id=None):
    """Hasil terukur sekumpulan baris StudentAnswer yang sudah dimuat."""
    return aggregate_rows(rows, exclude_student_id=exclude_student_id,
                          key_fn=interactive_slot_key)


def empty_observed(slot=None):
    """Hasil pengukuran kosong: soal yang belum pernah dijawab siapa pun.

    Statusnya INSUFFICIENT_DATA, bukan 'sedang'. Belum ada jawaban berarti
    belum ada yang bisa diklaim tentang tingkat soal itu.
    """
    return _empty(slot)


def observed_note(obs):
    """Kalimat sumber untuk satu hasil pengukuran, atau None bila belum cukup.

    Contoh: "63 siswa menjawab, 73% benar (+/-11 poin); dekat batas".
    Sengaja TIDAK memuat kata tingkat: pemanggil yang menempelkan label
    Indonesia lewat `difficulty_label`, supaya modul ini bebas dari
    ketergantungan service lain.
    """
    if not obs or obs.get('status') != 'READY':
        return None
    pct = round((obs.get('p') or 0.0) * 100)
    points = round((obs.get('margin') or 0.0) * 100)
    text = f"{obs.get('n', 0)} siswa menjawab, {pct}% benar (±{points} poin)"
    if obs.get('near_boundary'):
        text += '; dekat batas'
    return text
