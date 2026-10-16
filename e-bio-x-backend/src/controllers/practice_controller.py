"""Practice questions per material section (Fase 3).

Teacher side, in the order the workflow runs:

1. ``GET  /api/teacher/practice/sections`` - sections the teacher owns with raw
   draft counts, so the UI can say "bagian ini belum ada soal latihan" instead
   of guessing.
2. ``POST /api/teacher/practice/sections/<id>/drafts`` - ask the AI for drafts
   for ONE section the teacher picked. Drafts are stored as DRAFT and the
   section tag comes from the section record, never from the model output.
3. ``POST /api/teacher/practice/drafts/<id>/approve|reject`` - the teacher's
   decision. Only APPROVED questions can be used as practice later.

Student side (3d):

4. ``GET  /api/student/practice/<material_id>/sections`` - which sections have
   practice questions, and how many this student already answered.
5. ``GET  /api/student/practice/<material_id>/sections/<section_id>`` - the
   APPROVED questions of one section, without the answer key.
6. ``POST /api/student/practice/<material_id>/sections/<section_id>/answer`` -
   grade one answer and record the attempt.
"""
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime

from src.config.database import db
from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.material_content import MaterialContent
from src.models.question_bank import QuestionBank
from src.models.question_bank_option import QuestionBankOption
from src.models.student_answer import StudentAnswer
from src.services import practice_bank_service as practice
from src.services import student_practice_service as spractice
from src.services import question_difficulty_service as qds
from src.ml import ml_config as cfg
from src.services.learning_analytics_service import (
    student_can_access_material,
    teacher_materials,
    difficulty_label,
    normalize_difficulty,
)
from src.controllers.quiz_controller import (
    _cur_user,
    _is_teacher,
    _teacher_owns_material,
    _validate_question_payload,
    _serialize_bank,
)


def _owned_bank(bank_id, user):
    bq = QuestionBank.query.get(bank_id)
    if not bq:
        return None, (jsonify({'error': 'Soal bank tidak ditemukan'}), 404)
    if bq.teacher_id != user.id and user.role != 'admin':
        return None, (jsonify({'error': 'Anda tidak berhak menangani soal bank ini'}), 403)
    return bq, None


@jwt_required()
def get_practice_sections():
    """Sections of the teacher's materials plus how many practice questions exist.

    `ai_available` is reported so the UI can explain up front that AI drafts are
    unavailable instead of failing on click.
    """
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    material_id = request.args.get('material_id')
    if material_id:
        try:
            material_id = int(material_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'material_id tidak valid'}), 400

    available = practice.ai_available()
    return jsonify({
        'sections': practice.section_rows(user, material_id=material_id),
        'ai_available': available,
        'ai_model': practice.model_name() if available else None,
        'ai_unavailable_reason': None if available else (
            'AI belum dikonfigurasi (AI_API_KEY). Soal latihan tetap bisa ditulis '
            'sendiri lalu ditautkan ke bagian.'
        ),
    }), 200


@jwt_required()
def generate_section_drafts(section_id):
    """Create AI drafts for one section the teacher owns."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    section = MaterialSection.query.get(section_id)
    if not section:
        return jsonify({'error': 'Bagian materi tidak ditemukan'}), 404
    material = section.material
    if not material:
        return jsonify({'error': 'Bagian ini tidak tertaut ke materi'}), 400
    if not _teacher_owns_material(user, material):
        return jsonify({'error': 'Anda tidak berhak menangani bagian ini'}), 403

    data = request.get_json(silent=True) or {}
    raw_count = data.get('count', practice.DEFAULT_COUNT)
    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        return jsonify({'error': 'Jumlah soal tidak valid'}), 400
    if count < 1 or count > practice.MAX_COUNT:
        return jsonify({'error': f'Jumlah soal harus antara 1 dan {practice.MAX_COUNT}'}), 400

    # Tingkat kesulitan TIDAK lagi dipilih guru. Draf disimpan apa adanya dengan
    # tingkat USULAN AI (bila ada), dan sistem mengoreksinya nanti dari performa
    # siswa. Parameter 'difficulty' dari klien sengaja diabaikan.
    if not practice.ai_available():
        return jsonify({
            'error': 'AI belum dikonfigurasi (AI_API_KEY). Set di server lalu coba lagi, '
                     'atau tulis soal sendiri dan tautkan ke bagian ini.',
            'ai_available': False,
        }), 503

    # A section with no text at all has nothing to ground a question on. Saying so
    # beats spending an API call on invented content.
    if not practice.section_body(section).strip():
        return jsonify({
            'error': f'Bagian "{section.title}" belum punya teks, jadi tidak ada dasar '
                     'untuk membuat soal. Tambahkan isi bagian dulu.',
            'section_id': section.id,
        }), 400

    try:
        items, dropped = practice.generate_drafts(section, material, count)
    except practice.DraftUnavailable as exc:
        return jsonify({'error': str(exc), 'ai_available': False}), 503
    except practice.DraftFailed as exc:
        return jsonify({'error': str(exc)}), 502

    created = []
    skipped = dropped
    for item in items:
        payload = {
            'question_text': item['question_text'],
            'question_type': 'multiple_choice',
            # Usulan tingkat dari AI (boleh kosong = belum ditentukan).
            'difficulty': item.get('difficulty') or '',
            'points': 10,
            'explanation': item.get('explanation'),
            'options': item['options'],
        }
        validated, err = _validate_question_payload(payload, bank=True)
        if err:
            # AI returned something that cannot be a question (e.g. two correct
            # options). Report the count instead of storing it.
            skipped += 1
            continue

        bq = QuestionBank(
            teacher_id=user.id,
            question_text=validated['question_text'],
            question_type=validated['question_type'],
            # Section and topic come from the section the teacher chose. The
            # model's own idea of a topic is ignored on purpose.
            section_id=section.id,
            topic=section.title,
            difficulty=validated['difficulty'],
            explanation=validated['explanation'],
            points=validated['points'],
            misconception=item.get('misconception'),
            source='ai',
            status='DRAFT',
            generated_by='ai',
            model_name=practice.model_name(),
            prompt_version=practice.PROMPT_VERSION,
            created_at=datetime.utcnow(),
        )
        db.session.add(bq)
        db.session.flush()
        for idx, opt in enumerate(item['options']):
            db.session.add(QuestionBankOption(
                bank_question_id=bq.id,
                option_text=(opt.get('option_text') or '').strip(),
                is_correct=bool(opt.get('is_correct')),
                order_index=idx,
                feedback=(opt.get('feedback') or '').strip() or None,
            ))
        created.append(bq)

    db.session.commit()

    message = f'{len(created)} draf dibuat untuk bagian "{section.title}"'
    if skipped:
        message += f'; {skipped} hasil AI tidak disimpan karena tidak valid'
    return jsonify({
        'message': message,
        'created': [_serialize_bank(b) for b in created],
        'created_count': len(created),
        'skipped_count': skipped,
        'section_id': section.id,
    }), 201


@jwt_required()
def get_draft_queue():
    """Questions waiting for the teacher's review."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    status = (request.args.get('status') or 'DRAFT').strip().upper()
    query = QuestionBank.query
    if user.role != 'admin':
        query = query.filter_by(teacher_id=user.id)
    if status:
        query = query.filter_by(status=status)
    items = query.order_by(QuestionBank.created_at.desc()).all()

    return jsonify({
        'data': [_serialize_bank(b) for b in items],
        'status': status or None,
    }), 200


@jwt_required()
def approve_bank_draft(bank_id):
    """Teacher approval. This is the only path from DRAFT to APPROVED."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    bq, err = _owned_bank(bank_id, user)
    if err:
        return err

    if not any(bool(o.is_correct) for o in bq.options):
        return jsonify({'error': 'Soal ini tidak punya jawaban benar, tidak bisa disetujui'}), 400

    bq.status = 'APPROVED'
    bq.reviewed_by = user.id
    bq.reviewed_at = datetime.utcnow()
    bq.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'message': 'Soal disetujui dan siap dipakai sebagai latihan',
        'question': _serialize_bank(bq),
    }), 200


@jwt_required()
def reject_bank_draft(bank_id):
    """Teacher rejection. The row is kept so the decision stays auditable."""
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403
    bq, err = _owned_bank(bank_id, user)
    if err:
        return err

    bq.status = 'REJECTED'
    bq.reviewed_by = user.id
    bq.reviewed_at = datetime.utcnow()
    bq.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'message': 'Draf ditolak dan tidak akan dipakai sebagai latihan',
        'question': _serialize_bank(bq),
    }), 200


# ============================================================
# STUDENT SIDE (Fase 3d)
# ============================================================
#
# Gate yang dipakai ketiganya sama: siswa, materi sudah dipublikasikan, dan
# siswa berhak atas materi itu (kelas yang diikuti). Bagian juga harus benar
# milik materi tersebut, jadi tidak ada jalan untuk menjangkau bagian materi
# lain hanya karena tahu id-nya.

def _int_or_none(value):
    """Id dari kiriman yang mungkin rusak. None berarti "tidak ada id",
    bukan exception 500 dari dalam SQLAlchemy."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _practice_guard(material_id, section_id=None):
    user = _cur_user()
    if not user:
        return None, None, (jsonify({'error': 'User not found'}), 404)
    if user.role != 'student':
        return None, None, (jsonify({'error': 'Endpoint ini khusus siswa'}), 403)

    material = Material.query.get(_int_or_none(material_id))
    if not material:
        return None, None, (jsonify({'error': 'Materi tidak ditemukan'}), 404)
    if material.status != 'published':
        return None, None, (jsonify({'error': 'Materi belum dipublikasikan'}), 403)
    if not student_can_access_material(user, material):
        return None, None, (
            jsonify({'error': 'Materi hanya untuk kelas yang diikuti'}), 403)

    section = None
    if section_id is not None:
        section = MaterialSection.query.filter_by(
            id=_int_or_none(section_id), material_id=material.id).first()
        if not section:
            return None, None, (
                jsonify({'error': 'Bagian tidak ditemukan pada materi ini'}), 404)
    return user, (material, section), None


@jwt_required()
def get_student_practice_sections(material_id):
    """Bagian mana dari materi ini yang punya soal latihan, dan progress siswa."""
    user, ctx, err = _practice_guard(material_id)
    if err:
        return err
    material, _ = ctx

    sections = MaterialSection.query.filter_by(
        material_id=material.id).order_by(MaterialSection.position).all()
    approved = spractice.approved_count_map([s.id for s in sections])
    diagnostics = spractice.diagnostic_count_map([s.id for s in sections])
    stats = spractice.practice_stats(user.id, material.id)
    # Jawaban diagnostik siswa ini per bagian (mode='diagnostic'), dipakai UI
    # untuk gerbang "selesaikan asesmen dulu". Sumbernya satu query yang sama
    # dengan halaman asesmen, jadi angkanya tidak mungkin berbeda aturan.
    diag_stats = spractice.diagnostic_stats(user.id, material.id)

    rows = []
    for sec in sections:
        st = stats.get(sec.id, {'answered': 0, 'correct': 0, 'attempts': 0})
        dst = diag_stats.get(sec.id, {'answered': 0, 'correct': 0, 'attempts': 0})
        total = approved.get(sec.id, 0)
        diag_total = diagnostics.get(sec.id, 0)
        rows.append({
            'section_id': sec.id,
            'title': sec.title,
            'position': sec.position,
            # 0 = tidak ada soal yang disetujui guru. UI_DISABLE tombolnya
            # dan menjelaskan kenapa, bukan membuat soal lain.
            'practice_total': total,
            'practice_answered': st['answered'],
            'practice_correct': st['correct'],
            'practice_attempts': st['attempts'],
            'available': total > 0,
            # Pool diagnostik berdiri sendiri: 0 berarti bagian ini belum
            # punya soal pengukuran, dan tombol asesmen dimatikan.
            'diagnostic_total': diag_total,
            'diagnostic_available': diag_total > 0,
            # Wajib-sebelum-lanjut: berapa soal yang sudah dijawab siswa ini
            # dan berapa yang harus diselesaikan. Dibatasi MAX_SERVED karena
            # itulah jumlah soal yang benar-benar disajikan (sisanya tidak
            # mungkin dikerjakan, jadi tidak boleh ikut dihitung).
            'diagnostic_answered': dst['answered'],
            'diagnostic_required': min(diag_total, spractice.MAX_SERVED),
        })

    return jsonify({
        'material_id': material.id,
        'material_title': material.title,
        'sections': rows,
        'sections_with_practice': sum(1 for r in rows if r['available']),
        'sections_total': len(rows),
        # Reminder supaya angka latihan tidak dibaca sebagai nilai Finally.
        'note': 'Hanya soal yang sudah disetujui guru yang dihitung sebagai latihan.',
    }), 200


@jwt_required()
def get_student_practice_questions(material_id, section_id):
    """Soal latihan satu bagian. Kunci jawaban TIDAK ikut di respons ini."""
    user, ctx, err = _practice_guard(material_id, section_id)
    if err:
        return err
    material, section = ctx

    entries, session = spractice.session_for_section(material.id, section.id, user)
    items = spractice.approved_for_section(section.id)
    served = entries[:spractice.SESSION_SIZE]
    stats = spractice.practice_stats(user.id, material.id).get(
        section.id, {'answered': 0, 'correct': 0, 'attempts': 0})

    # Pesan hanya untuk kasus JUJUR (tidak ada soal). Pemotongan jendela sesi
    # bukan pesan galat: UI membacanya dari `session` (total/served/has_more)
    # supaya tidak memunculkan notifikasi berulang tiap sesi dimuat.
    message = None
    if not items:
        message = (f'Belum ada soal latihan yang disetujui guru untuk bagian '
                   f'"{section.title}".')

    questions = [
        spractice.question_for_student(
            e['bq'],
            difficulty=e['label'],
            difficulty_basis=e['basis'],
            difficulty_note=e['note'],
        ) for e in served
    ]

    return jsonify({
        'material_id': material.id,
        'section_id': section.id,
        'section_title': section.title,
        'questions': questions,
        'total_available': len(items),
        'total_served': len(served),
        'practice_answered': stats['answered'],
        'practice_correct': stats['correct'],
        'message': message,
        # Sesi adaptif: urutan + rumus pemilihan sasaran selalu ikut dikirim.
        'session': session,
    }), 200


@jwt_required()
def submit_student_practice_answer(material_id, section_id):
    """Nilai satu jawaban latihan dan catat-legal sebagai bukti belajar.

    Server memuat ulang soalnya dari bank dan mencocokkan `selected_option`
    dengan `order_index` yang tersimpan, jadi kiriman klien tidak bisa memilih
    kunci jawaban secara langsung.
    """
    user, ctx, err = _practice_guard(material_id, section_id)
    if err:
        return err
    material, section = ctx

    data = request.get_json(silent=True) or {}
    raw = data.get('selected_option', data.get('selected_index'))
    if raw is None:
        return jsonify({'error': 'Opsi jawaban belum dikirim'}), 400
    try:
        selected = int(raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'Opsi jawaban tidak valid'}), 400

    bq = QuestionBank.query.get(_int_or_none(data.get('bank_question_id')))
    if not bq:
        return jsonify({'error': 'Soal latihan tidak ditemukan'}), 404
    # Diperiksa ulang di sini, bukan hanya saat pemuatan: status bisa berubah
    # di antara keduanya dan soalnya bisa saja bukan milik bagian ini.
    if bq.status != 'APPROVED':
        return jsonify({'error': 'Soal ini belum disetujui guru, tidak bisa dikerjakan'}), 403
    if bq.section_id != section.id:
        return jsonify({'error': 'Soal ini bukan milik bagian yang diminta'}), 400
    # Pool terpisah, tidak boleh tertukar: soal diagnostik dijawab lewat jalur
    # diagnostik supaya catatannya tetap bisa dibedakan dan sesi adaptif tidak
    # pernah menyerap soal pengukuran.
    if (bq.purpose or 'practice') != 'practice':
        return jsonify({'error': 'Soal ini bagian dari asesmen diagnostik; '
                                 'kerjakan lewat menu Asesmen Diagnostik'}), 400

    graded = spractice.grade(bq, selected)
    if graded is None:
        return jsonify({'error': 'Opsi jawaban tidak ditemukan pada soal ini'}), 400

    row = spractice.record(user.id, material.id, section.id, bq, graded)
    db.session.commit()

    stats = spractice.practice_stats(user.id, material.id).get(
        section.id, {'answered': 0, 'correct': 0, 'attempts': 0})
    # Hitungan live (setelah baris ini tersimpan) supaya layar "selesai" tahu
    # apakah masih ada soal latihan yang belum pernah dikerjakan, tanpa
    # menebak dari state lama.
    bank_total, bank_seen = spractice.section_practice_counts(section.id, user.id)

    payload = dict(graded)
    payload.update({
        'section_id': section.id,
        'section_title': section.title,
        'attempt_no': row.attempt_no,
        'practice_answered': stats['answered'],
        'practice_correct': stats['correct'],
        'practice_total': bank_total,
        'practice_seen': bank_seen,
        'has_more': bank_seen < bank_total,
    })
    return jsonify(payload), 200


# ============================================================
# STUDENT SIDE: ASESMEN DIAGNOSTIK (Fase 4 level materi)
# ============================================================
#
# Dua pool yang tidak pernah bercampur:
#   - latihan adaptif  -> soal purpose='practice', urutan dari mesin 60/30/10
#   - asesmen diagnostik -> soal purpose='diagnostic', URUTAN TETAP
#
# Urutan tetap itu bukan detail kosmetik: membandingkan hasil antar-siswa dan
# antar-bagian hanya sah bila semuanya menjawab soal yang sama dengan urutan
# yang sama. Tidak ada satu pun field tingkat yang dihitung dari performa di
# sini - yang dikirim hanya soal apa adanya.

@jwt_required()
def get_student_diagnostic_questions(material_id, section_id):
    """Soal diagnostik satu bagian, urutan tetap. Kunci jawaban TIDAK ikut."""
    user, ctx, err = _practice_guard(material_id, section_id)
    if err:
        return err
    material, section = ctx

    items = spractice.diagnostic_for_section(section.id)
    served = items[:spractice.MAX_SERVED]
    stats = spractice.diagnostic_stats(user.id, material.id).get(
        section.id, {'answered': 0, 'correct': 0, 'attempts': 0})

    message = None
    if not items:
        message = (f'Bagian "{section.title}" belum punya soal diagnostik. '
                   f'Guru perlu menandai soal sebagai diagnostik di menu '
                   f'Latihan per Bagian.')
    elif len(items) > len(served):
        message = (f'Bagian ini punya {len(items)} soal diagnostik; '
                   f'{len(served)} ditampilkan sekaligus.')

    return jsonify({
        'material_id': material.id,
        'section_id': section.id,
        'section_title': section.title,
        'questions': [spractice.question_for_student(bq) for bq in served],
        'total_available': len(items),
        'total_served': len(served),
        'diagnostic_answered': stats['answered'],
        'diagnostic_correct': stats['correct'],
        'message': message,
        'session': {
            'basis': 'diagnostic',
            'basis_text': ('Asesmen diagnostik: urutan soal tetap dan tidak '
                           'disesuaikan dengan jawaban sebelumnya. Dipakai '
                           'mengukur tingkat materi, bukan untuk berlatih.'),
        },
    }), 200


@jwt_required()
def submit_student_diagnostic_answer(material_id, section_id):
    """Nilai satu jawaban diagnostik dan catat sebagai bukti pengukuran.

    Server memuat ulang soalnya dari bank dan mencocokkan opsi dengan
    `order_index` tersimpan, sama seperti jalur latihan: klien tidak bisa
    memilih kunci jawaban lewat kiriman.
    """
    user, ctx, err = _practice_guard(material_id, section_id)
    if err:
        return err
    material, section = ctx

    data = request.get_json(silent=True) or {}
    raw = data.get('selected_option', data.get('selected_index'))
    if raw is None:
        return jsonify({'error': 'Opsi jawaban belum dikirim'}), 400
    try:
        selected = int(raw)
    except (TypeError, ValueError):
        return jsonify({'error': 'Opsi jawaban tidak valid'}), 400

    bq = QuestionBank.query.get(_int_or_none(data.get('bank_question_id')))
    if not bq:
        return jsonify({'error': 'Soal diagnostik tidak ditemukan'}), 404
    if bq.status != 'APPROVED':
        return jsonify({'error': 'Soal ini belum disetujui guru, tidak bisa dikerjakan'}), 403
    if bq.section_id != section.id:
        return jsonify({'error': 'Soal ini bukan milik bagian yang diminta'}), 400
    if (bq.purpose or 'practice') != 'diagnostic':
        return jsonify({'error': 'Soal ini soal latihan; kerjakan lewat menu '
                                 'Latihan'}), 400

    graded = spractice.grade(bq, selected)
    if graded is None:
        return jsonify({'error': 'Opsi jawaban tidak ditemukan pada soal ini'}), 400

    row = spractice.record(user.id, material.id, section.id, bq, graded,
                           mode='diagnostic')
    db.session.commit()

    stats = spractice.diagnostic_stats(user.id, material.id).get(
        section.id, {'answered': 0, 'correct': 0, 'attempts': 0})

    payload = dict(graded)
    payload.update({
        'section_id': section.id,
        'section_title': section.title,
        'attempt_no': row.attempt_no,
        'diagnostic_answered': stats['answered'],
        'diagnostic_correct': stats['correct'],
    })
    return jsonify(payload), 200


@jwt_required()
def get_teacher_difficulty_observed():
    """Analisis tingkat soal otomatis dari performa (Fase 3f), cakupan guru.

    Mengembalikan dua sumber berdampingan untuk tiap soal dalam cakupan:

    - `declared_*`  : label guru/deklarasi (apa yang ditulis saat soal dibuat)
    - `observed`    : label terukur dari p-value jawaban siswa lintas kelas,
                      lengkap dengan n, p, selisih (±), dan `near_boundary`

    Label guru tidak pernah ditimpa oleh label terukur; keduanya dikirim
    berdampingan supaya pembaca bisa melihat persis sumber mana yang
    dipakai. Soal dengan n < MIN_DIFFICULTY_SAMPLE berstatus
    INSUFFICIENT_DATA: tidak ada label yang diklaim.

    Dua jenis soal yang dianalisis: soal bank (question_bank) dan soal
    interaktif (student_answers per content + question_index). Keduanya
    diukur dari data yang benar-benar ada, bukan dari teks soalnya.
    """
    user = _cur_user()
    if not _is_teacher(user):
        return jsonify({'error': 'Akses khusus guru'}), 403

    filters = {}
    raw_material = request.args.get('material_id')
    if raw_material:
        try:
            filters['material_id'] = int(raw_material)
        except (TypeError, ValueError):
            return jsonify({'error': 'material_id tidak valid'}), 400

    materials = teacher_materials(filters, teacher_id=user.id)
    material_ids = [m.id for m in materials]
    material_by_id = {m.id: m for m in materials}
    if not material_ids:
        return jsonify({
            'items': [],
            'counts': {'total': 0, 'observed_ready': 0, 'observed_insufficient': 0},
            'rules': _difficulty_rules(),
            'message': 'Belum ada materi dalam cakupan.',
        }), 200

    sections = MaterialSection.query.filter(
        MaterialSection.material_id.in_(material_ids)).all()
    section_ids = [s.id for s in sections]
    section_by_id = {s.id: s for s in sections}
    if not section_ids:
        return jsonify({
            'items': [],
            'counts': {'total': 0, 'observed_ready': 0, 'observed_insufficient': 0},
            'rules': _difficulty_rules(),
            'message': 'Materi belum punya bagian.',
        }), 200

    items = []

    # --- 1. soal bank (practice), semua status ---
    bank_rows = QuestionBank.query.filter(
        QuestionBank.section_id.in_(section_ids)).order_by(QuestionBank.id).all()
    bank_observed = qds.observed_bank_batch([b.id for b in bank_rows])
    for bq in bank_rows:
        section = section_by_id.get(bq.section_id)
        material = material_by_id.get(section.material_id) if section else None
        obs = bank_observed.get(bq.id) or qds.empty_observed(bq.id)
        declared_canon = normalize_difficulty(bq.difficulty)
        items.append({
            'kind': 'bank',
            'question_id': bq.id,
            'status': bq.status,
            'question_text': bq.question_text,
            'section_id': bq.section_id,
            'section_title': section.title if section else None,
            'material_id': material.id if material else None,
            'material_title': material.title if material else None,
            'declared_difficulty': bq.difficulty,
            'declared_label': difficulty_label(declared_canon) if declared_canon else '',
            'observed': obs,
            'observed_note': qds.observed_note(obs),
        })

    # --- 2. soal interaktif (student_answers per content + question_index) ---
    ia_rows = StudentAnswer.query.filter(
        StudentAnswer.section_id.in_(section_ids)).all()
    if ia_rows:
        ia_observed = qds.interactive_batch(ia_rows)
        content_ids = {r.content_id for r in ia_rows}
        contents = {c.id: c for c in MaterialContent.query.filter(
            MaterialContent.id.in_(content_ids)).all()}
        counts_by_slot = {}
        for r in ia_rows:
            slot = qds.interactive_slot_key(r)
            counts_by_slot.setdefault(slot, 0)
            counts_by_slot[slot] += 1
        for slot, obs in ia_observed.items():
            section_id, content_id, q_index = slot
            section = section_by_id.get(section_id)
            material = material_by_id.get(section.material_id) if section else None
            content = contents.get(content_id)
            data = content.data if content and isinstance(content.data, dict) else {}
            declared_canon = normalize_difficulty(data.get('difficulty'))
            preview = (data.get('question') or data.get('text') or data.get('prompt')
                       or (content.type if content else None) or '')
            items.append({
                'kind': 'interactive',
                'content_id': content_id,
                'question_index': q_index,
                'status': 'ANSWERED',
                'question_text': str(preview)[:200],
                'section_id': section_id,
                'section_title': section.title if section else None,
                'material_id': material.id if material else None,
                'material_title': material.title if material else None,
                'declared_difficulty': (data.get('difficulty')
                                        if isinstance(data, dict) else None),
                'declared_label': difficulty_label(declared_canon) if declared_canon else '',
                'observed': obs,
                'observed_note': qds.observed_note(obs),
                'answered_rows': counts_by_slot.get(slot, 0),
            })

    items.sort(key=lambda it: (
        it.get('material_id') or 0, it.get('section_id') or 0,
        0 if it['kind'] == 'bank' else 1, it.get('question_id') or 0))

    ready = sum(1 for it in items if it['observed'].get('status') == 'READY')
    insufficient = len(items) - ready

    return jsonify({
        'items': items,
        'counts': {
            'total': len(items),
            'observed_ready': ready,
            'observed_insufficient': insufficient,
            'bank': sum(1 for it in items if it['kind'] == 'bank'),
            'interactive': sum(1 for it in items if it['kind'] == 'interactive'),
        },
        'rules': _difficulty_rules(),
    }), 200


def _difficulty_rules():
    """Aturan hitung yang dipakai endpoint ini, ikut dikirim biar bisa ditelusuri."""
    return {
        'method': ('p-value: fraksi benar dari siswa BERBEDA yang mengerjakan '
                   '(jawaban pertama per siswa), dihitung global lintas kelas.'),
        'p_easy': cfg.DIFFICULTY_P_EASY,
        'p_hard': cfg.DIFFICULTY_P_HARD,
        'min_sample': cfg.MIN_DIFFICULTY_SAMPLE,
        'margin_z': cfg.DIFFICULTY_MARGIN_Z,
        'near_boundary': ('Rentang p ± margin memotong garis 0.40/0.70 → ditandai '
                          '"dekat batas", bukan dianggap pasti.'),
        'leave_one_out': ('Saat menilai satu siswa (sesi latihan), jawaban siswa '
                          'itu sendiri dikeluarkan dari hitungan.'),
        'declared_note': ('Label guru tidak pernah ditimpa; label terukur hidup '
                          'bersamanya dengan sumbernya masing-masing.'),
    }