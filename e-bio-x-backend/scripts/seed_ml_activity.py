# ============================================================
# TAHAP 5 - Seeder aktivitas belajar sintetis untuk melatih ML.
#
# Membuat 3 materi demo (published, ditautkan ke kelas guru lewat
# link_demo_materials) + kuis draf pendamping dengan 10 soal pilihan
# ganda, lalu mensimulasikan aktivitas belajar untuk siswa yang belum
# punya sinyal, dengan 4 arketipe (strong/good/fair/weak) agar Decision
# Tree & K-Means punya pola yang bisa dipelajari. Setiap submission
# demo disertai Answer rows sehingga skornya bisa diturunkan dari
# jawaban (tidak ada skor tanpa soal).
#
# Pemakaian:
#   python scripts/seed_ml_activity.py          # seed (idempoten)
#   python scripts/seed_ml_activity.py --reset  # hapus data demo lalu seed ulang
# ============================================================
import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, bindparam

from src import create_app
from src.config.database import db
from src.models.user import User
from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.material_content import MaterialContent
from src.models.material_student_state import MaterialStudentState
from src.models.material_progress import MaterialProgress
from src.models.student_answer import StudentAnswer
from src.models.learning_activity import LearningActivity
from src.models.quiz import Quiz
from src.models.question import Question
from src.models.option import Option
from src.models.submission import Submission
from src.models.answer import Answer
from src.models.course import Course
from src.models.enrollment import Enrollment

DEMO_PREFIX = '[Demo] '
DEMO_COURSE_NAME = DEMO_PREFIX + 'Biologi ML'
TEACHER_EMAIL = 'guru1@ebiox.com'

# Every student is seeded, not a hand-picked subset. The previous default
# of 28 left 47 of 76 students with too little data for the ML layer, so
# opening the dashboard as those students showed nothing at all. No
# exclusions either: student 72/73 were skipped historically, which is
# exactly the kind of arbitrary gap that makes a demo look broken.
TARGET_STUDENTS = 1000
EXCLUDE_STUDENT_IDS = set()
RNG_SEED = 20260823

MATERIAL_SPECS = [
    {
        'title': 'Sel dan Organel',
        'topic': 'SEL',
        'subject': 'Biologi',
        'phase': 'C',
        'class_level': 'VIII',
        'difficulty': 'mudah',
        'estimated_time': '2 JP',
        'description': 'Materi demo tentang struktur sel, organel, dan fungsinya.',
        'sections': ['Pengenalan Sel', 'Organel dan Fungsinya'],
    },
    {
        'title': 'Bakteri dan Peranannya',
        'topic': 'BAKTERI',
        'subject': 'Biologi',
        'phase': 'C',
        'class_level': 'VIII',
        'difficulty': 'sedang',
        'estimated_time': '3 JP',
        'description': 'Materi demo tentang ciri bakteri, reproduksi, dan peranannya.',
        'sections': ['Ciri dan Struktur Bakteri', 'Peranan Bakteri'],
    },
    {
        'title': 'Virus dan Replikasinya',
        'topic': 'VIRUS',
        'subject': 'Biologi',
        'phase': 'D',
        'class_level': 'IX',
        'difficulty': 'sulit',
        'estimated_time': '3 JP',
        'description': 'Materi demo tentang struktur virus, siklus litik-lisogenik.',
        'sections': ['Struktur Virus', 'Siklus Replikasi Virus'],
    },
]

QUESTION_BANK = {
    'SEL': [
        ('Bagian sel yang mengontrol seluruh aktivitas sel adalah?', ['Membran sel', 'Nukleus', 'Sitoplasma', 'Dinding sel'], 1),
        ('Organel tempat respirasi sel disebut?', ['Ribosom', 'Vakuola', 'Mitokondria', 'Kloroplas'], 2),
        ('Dinding sel pada tumbuhan tersusun atas?', ['Kitin', 'Selulosa', 'Peptidoglikan', 'Lipid'], 1),
        ('Proses makanan dicerna di dalam sel terjadi pada?', ['Lisosom', 'Badan Golgi', 'RE halus', 'Nukleolus'], 0),
        ('Organel yang berperan dalam sintesis protein adalah?', ['Lisosom', 'Ribosom', 'Mitokondria', 'Vakuola'], 1),
        ('Bagian sel yang mengatur keluar masuknya zat adalah?', ['Nukleus', 'Ribosom', 'Membran sel', 'Badan Golgi'], 2),
        ('Organel yang hanya dimiliki sel tumbuhan dan berperan dalam fotosintesis adalah?', ['Mitokondria', 'Kloroplas', 'Ribosom', 'Badan Golgi'], 1),
        ('Cairan sel tempat organel tersuspensi disebut?', ['Sitoplasma', 'Nukleoplasma', 'Matriks', 'Plasma'], 0),
        ('Organel yang menyimpan air dan zat pada sel tumbuhan adalah?', ['Lisosom', 'Ribosom', 'Vakuola', 'Peroksisom'], 2),
        ('Badan Golgi berfungsi untuk?', ['Mengemas dan mengangkut protein', 'Menghasilkan energi', 'Mencerna zat asing', 'Mensintesis lemak'], 0),
    ],
    'BAKTERI': [
        ('Bakteri berkembang biak dengan pembelahan binary fission pada kondisi?', ['Baik', 'Buruk', 'Ekstrem', 'Kering'], 0),
        ('Bentuk bakteri berbentuk batang disebut?', ['Kokus', 'Basil', 'Spiril', 'Vibrio'], 1),
        ('Zat yang dibuat oleh bakteri untuk melawan bakteri lain adalah?', ['Antibiotik', 'Antigen', 'Toksin', 'Enzim'], 0),
        ('Kelompok bakteri penghasil asam dalam yoghurt adalah?', ['Lactobacillus', 'E. coli', 'Salmonella', 'Nitrosomonas'], 0),
        ('Struktur bakteri yang berfungsi sebagai alat gerak adalah?', ['Kapsul', 'Flagel', 'Pili', 'Dinding sel'], 1),
        ('Bakteri yang menguntungkan dalam pembuatan keju dan mentega adalah?', ['Lactobacillus', 'Salmonella', 'Mycobacterium', 'Clostridium'], 0),
        ('Pewarnaan Gram membedakan bakteri menjadi?', ['Aerob dan anaerob', 'Gram positif dan Gram negatif', 'Autotrof dan heterotrof', 'Kokus dan basil'], 1),
        ('Bakteri yang dapat menambat nitrogen di tanah adalah?', ['Rhizobium', 'E. coli', 'Streptococcus', 'Vibrio'], 0),
        ('Bagian bakteri yang berperan sebagai materi genetik adalah?', ['Ribosom', 'DNA pada nukleoid', 'Membran plasma', 'Flagel'], 1),
        ('Bakteri yang menyebabkan penyakit tuberkulosis adalah?', ['Mycobacterium tuberculosis', 'Vibrio cholerae', 'Salmonella typhi', 'Clostridium tetani'], 0),
    ],
    'VIRUS': [
        ('Siklus virus yang langsung memecah sel inang disebut siklus?', ['Lisogenik', 'Litik', 'Biner', 'Konjugasi'], 1),
        ('Bahan genetik virus dapat berupa?', ['DNA saja', 'RNA saja', 'DNA atau RNA', 'Protein'], 2),
        ('Selubung protein virus disebut?', ['Kapsid', 'Membran', 'Dinding', 'Sitoplasma'], 0),
        ('Virus tidak dianggap organisme karena?', ['Ukuran kecil', 'Tidak bisa dikristalkan', 'Tidak memiliki sel', 'Tidak bereproduksi'], 2),
        ('Bagian virus yang berfungsi sebagai material genetik adalah?', ['Kapsid', 'Asam nukleat', 'Selubung', 'Ekor'], 1),
        ('Virus yang menyerang bakteri disebut?', ['Bakteriofag', 'Retrovirus', 'Papillomavirus', 'Coronavirus'], 0),
        ('Tahap pertama infeksi virus ke sel inang adalah?', ['Penetrasi', 'Adsorpsi', 'Replikasi', 'Lisis'], 1),
        ('Virus penyebab penyakit AIDS adalah?', ['HIV', 'HBV', 'H5N1', 'SARS-CoV-2'], 0),
        ('Vaksin bekerja dengan cara?', ['Membunuh semua virus', 'Merangsang kekebalan tubuh', 'Mengganti sel yang rusak', 'Menambah asam nukleat'], 1),
        ('Siklus virus yang menyisipkan materi genetik ke DNA inang disebut?', ['Litik', 'Lisogenik', 'Biner', 'Konjugasi'], 1),
    ],
}

# Kuis demo memakai seluruh bank (10 soal), materi memakai 4 soal pertama
# (2 per bagian). 10 soal x 10 poin, sehingga persentase selalu kelipatan
# 10 dan konsisten dengan correct_count.
N_QUIZ_QUESTIONS = 10
QUIZ_QUESTION_POINTS = 10


ARCHETYPES = {
    # label: (jumlah, akurasi_min, akurasi_max, quiz_min, quiz_max, completion_min, completion_max, menit_min, menit_max)
    'strong': (8, 0.85, 0.97, 88, 98, 0.90, 1.00, 90, 150),
    'good':   (8, 0.72, 0.85, 76, 88, 0.70, 0.95, 60, 110),
    'fair':   (7, 0.55, 0.70, 58, 74, 0.40, 0.75, 30, 70),
    'weak':   (5, 0.35, 0.52, 40, 56, 0.15, 0.45, 15, 45),
}

ARCHETYPE_ORDER = ['strong'] * 8 + ['good'] * 8 + ['fair'] * 7 + ['weak'] * 5


def demo_materials():
    """Materials created by THIS script.

    The prefix is compared in Python, case-sensitively, on purpose.
    MySQL's LIKE is case-insensitive under the default collation, so
    `title.like('[Demo] %')` also matched the product's real material
    '[DEMO] VIRUS' (id=107). Worse, reset_demo() deletes whatever this
    returns - so the SQL version would have wiped genuine demo content.
    """
    return [m for m in Material.query.all() if m.title.startswith(DEMO_PREFIX)]


def demo_quizzes():
    """Quizzes created by THIS script (same case-sensitivity reason)."""
    return [q for q in Quiz.query.all()
            if q.title.startswith(DEMO_PREFIX + 'Kuis')]


def ensure_quiz_questions(quiz):
    """Create a demo quiz's Question/Option rows once, return the questions.

    The first seeding pass created a quiz, a title and a score for every
    submitter, but no questions at all - so opening the quiz or reviewing a
    submission showed nothing. Questions come from the same topic bank as
    the material: 10 multiple-choice items, 10 points each, so a graded
    percentage is always a multiple of 10 and can be reproduced from the
    answers. Idempotent.
    """
    existing = sorted(quiz.questions, key=lambda q: q.order_index)
    if existing:
        return existing
    material = quiz.material
    topic = (material.topic if material is not None else None) or 'SEL'
    bank = QUESTION_BANK.get(topic, QUESTION_BANK['SEL'])[:N_QUIZ_QUESTIONS]
    diff_bucket = {'mudah': 'easy', 'sedang': 'medium', 'sulit': 'hard'}.get(
        material.difficulty if material is not None else None, 'medium')
    questions = []
    for i, (text, options, correct_idx) in enumerate(bank):
        q = Question(quiz_id=quiz.id, text=text, question_type='multiple_choice',
                     difficulty=diff_bucket, points=QUIZ_QUESTION_POINTS,
                     order_index=i)
        db.session.add(q)
        db.session.flush()
        for oi, opt_text in enumerate(options):
            db.session.add(Option(question_id=q.id, option_text=opt_text,
                                  is_correct=(oi == correct_idx), order_index=oi))
        questions.append(q)
    db.session.flush()
    return questions


def _correct_positions(n_questions, correct_n, seed):
    """Which question positions are correct, varied but reproducible."""
    n = max(0, min(correct_n, n_questions))
    return set(random.Random(seed).sample(range(n_questions), n))


def seed_answers_for(submission, questions, correct_n, seed, answered_at=None):
    """Create the Answer rows that justify a submission's stored score.

    Full credit per question (the same formula as quiz_controller
    `_grade_submission`), exactly `correct_n` correct, so the stored
    percentage can be recomputed from the answers instead of floating free.
    """
    positions = _correct_positions(len(questions), correct_n, seed)
    rng = random.Random(seed + 7919)
    for pos, q in enumerate(questions):
        options = sorted(q.options, key=lambda o: o.order_index)
        is_correct = pos in positions
        if is_correct:
            chosen = next((o for o in options if o.is_correct), None)
        else:
            wrongs = [o for o in options if not o.is_correct]
            chosen = rng.choice(wrongs) if wrongs else None
        db.session.add(Answer(
            submission_id=submission.id, question_id=q.id,
            student_id=submission.student_id,
            option_id=chosen.id if chosen else None,
            is_correct=is_correct,
            points_earned=(q.points if is_correct else 0),
            answered_at=answered_at or submission.submitted_at,
        ))


def backfill_demo_quiz_content():
    """Fill in demo quiz questions and per-submission answers.

    The first seeding pass wrote scores with no Question/Answer rows, so a
    submission could not be reviewed and its score could not be recomputed.
    This creates the questions and then, for every submission that has no
    answers yet, the answers that earn its score - snapping the stored
    percentage to what those answers actually sum to. Idempotent: it never
    touches a submission that already has answers (e.g. a real attempt).
    """
    quizzes_new = 0
    submissions_filled = 0
    answers_new = 0
    for quiz in demo_quizzes():
        had = Question.query.filter_by(quiz_id=quiz.id).count()
        questions = ensure_quiz_questions(quiz)
        if not had and questions:
            quizzes_new += 1
        if not questions:
            continue
        n_q = len(questions)
        total_points = sum(q.points or 0 for q in questions)
        for sub in Submission.query.filter_by(quiz_id=quiz.id).all():
            if Answer.query.filter_by(submission_id=sub.id).first() is not None:
                continue
            correct_n = max(0, min(n_q, sub.correct_count or 0))
            seed_answers_for(sub, questions, correct_n,
                             seed=sub.student_id * 131 + quiz.id,
                             answered_at=sub.completed_at or sub.submitted_at)
            earned = correct_n * QUIZ_QUESTION_POINTS
            sub.score = round(earned / total_points * 100, 1) if total_points else 0
            sub.percentage = sub.score
            sub.correct_count = correct_n
            sub.wrong_count = n_q - correct_n
            sub.unanswered_count = 0
            submissions_filled += 1
            answers_new += n_q
        db.session.commit()
    return quizzes_new, submissions_filled, answers_new


def build_materials(teacher_id):
    """Create demo materials once. Returns list of Material."""
    existing = demo_materials()
    if existing:
        return existing
    materials = []
    for spec in MATERIAL_SPECS:
        m = Material(
            title=DEMO_PREFIX + spec['title'],
            description=spec['description'] + ' (data demo untuk pelatihan ML)',
            subject=spec['subject'], phase=spec['phase'], class_level=spec['class_level'],
            topic=spec['topic'], difficulty=spec['difficulty'],
            estimated_time=spec['estimated_time'],
            status='published', teacher_id=teacher_id,
        )
        db.session.add(m)
        db.session.flush()
        diff_bucket = {'mudah': 'easy', 'sedang': 'medium', 'sulit': 'hard'}[spec['difficulty']]
        for pos, sec_title in enumerate(spec['sections']):
            sec = MaterialSection(title=sec_title, position=pos, material_id=m.id)
            db.session.add(sec)
            db.session.flush()
            db.session.add(MaterialContent(section_id=sec.id, type='text', position=0,
                                           data={'text': f'Ringkasan materi {sec_title.lower()}.'}))
            bank = QUESTION_BANK[spec['topic']]
            db.session.add(MaterialContent(
                section_id=sec.id, type='interactive', position=1,
                data={'difficulty': diff_bucket, 'questions': [
                    {'question': q, 'options': opts, 'correct_answer': ans}
                    for (q, opts, ans) in bank[pos * 2:pos * 2 + 2]
                ]}))
        quiz = Quiz(
            title=DEMO_PREFIX + 'Kuis ' + spec['title'], description='Kuis demo ML',
            material_id=m.id, duration=10, passing_grade=75, max_attempts=1,
            status='draft', created_by=teacher_id,
        )
        db.session.add(quiz)
        db.session.flush()
        ensure_quiz_questions(quiz)
        materials.append(m)
    db.session.commit()
    return materials


def demo_course():
    return Course.query.filter_by(name=DEMO_COURSE_NAME).first()


def ensure_demo_course(teacher_id, student_ids):
    """Kelas demo milik guru agar siswa seed tercakup di analitik guru."""
    course = demo_course()
    if course is None:
        course = Course(name=DEMO_COURSE_NAME, teacher_id=teacher_id)
        db.session.add(course)
        db.session.flush()
    existing = {e.student_id for e in Enrollment.query.filter_by(course_id=course.id).all()}
    added = 0
    for sid in student_ids:
        if sid not in existing:
            db.session.add(Enrollment(student_id=sid, course_id=course.id))
            added += 1
    db.session.commit()
    return course.id, added


def link_demo_materials(materials, teacher_id):
    """Tautkan materi demo ke seluruh course milik gurunya.

    Materi tanpa course link bukan materi publik (lihat
    learning_analytics_service.student_can_access_material) - ia hanya
    terjangkau lewat gurunya. Materi demo yang dibiarkan tanpa link dulu
    "kebetulan" terlihat; setelah aturan itu diperbaiki, mereka mengambang
    di luar kelas mana pun. Menautkannya ke semua course guru mempertahankan
    cakupan siswa yang sama (termasuk siswa yang ada di course non-demo
    tetapi sudah punya state pada materi ini) sekaligus membuat
    keanggotaan kelasnya eksplisit.

    Idempoten: aman dijalankan berulang kali.
    """
    courses = Course.query.filter_by(teacher_id=teacher_id).all()
    linked = 0
    for m in materials:
        have = {c.id for c in m.course_links}
        for c in courses:
            if c.id not in have:
                m.course_links.append(c)
                linked += 1
    if linked:
        db.session.commit()
    return linked


_DEMO_CHILD_COLUMNS = [
    # Every column with a direct FK to the demo materials. They must all be
    # gone before the material row itself, otherwise MySQL rejects the
    # delete (recommendations.material_id, for instance, is NOT NULL and
    # SQLAlchemy would try to null it). Ordered children-first where one
    # child references another (material_file_texts -> material_files).
    ('learning_activities', 'material_id'),
    ('learning_sessions', 'material_id'),
    ('material_bookmarks', 'material_id'),
    ('material_file_texts', 'material_id'),
    ('material_files', 'material_id'),
    ('material_progress', 'material_id'),
    ('material_student_state', 'material_id'),
    ('recommendations', 'material_id'),
    ('student_answers', 'material_id'),
    ('student_content_track', 'material_id'),
    ('student_notes', 'material_id'),
    ('video_progress', 'material_id'),
    ('topic_knowledge', 'source_material_id'),
    ('quiz_explanations', 'source_material_id'),
    ('quiz_explanations', 'recommended_material_id'),
    ('forums', 'material_id'),
]


def _delete_material_children(mat_ids):
    """Delete every row that points at the given demo materials."""
    for table, col in _DEMO_CHILD_COLUMNS:
        db.session.execute(
            text(f'DELETE FROM `{table}` WHERE `{col}` IN :ids').bindparams(
                bindparam('ids', expanding=True)),
            {'ids': mat_ids})


def reset_demo():
    course = demo_course()
    if course is not None:
        Enrollment.query.filter_by(course_id=course.id).delete(synchronize_session=False)
        db.session.delete(course)
    mats = demo_materials()
    mat_ids = [m.id for m in mats]
    quiz_ids = [q.id for q in demo_quizzes()]
    if quiz_ids:
        # Delete children before parents: MySQL InnoDB enforces the FKs
        # answers -> submissions/questions/options, options -> questions,
        # and questions/submissions -> quizzes. Bulk .delete() skips the
        # ORM cascade, so the order must be explicit or the delete fails
        # with a foreign-key error.
        sub_ids = [r.id for r in Submission.query.filter(
            Submission.quiz_id.in_(quiz_ids)).with_entities(Submission.id).all()]
        q_ids = [r.id for r in Question.query.filter(
            Question.quiz_id.in_(quiz_ids)).with_entities(Question.id).all()]
        if sub_ids:
            Answer.query.filter(Answer.submission_id.in_(sub_ids)).delete(synchronize_session=False)
        if q_ids:
            Answer.query.filter(Answer.question_id.in_(q_ids)).delete(synchronize_session=False)
            Option.query.filter(Option.question_id.in_(q_ids)).delete(synchronize_session=False)
        Submission.query.filter(Submission.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
        Question.query.filter(Question.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
        Quiz.query.filter(Quiz.id.in_(quiz_ids)).delete(synchronize_session=False)
    if mat_ids:
        # Every table pointing at the materials must be cleared first, or
        # the delete trips over a foreign key (see _DEMO_CHILD_COLUMNS).
        # Sections/contents/files then cascade from the ORM delete.
        _delete_material_children(mat_ids)
        for m in mats:
            db.session.delete(m)
    db.session.commit()
    return len(mat_ids)


def pick_students():
    """Students whose feature row cannot be built yet.

    The old check was "has no signals at all", which left students with
    1-2 signals permanently stuck below MIN_SIGNALS_FOR_STUDENT even after
    seeding: they looked non-empty so they were skipped, yet they were
    still not enough. Delegating to aggregate_student_features asks the
    real question - can the ML layer build a row for this student yet?
    """
    from src.ml.feature_service import aggregate_student_features
    candidates = [s for s in User.query.filter_by(role='student').all()
                  if s.id not in EXCLUDE_STUDENT_IDS]
    needs_data = [s for s in candidates if aggregate_student_features(s) is None]
    return sorted(needs_data, key=lambda s: s.id)[:TARGET_STUDENTS]


def simulate(student, materials, rng):
    idx = student.id % len(ARCHETYPE_ORDER)
    arch = ARCHETYPE_ORDER[idx]
    _, amin, amax, qmin, qmax, cmin, cmax, tmin, tmax = ARCHETYPES[arch]
    acc = rng.uniform(amin, amax)
    quiz_mean = rng.uniform(qmin, qmax)
    comp_frac = rng.uniform(cmin, cmax)
    minutes_total = rng.uniform(tmin, tmax)

    n_study = 2 + (student.id % 2)
    studied = [materials[(student.id + off) % len(materials)] for off in range(n_study)]
    base = datetime.utcnow() - timedelta(days=rng.randint(10, 45))
    cursor = base

    def tick(days=1.5):
        nonlocal cursor
        cursor += timedelta(days=rng.uniform(0.2, days))
        return cursor

    for mat in studied:
        secs = sorted(mat.sections, key=lambda s: s.position)
        n_view = max(1, min(len(secs), round(comp_frac * len(secs))))
        learned_secs = secs[:n_view]
        done_all = n_view == len(secs)

        state = MaterialStudentState.query.filter_by(
            material_id=mat.id, student_id=student.id).first()
        if state is None:
            state = MaterialStudentState(
                material_id=mat.id, student_id=student.id,
                last_section_id=learned_secs[-1].id,
                total_learning_seconds=int(minutes_total * 60 / n_study),
                first_accessed_at=cursor, last_accessed=cursor,
                completed=done_all, completed_at=tick() if done_all else None,
            )
            db.session.add(state)

        # Guard against re-seeding: MaterialProgress has a unique key on
        # (material, section, student), so a second pass would crash the
        # whole run part-way through with a duplicate-entry error.
        already = {(p.section_id) for p in MaterialProgress.query.filter_by(
            student_id=student.id, material_id=mat.id).all()}
        for sec in learned_secs:
            db.session.add(LearningActivity(
                student_id=student.id, material_id=mat.id, section_id=sec.id,
                event_type='section_view', created_at=tick(0.6)))
            if sec.id in already:
                continue
            db.session.add(MaterialProgress(
                material_id=mat.id, section_id=sec.id, student_id=student.id,
                completed_at=cursor))

            interactive = [c for c in sec.contents if c.type == 'interactive']
            for content in interactive:
                questions = (content.data or {}).get('questions', [])
                # Same re-seed guard for StudentAnswer.
                answered_q = {a.question_index for a in StudentAnswer.query.filter_by(
                    student_id=student.id, content_id=content.id).all()}
                for qi, qd in enumerate(questions):
                    if qi in answered_q:
                        continue
                    correct_idx = qd.get('correct_answer')
                    is_correct = rng.random() < acc
                    options = qd.get('options', [])
                    if is_correct or not options:
                        selected = correct_idx
                    else:
                        wrong = [i for i in range(len(options)) if i != correct_idx]
                        selected = rng.choice(wrong) if wrong else correct_idx
                    db.session.add(StudentAnswer(
                        student_id=student.id, material_id=mat.id, section_id=sec.id,
                        content_id=content.id, selected_answer=selected,
                        is_correct=is_correct, question_index=qi, answered_at=tick(0.3)))

        quiz = Quiz.query.filter_by(material_id=mat.id, title=DEMO_PREFIX + 'Kuis ' +
                                   mat.title.replace(DEMO_PREFIX, '')).first()
        if quiz is None:
            continue
        quiz_questions = ensure_quiz_questions(quiz)
        n_q = len(quiz_questions) or N_QUIZ_QUESTIONS
        pct = max(25.0, min(100.0, rng.gauss(quiz_mean, 5)))
        correct_n = int(round(pct / 100 * n_q))
        # Snap the score to what the answers will earn (n_q questions worth
        # QUIZ_QUESTION_POINTS each) so submission and answers agree.
        pct = correct_n / n_q * 100.0
        submitted = tick(1.0)
        # Skip if this student already has a submitted attempt on the
        # quiz, otherwise re-seeding piles up duplicate attempts and
        # inflates quiz_attempts / quiz_average.
        if Submission.query.filter_by(
                quiz_id=quiz.id, student_id=student.id,
                status='submitted').first() is None:
            sub = Submission(
                quiz_id=quiz.id, student_id=student.id, attempt_number=1,
                started_at=submitted - timedelta(minutes=12),
                work_time=None, submitted_at=submitted, completed_at=submitted,
                score=round(pct, 1), percentage=round(pct, 1),
                correct_count=correct_n, wrong_count=n_q - correct_n,
                unanswered_count=0, status='submitted')
            db.session.add(sub)
            db.session.flush()
            seed_answers_for(sub, quiz_questions, correct_n,
                             seed=student.id * 131 + quiz.id,
                             answered_at=submitted)
    db.session.commit()


def main():
    do_reset = '--reset' in sys.argv
    app = create_app()
    with app.app_context():
        teacher = User.query.filter_by(email=TEACHER_EMAIL, role='teacher').first()
        if teacher is None:
            teachers = User.query.filter_by(role='teacher').all()
            teacher = teachers[0] if teachers else None
        if teacher is None:
            print('ERROR: tidak ada guru di database')
            return

        if do_reset:
            removed = reset_demo()
            print(f'reset: {removed} materi demo dihapus')

        if demo_materials():
            print('materi demo sudah ada, lewati pembuatan (pakai --reset untuk ulang)')
            materials = demo_materials()
        else:
            materials = build_materials(teacher.id)
            print(f'dibuat {len(materials)} materi demo + kuis draf')

        # Lengkapi kuis demo dengan soal + jawaban (lihat
        # backfill_demo_quiz_content). Dijalankan sebelum simulasi supaya
        # submission lama ikut diperbaiki dan skornya konsisten dengan
        # jawaban yang tersimpan.
        q_new, sub_filled, ans_new = backfill_demo_quiz_content()
        print(f'kuis demo: {q_new} kuis diberi soal, {sub_filled} submission '
              f'dilengkapi jawaban ({ans_new} jawaban)')

        students = pick_students()
        print(f'mensimulasikan aktivitas untuk {len(students)} siswa...')
        rng = random.Random(RNG_SEED)
        for s in students:
            simulate(s, materials, rng)

        # siswa yang punya aktivitas pada materi demo -> daftarkan ke kelas demo
        mat_ids = [m.id for m in materials]
        seeded_ids = {r.student_id for r in StudentAnswer.query.filter(
            StudentAnswer.material_id.in_(mat_ids)).all()}
        course_id, added = ensure_demo_course(teacher.id, sorted(seeded_ids))
        print(f'kelas demo id={course_id}: {added} siswa didaftarkan '
              f'(total anggota: {Enrollment.query.filter_by(course_id=course_id).count()})')

        # Tautkan materi demo ke kelas guru. Tanpa ini materi mengambang
        # di luar kelas (lihat link_demo_materials).
        changed = link_demo_materials(materials, teacher.id)
        owner_courses = Course.query.filter_by(teacher_id=teacher.id).all()
        print(f'tautan materi->course: {changed} tautan baru '
              f'({len(materials)} materi x {len(owner_courses)} kelas guru)')

        # verifikasi readiness
        from src.ml.feature_service import aggregate_student_features
        ready = 0
        dist = {'strong': [], 'good': [], 'fair': [], 'weak': []}
        for s in User.query.filter_by(role='student').all():
            row = aggregate_student_features(s)
            if row is not None:
                ready += 1
        print(f'siswa dengan sinyal cukup (>= MIN_SIGNALS): {ready}')
        print('selesai.')


if __name__ == '__main__':
    main()
