# ============================================================
# TAHAP 5 - ML data preparation / feature engineering.
#
# Converts raw Tahap-4 data into one aggregated feature row per
# student. `student_id` is ONLY an identifier, never a model feature.
#
# Mapping DB field -> ML feature:
#   MDone/materials                              -> material_completion_rate
#   completed sections / total sections          -> section_completion_rate
#   submissions.percentage (mean)                -> quiz_average
#   submissions.percentage (max)                 -> quiz_best_score
#   practice_answers by effective difficulty     -> easy/medium/hard_accuracy
#   learning_sessions / state total seconds      -> learning_minutes
#   submissions count                            -> quiz_attempts
#   quiz correct / answered                      -> correct_rate
#   forum_posts (no parent)                      -> forum_posts_count
#   forum_posts (with parent)                    -> forum_replies_count
#   forum_questions (questioner)                 -> forum_questions_asked
#   forum_answers (presenter)                    -> forum_answers_given
#   forum_reactions on student posts             -> forum_reactions_received
#   quiz_explanations (viewable statuses)        -> ai_explanations_viewed
#   quiz_explanations (feedback.helpful=true)    -> ai_explanations_helpful
#
# feature_version 1.1: dua perubahan sumber, keduanya karena soal interaktif
# dihapus dari produk.
#
#   1. `interactive_accuracy` (dulu dari student_answers) DIHAPUS. Seluruh
#      jawaban soal interaktif yang tercatat berjumlah nol, jadi fitur ini
#      selalu 0.0 - bukan pengukur, melainkan pemangkas bobot label.
#
#   2. easy/medium/hard_accuracy kini dari `practice_answers`, bukan
#      `student_answers`. Aturannya sengaja DIAMBIL PERSIS dari
#      student_practice_service._diagnose (jawaban TERAKHIR per soal bank,
#      tingkat terukur leave-one-out bila cukup bukti, selain itu deklarasi
#      guru, tanpa soal yang mengarang tingkat) supaya tidak ada dua
#      definisi "akurasi per tingkat" yang saling bertentangan.
# ============================================================
from src.models.material_section import MaterialSection
from src.models.material_progress import MaterialProgress
from src.models.material_student_state import MaterialStudentState
from src.models.practice_answer import PracticeAnswer
from src.models.learning_activity import LearningActivity
from src.models.submission import Submission
from src.services import learning_analytics_service as analytics
from src.ml import ml_config as cfg


def accessible_materials(student):
    return analytics.student_accessible_materials(student)


def _started_material_ids(student):
    ids = {r.material_id for r in MaterialStudentState.query.filter_by(student_id=student.id).all()}
    ids.update(p.material_id for p in MaterialProgress.query.filter_by(student_id=student.id).all())
    ids.update(a.material_id for a in LearningActivity.query.filter_by(student_id=student.id).all())
    return ids


def _aggregate_difficulty(student):
    """Akurasi siswa per tingkat kesulitan, seluruh materi, dari jawaban latihan.

    Sumbernya bukan lagi `student_answers` (soal interaktif) - tipe itu dihapus
    karena seluruh jawabannya berjumlah nol, sehingga fitur ini dulu selalu 0.0
    untuk semua siswa. Sekarang bersumber dari `practice_answers`.

    Aturannya DIAMBIL PERSIS dari student_practice_service._diagnose (jawaban
    TERAKHIR per soal bank, tingkat terukur leave-one-out bila cukup bukti,
    selain itu deklarasi guru) - bukan ditulis ulang - supaya tampilan siswa
    dan fitur ML tidak pernah berbeda pendapat tentang tingkat mana yang lemah.

    Cakupannya seluruh materi, persis seperti sebelumnya: tingkat kesulitan
    tidak terikat topik, jadi "siswa lemah di soal sulit" berlaku umum.

    BIAYA: leave-one-out menuntut seluruh jawaban SEMUA siswa atas soal-soal
    itu, sehingga fungsi ini memindai `practice_answers` per pemanggilan -
    persis seperti yang sudah dilakukan student_practice_service._diagnose di
    endpoint sesi latihan. Sebelumnya fungsi ini membaca `student_answers`
    yang isinya nol, jadi praktis gratis. Konsistensi metodologi dipilih di
    atas kecepatan: menulis ulang aturannya hanya untuk memangkas biaya akan
    menghasilkan dua definisi "akurasi per tingkat" yang bisa berbeda jawaban
    untuk siswa yang sama. Bila latensi dashboard terasa, yang perlu ditambah
    adalah cache hasil ukur per kumpulan soal, BUKAN versi aturan kedua.

    Mengembalikan {level: {'total': n, 'correct': n}}.
    """
    from src.services import student_practice_service as sps
    per_level, _basis, _notes, _counts = sps._diagnose(
        student, {})
    return per_level


def aggregate_student_features(student):
    """Build one aggregated ML feature row for the student.

    Returns None when data is insufficient (INSUFFICIENT_DATA) - we never
    fabricate a row that would silently produce a fake profile.
    """
    materials = accessible_materials(student)
    started_ids = _started_material_ids(student)
    started = [m for m in materials if m.id in started_ids]

    # ---- signal count -------------------------------------------
    quiz_rows = Submission.query.filter_by(
        student_id=student.id, status='submitted').all()
    # Jawaban latihan kini dihitung sebagai sinyal. Dulu slot ini diisi
    # jumlah jawaban soal interaktif yang selalu nol, jadi seorang siswa
    # dengan puluhan jawaban latihan bisa gugur sebagai sampel ML hanya
    # karena ia tidak pernah menyentuh tipe soal yang bahkan tidak pernah
    # ditawarkan kepadanya.
    practice_count = PracticeAnswer.query.filter_by(student_id=student.id).count()
    completed_sections = MaterialProgress.query.filter_by(student_id=student.id).count()
    signals = practice_count + len([s for s in quiz_rows if s.percentage is not None]) + completed_sections
    if signals < cfg.MIN_SIGNALS_FOR_STUDENT:
        return None

    # ---- progress -----------------------------------------------
    pcts = [analytics.progress_percentage(m.id, student.id) for m in started]
    material_completion_rate = (sum(pcts) / len(pcts)) / 100.0 if pcts else 0.0

    total_sections = 0
    completed_sections_total = 0
    for m in materials:
        sections = MaterialSection.query.filter_by(material_id=m.id).all()
        sid_set = {s.id for s in sections}
        total_sections += len(sid_set)
        completed_sections_total += len(analytics.completed_section_ids(student.id, m.id) & sid_set)
    section_completion_rate = (completed_sections_total / total_sections) if total_sections else 0.0

    # ---- difficulty accuracy -------------------------------------
    # Bersumber dari jawaban latihan; `started` tidak dipakai di sini karena
    # cakupannya seluruh materi (tingkat kesulitan tidak terikat topik).
    diff = _aggregate_difficulty(student)

    def diff_acc(level):
        b = diff.get(level)
        return (b['correct'] / b['total']) if b and b['total'] else 0.0

    # How many questions the student ACTUALLY answered per difficulty.
    # `*_accuracy` alone cannot express this: a level never attempted and
    # a level attempted-but-all-wrong both collapse to 0.0, which used to
    # hide the weakest level from recommendation.difficulty_fit.
    # These are METADATA, deliberately NOT model features - they are not
    # in cfg.FEATURES, so trained artifacts are unaffected.
    def diff_total(level):
        b = diff.get(level)
        return b['total'] if b else 0

    # ---- quiz ----------------------------------------------------
    scores = [r.percentage for r in quiz_rows if r.percentage is not None]
    quiz_average = (sum(scores) / len(scores)) / 100.0 if scores else 0.0
    quiz_best_score = (max(scores) / 100.0) if scores else 0.0
    quiz_attempts = len(scores)

    # ---- learning time -------------------------------------------
    learning_minutes = analytics.student_total_seconds(student.id) / 60.0

    # ---- overall correct rate ------------------------------------
    # Kuis saja sekarang. Jawaban soal interaktif tidak lagi menjadi bagian
    # dari kanal ini (tipe itu dihapus), dan angkanya memang selalu nol -
    # jadi ini bukan perubahan nilai, hanya penghapusan sumber mati.
    quiz_correct = sum(r.correct_count or 0 for r in quiz_rows)
    quiz_wrong = sum(r.wrong_count or 0 for r in quiz_rows)
    answered_total = quiz_correct + quiz_wrong
    answered_correct = quiz_correct
    correct_rate = (answered_correct / answered_total) if answered_total else 0.0

    # ---- forum activity ------------------------------------------
    from src.models.forum import ForumPost, ForumQuestion, ForumAnswer, ForumReaction
    forum_posts = ForumPost.query.filter_by(
        author_id=student.id, deleted_at=None).filter(
        ForumPost.parent_id.is_(None)).count()
    forum_replies = ForumPost.query.filter_by(
        author_id=student.id, deleted_at=None).filter(
        ForumPost.parent_id.isnot(None)).count()
    forum_questions = ForumQuestion.query.filter_by(questioner_id=student.id).count()
    forum_answers = ForumAnswer.query.filter_by(presenter_id=student.id).count()

    # reactions received on student's posts
    student_post_ids = [p.id for p in ForumPost.query.filter_by(
        author_id=student.id, deleted_at=None).with_entities(ForumPost.id).all()]
    forum_reactions = ForumReaction.query.filter(
        ForumReaction.post_id.in_(student_post_ids)).count() if student_post_ids else 0

    # ---- AI explanation interactions ------------------------------
    from src.models.quiz_explanation import QuizExplanation
    STUDENT_VIEWABLE = ('APPROVED', 'TEACHER_APPROVED')
    explanation_rows = QuizExplanation.query.filter_by(student_id=student.id).filter(
        QuizExplanation.status.in_(STUDENT_VIEWABLE)).all()
    ai_explanations_viewed = len(explanation_rows)
    ai_explanations_helpful = sum(
        1 for e in explanation_rows
        if isinstance(e.feedback_summary, dict) and e.feedback_summary.get('helpful')
    )

    return {
        cfg.ID_COLUMN: student.id,
        'material_completion_rate': round(material_completion_rate, 4),
        'section_completion_rate': round(section_completion_rate, 4),
        'quiz_average': round(quiz_average, 4),
        'quiz_best_score': round(quiz_best_score, 4),
        'easy_accuracy': round(diff_acc('easy'), 4),
        'medium_accuracy': round(diff_acc('medium'), 4),
        'hard_accuracy': round(diff_acc('hard'), 4),
        'easy_attempted': diff_total('easy'),
        'medium_attempted': diff_total('medium'),
        'hard_attempted': diff_total('hard'),
        'learning_minutes': round(learning_minutes, 2),
        'quiz_attempts': quiz_attempts,
        'correct_rate': round(correct_rate, 4),
        'forum_posts_count': forum_posts,
        'forum_replies_count': forum_replies,
        'forum_questions_asked': forum_questions,
        'forum_answers_given': forum_answers,
        'forum_reactions_received': forum_reactions,
        'ai_explanations_viewed': ai_explanations_viewed,
        'ai_explanations_helpful': ai_explanations_helpful,
    }


def build_dataset(students):
    """Returns [feature rows]; only students with sufficient data included."""
    rows = []
    for s in students:
        row = aggregate_student_features(s)
        if row is not None:
            rows.append(row)
    return rows


def feature_matrix(rows):
    """Return X (list of lists aligned to cfg.FEATURES) and identifiers."""
    ids = [r[cfg.ID_COLUMN] for r in rows]
    X = [[r.get(f, 0.0) for f in cfg.FEATURES] for r in rows]
    return ids, X