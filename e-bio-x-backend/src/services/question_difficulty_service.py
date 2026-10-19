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


def _slot_of(row):
    """Kunci satu soal. Semua baris yang sampai ke sini adalah PracticeAnswer,
    jadi kuncinya selalu id soal bank. Cabang `question_index` yang dulu ada di
    sini melayani soal interaktif dan sudah dihapus bersama kanalnya."""
    return int(row.bank_question_id)


def _count_slots(rows, exclude_student_id=None, key_fn=None):
    """slot -> {'students': set(...), 'correct': int}.

    INI satu-satunya tempat aturan "satu siswa = satu jawaban pertama"
    didefinisikan; `aggregate_rows` dan `material_level_observed` sama-sama
    memanggilnya supaya aturannya tidak mungkin berbeda.
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
    return counts


def aggregate_rows(rows, exclude_student_id=None, min_sample=None, key_fn=None):
    """Ukur tingkat tiap soal dari sekumpulan baris jawaban.

    Satu siswa dihitung sekali per soal memakai jawaban PERTAMA (paling
    awal `answered_at`). Baris milik `exclude_student_id` dilewati lebih
    dulu, jadi leave-one-out mengubah count sebelum ambang diperiksa.
    """
    counts = _count_slots(rows, exclude_student_id=exclude_student_id,
                          key_fn=key_fn)
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


# ------------------------------------------------------------
# LEVEL MATERI dari set diagnostik (Fase 4 level)
# ------------------------------------------------------------
#
# Materi tidak punya kolom material_id pada soal: satu-satunya jalan dari
# sebutan "soal ini milik materi X" adalah `question_bank.section_id` ->
# `material_sections.material_id`. Jadi semua kueri di bawah join ke sana,
# bukan menebak dari string topic.

def diagnostic_questions_for_material(material_id):
    """Soal ber-purpose='diagnostic' yang sudah APPROVED pada satu materi."""
    from src.models.material_section import MaterialSection
    from src.models.question_bank import QuestionBank

    return (
        QuestionBank.query
        .join(MaterialSection, MaterialSection.id == QuestionBank.section_id)
        .filter(MaterialSection.material_id == int(material_id),
                QuestionBank.status == 'APPROVED',
                QuestionBank.purpose == 'diagnostic')
        .order_by(QuestionBank.id)
        .all()
    )


def _level_insufficient(reason, message, thresholds, meta):
    return {
        'status': 'INSUFFICIENT_DATA',
        'label': None,
        'label_id': None,
        'p': None,
        'margin': None,
        'margin_points': None,
        'near_boundary': False,
        'reason': reason,
        'message': message,
        'basis': 'observed_diagnostic',
        'thresholds': thresholds,
        'computed_at': datetime.utcnow().isoformat() + 'Z',
        'n_answers': meta['n_answers'],
        'correct': meta['correct'],
        'n_students': meta['n_students'],
        'n_items': meta['n_items'],
        'n_items_total': meta['n_items_total'],
    }


def material_level_observed(material_id, min_items=None, min_students=None,
                            item_sample=None):
    """Tingkat kesulitan terukur SATU MATERI dari jawaban diagnostik.

    Tahapannya sengaja berurutan dan semuanya harus lewat sebelum ada label:

    1. Kumpulkan soal ber-purpose='diagnostic' (APPROVED) milik materi ini.
    2. Hitung tiap soal memakai `_count_slots` - aturan yang PERSIS sama
       dengan soal latihan biasa: satu siswa dihitung sekali, jawaban
       pertama yang dipakai.
    3. Hanya soal yang per READY (>= `item_sample` siswa) yang masuk ke
       penghitungan bersama. Soal yang datanya tipis ikut dilaporkan
       `n_items_total` supaya jelas apa yang belum siap, bukan hilang.
    4. Jumlah soal READY >= K dan siswa berbeda >= N -> label diberikan,
       bersama p, margin, dan penanda "dekat batas" (persis satu aturan
       dengan `classify`).

    Jawaban latihan adaptif TIDAK ikut: pemisahnya kolom `mode` pada
    `practice_answers`. Soal memang terpisah dari pool adaptif, tapi itu hanya
    menjamin soalnya; yang menjamin sampelnya adalah catatan jalur per jawaban,
    sebab sebuah soal bisa berpindah jalur kapan saja. Hasilnya bebas dari
    campur tangan mesin 60/30/10.
    """
    min_items = cfg.MATERIAL_LEVEL_MIN_ITEMS if min_items is None else int(min_items)
    min_students = cfg.MATERIAL_LEVEL_MIN_STUDENTS if min_students is None else int(min_students)
    item_sample = cfg.MIN_DIFFICULTY_SAMPLE if item_sample is None else int(item_sample)

    thresholds = {'items': min_items, 'students': min_students,
                  'item_sample': item_sample}

    questions = diagnostic_questions_for_material(material_id)
    meta = {'n_answers': 0, 'correct': 0, 'n_students': 0,
            'n_items': 0, 'n_items_total': len(questions)}

    if not questions:
        return _level_insufficient(
            'no_questions',
            'Materi ini belum punya soal diagnostik. Tambahkan soal di '
            'bagian "Latihan per Bagian" lalu tandai sebagai diagnostik.',
            thresholds, meta)

    # Jawaban latihan adaptif TIDAK ikut, dan penanda yang sah adalah kolom
    # `practice_answers.mode`, bukan `purpose` soal. Sebab soal boleh berpindah
    # jalur (guru menandai soal latihan lama sebagai diagnostik); kalau kita
    # hanya menyaring "soal purpose-nya diagnostic", jawaban-jawaban adaptif
    # masa lalu ikut terhitung dan sampelnya kembali bias mesin 60/30/10.
    rows = PracticeAnswer.query.filter(
        PracticeAnswer.bank_question_id.in_([q.id for q in questions]),
        PracticeAnswer.mode == 'diagnostic',
    ).all()
    counts = _count_slots(rows)

    ready_ids = []
    students_ready = set()
    n_answers = 0
    n_correct = 0
    for q in questions:
        bucket = counts.get(q.id, {'students': set(), 'correct': 0})
        per_item = classify(len(bucket['students']), bucket['correct'])
        if per_item['status'] != 'READY':
            continue
        ready_ids.append(q.id)
        students_ready |= bucket['students']
        n_answers += per_item['n']
        n_correct += per_item['correct']

    meta.update({
        'n_items': len(ready_ids),
        'n_answers': n_answers,
        'correct': n_correct,
        'n_students': len(students_ready),
    })

    if len(ready_ids) < min_items:
        return _level_insufficient(
            'items',
            f'Baru {len(ready_ids)} soal diagnostik yang terukur '
            f'(perlu {min_items}); {meta["n_items_total"] - len(ready_ids)} '
            f'soal lain belum dijawab cukup banyak siswa.',
            thresholds, meta)
    if len(students_ready) < min_students:
        return _level_insufficient(
            'students',
            f'Baru {len(students_ready)} siswa berbeda yang menjawab soal '
            f'diagnostik siap ukur (perlu {min_students}).',
            thresholds, meta)

    # Gerbang di atas sudah memastikan n_answers >= n_students >= min_students,
    # jadi min_sample=1 hanya dipakai untuk melewati pembagian nol tanpa
    # memutuskan apa pun; p, label, margin, dan near_boundary tetap dihitung
    # oleh `classify` - satu sumber ambang untuk seluruh sistem.
    result = classify(n_answers, n_correct, min_sample=1)
    result.update({
        'basis': 'observed_diagnostic',
        # Label Indonesia berdampingan dengan kunci kanonik, supaya UI tidak
        # perlu tahu kamusnya dan tidak ada dua sumber ambang.
        'label_id': LABEL_TEXT.get(result.get('label')),
        'margin_points': (round(result['margin'] * 100)
                          if result.get('margin') is not None else None),
        'thresholds': thresholds,
        'n_students': len(students_ready),
        'n_items': len(ready_ids),
        'n_items_total': len(questions),
        'n_answers': n_answers,
        'computed_at': datetime.utcnow().isoformat() + 'Z',
    })
    return result


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
