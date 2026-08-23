# ============================================================
# TAHAP 5 - Seeder aktivitas belajar sintetis untuk melatih ML.
#
# Membuat 3 materi demo (published, tanpa course link sehingga
# dapat diakses semua siswa) + kuis draf pendamping, lalu
# mensimulasikan aktivitas belajar untuk 28 siswa yang belum
# punya sinyal, dengan 4 arketipe (strong/good/fair/weak)
# agar Decision Tree & K-Means punya pola yang bisa dipelajari.
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
from src.models.submission import Submission
from src.models.course import Course
from src.models.enrollment import Enrollment

DEMO_PREFIX = '[Demo] '
DEMO_COURSE_NAME = DEMO_PREFIX + 'Biologi ML'
TEACHER_EMAIL = 'guru1@ebiox.com'
EXCLUDE_STUDENT_IDS = {72, 73}
TARGET_STUDENTS = 28
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
    ],
    'BAKTERI': [
        ('Bakteri berkembang biak dengan pembelahan binary fission pada kondisi?', ['Baik', 'Buruk', 'Ekstrem', 'Kering'], 0),
        ('Bentuk bakteri berbentuk batang disebut?', ['Kokus', 'Basil', 'Spiril', 'Vibrio'], 1),
        ('Zat yang dibuat oleh bakteri untuk melawan bakteri lain adalah?', ['Antibiotik', 'Antigen', 'Toksin', 'Enzim'], 0),
        ('Kelompok bakteri penghasil asam dalam yoghurt adalah?', ['Lactobacillus', 'E. coli', 'Salmonella', 'Nitrosomonas'], 0),
    ],
    'VIRUS': [
        ('Siklus virus yang langsung memecah sel inang disebut siklus?', ['Lisogenik', 'Litik', 'Biner', 'Konjugasi'], 1),
        ('Bahan genetik virus dapat berupa?', ['DNA saja', 'RNA saja', 'DNA atau RNA', 'Protein'], 2),
        ('Selubung protein virus disebut?', ['Kapsid', 'Membran', 'Dinding', 'Sitoplasma'], 0),
        ('Virus tidak dianggap organisme karena?', ['Ukuran kecil', 'Tidak bisa dikristalkan', 'Tidak memiliki sel', 'Tidak bereproduksi'], 2),
    ],
}

ARCHETYPES = {
    # label: (jumlah, akurasi_min, akurasi_max, quiz_min, quiz_max, completion_min, completion_max, menit_min, menit_max)
    'strong': (8, 0.85, 0.97, 88, 98, 0.90, 1.00, 90, 150),
    'good':   (8, 0.72, 0.85, 76, 88, 0.70, 0.95, 60, 110),
    'fair':   (7, 0.55, 0.70, 58, 74, 0.40, 0.75, 30, 70),
    'weak':   (5, 0.35, 0.52, 40, 56, 0.15, 0.45, 15, 45),
}

ARCHETYPE_ORDER = ['strong'] * 8 + ['good'] * 8 + ['fair'] * 7 + ['weak'] * 5


def demo_materials():
    return Material.query.filter(Material.title.like(DEMO_PREFIX + '%')).all()


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


def reset_demo():
    course = demo_course()
    if course is not None:
        Enrollment.query.filter_by(course_id=course.id).delete(synchronize_session=False)
        db.session.delete(course)
    mats = demo_materials()
    mat_ids = [m.id for m in mats]
    quiz_ids = [q.id for q in Quiz.query.filter(Quiz.title.like(DEMO_PREFIX + 'Kuis%')).all()]
    if quiz_ids:
        Submission.query.filter(Submission.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
        Quiz.query.filter(Quiz.id.in_(quiz_ids)).delete(synchronize_session=False)
    if mat_ids:
        StudentAnswer.query.filter(StudentAnswer.material_id.in_(mat_ids)).delete(synchronize_session=False)
        MaterialProgress.query.filter(MaterialProgress.material_id.in_(mat_ids)).delete(synchronize_session=False)
        LearningActivity.query.filter(LearningActivity.material_id.in_(mat_ids)).delete(synchronize_session=False)
        MaterialStudentState.query.filter(MaterialStudentState.material_id.in_(mat_ids)).delete(synchronize_session=False)
        for m in mats:
            db.session.delete(m)
    db.session.commit()
    return len(mat_ids)


def pick_students():
    students = [s for s in User.query.filter_by(role='student').all()
                if s.id not in EXCLUDE_STUDENT_IDS]
    has_signal_ids = {r.student_id for r in StudentAnswer.query.all()}
    has_signal_ids |= {r.student_id for r in Submission.query.filter_by(status='submitted').all()}
    fresh = [s for s in students if s.id not in has_signal_ids]
    return sorted(fresh, key=lambda s: s.id)[:TARGET_STUDENTS]


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

        state = MaterialStudentState(
            material_id=mat.id, student_id=student.id,
            last_section_id=learned_secs[-1].id,
            total_learning_seconds=int(minutes_total * 60 / n_study),
            first_accessed_at=cursor, last_accessed=cursor,
            completed=done_all, completed_at=tick() if done_all else None,
        )
        db.session.add(state)

        for sec in learned_secs:
            db.session.add(LearningActivity(
                student_id=student.id, material_id=mat.id, section_id=sec.id,
                event_type='section_view', created_at=tick(0.6)))
            db.session.add(MaterialProgress(
                material_id=mat.id, section_id=sec.id, student_id=student.id,
                completed_at=cursor))

            interactive = [c for c in sec.contents if c.type == 'interactive']
            for content in interactive:
                questions = (content.data or {}).get('questions', [])
                for qi, qd in enumerate(questions):
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
        pct = max(25.0, min(100.0, rng.gauss(quiz_mean, 5)))
        n_virtual = 10
        correct_n = int(round(pct / 100 * n_virtual))
        submitted = tick(1.0)
        db.session.add(Submission(
            quiz_id=quiz.id, student_id=student.id, attempt_number=1,
            started_at=submitted - timedelta(minutes=12),
            work_time=None, submitted_at=submitted, completed_at=submitted,
            score=round(pct, 1), percentage=round(pct, 1),
            correct_count=correct_n, wrong_count=n_virtual - correct_n,
            unanswered_count=0, status='submitted'))
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
