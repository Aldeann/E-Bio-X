"""AI Quiz Explanation - cross-teacher knowledge base (brain).

Scope rule (as chosen): AI explanations may use REALM context from published
materials owned by OTHER teachers but ONLY within the same course. Files
uploaded as PDF/DOCX/TXT are text-extracted once, cached, and reused.
Generated/approved knowledge is aggregated per-topic into `topic_knowledge`
so later questions on the same topic benefit from previous approved answers.
"""
import os
import re
from datetime import datetime

from src.config.database import db
from src.models.material import Material, material_courses
from src.models.material_file import MaterialFile
from src.models.material_file_text import MaterialFileText
from src.models.topic_knowledge import TopicKnowledge
from src.models.quiz_explanation import QuizExplanation
from src.utils.text_extraction import extract_file_text

MAX_FILES_CONTEXT = 4000
MAX_SECTIONS = 3000


def _upload_folder():
    try:
        from flask import current_app
        folder = current_app.config.get('UPLOAD_FOLDER')
        if folder:
            return folder
    except Exception:
        pass
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')


def file_text_cached(material_file):
    """Extract text from an uploaded MaterialFile once, cache in DB."""
    if not material_file:
        return ''
    try:
        row = MaterialFileText.query.filter_by(material_file_id=material_file.id).first()
        if row and row.content:
            return row.content
        if not row:
            row = MaterialFileText(
                material_file_id=material_file.id,
                material_id=material_file.material_id,
            )
            db.session.add(row)
        path = os.path.join(_upload_folder(), material_file.file_name)
        content = extract_file_text(path, material_file.file_type)
        row.content = content
        row.chars = len(content) if content else 0
        row.updated_at = datetime.utcnow()
        db.session.commit()
        return content or ''
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return ''


def _strip_html(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', str(text))
    return re.sub(r'\s+', ' ', text).strip()


def _content_parts(content):
    """Read the actual data shape written by the frontend block form."""
    data = content.data or {}
    ctype = content.type
    if ctype in ('text', 'heading', 'box', 'link'):
        return [_strip_html(data.get('content') or data.get('label') or data.get('variant') or '')]
    if ctype == 'pdf':
        parts = [_strip_html(data.get('title') or '')]
        # pdf url references an uploaded file; try to pull its extracted text
        url = data.get('url') or ''
        if url:
            fname = os.path.basename(url.split('?')[0])
            mf = MaterialFile.query.filter_by(material_id=content.section.material_id, file_name=fname).first() \
                if content.section and content.section.material_id else None
            if not mf:
                mf = MaterialFile.query.filter(MaterialFile.file_url.endswith(fname)).first()
            if mf:
                parts.append(file_text_cached(mf))
        return [p for p in parts if p]
    if ctype == 'video':
        return [_strip_html(data.get('title') or '')]
    if ctype == 'image':
        return [_strip_html(data.get('caption') or '')]
    return []


def material_context_parts(material, question_text):
    """Keyword-scored sections + uploaded file text of one material."""
    keywords = list(dict.fromkeys(w for w in re.findall(r'[a-zA-Z]{3,}', (question_text or '').lower())))
    prompts = [f"Judul Materi: {material.title}"]
    if material.topic:
        prompts.append(f"Topik: {material.topic}")
    if material.subject:
        prompts.append(f"Mapel: {material.subject}")
    if material.learning_objectives:
        prompts.append(f"Tujuan Pembelajaran: {_strip_html(material.learning_objectives)}")

    scored = []
    for sec in material.sections or []:
        sec_text = sec.title or ''
        for content in (sec.contents or []):
            sec_text += ' ' + ' '.join(_content_parts(content))
        score = sum(1 for kw in keywords if kw in sec_text.lower())
        scored.append((score, sec.title or '', sec_text))

    scored.sort(key=lambda x: (-x[0], 0))
    picked = [s for s in scored if s[0] > 0]
    if not picked and scored:
        picked = scored[:1]
    budget = MAX_SECTIONS
    for _, title, sec_text in picked[:3]:
        snippet = sec_text[:1400]
        if title:
            prompts.append(f"Bagian Materi - {title}:\n{snippet}")
            budget -= len(snippet)
        elif snippet:
            prompts.append(snippet)
            budget -= len(snippet)

    # uploaded file text (PDF/DOCX/TXT) of this material
    file_budget = min(MAX_FILES_CONTEXT, budget)
    for mf in (material.files or []):
        if file_budget <= 0:
            break
        text = file_text_cached(mf)
        if not text:
            continue
        snippet = text[:max(600, file_budget)]
        prompts.append(f"Isi file \"{mf.original_name}\":\n{snippet}")
        file_budget -= len(snippet)

    return prompts


def course_published_materials(course_id, teacher_id=None):
    """Published materials in the same course (may belong to other teachers)."""
    if not course_id:
        return []
    q = Material.query.filter(Material.status == 'published')
    q = q.filter((Material.course_id == course_id) | (Material.course_links.any(material_courses.c.course_id == course_id)))
    return q.all()


def build_course_context(question_text, course_id, own_material_id=None, teacher_id=None, max_chars=5000):
    """Context realm from published materials of the SAME course (other teachers)."""
    if not course_id:
        return None
    curated = []
    for mat in course_published_materials(course_id, teacher_id):
        if mat.id == own_material_id:
            continue  # own material already injected separately
        if mat.teacher_id == teacher_id:
            continue  # still mine; avoid duplication
        parts = material_context_parts(mat, question_text)
        for p in parts:
            curated.append(p)
        if len('\n'.join(curated)) > max_chars * 2:
            break
    if not curated:
        return None
    joined = '\n'.join(curated)
    return joined[:max_chars]


def topic_for(question_text, material=None, bank=None):
    if material and material.topic:
        return str(material.topic)[:150]
    if bank and bank.topic:
        return str(bank.topic)[:150]
    words = re.findall(r'[a-zA-Z]{3,}', question_text or '')
    if len(words) <= 3:
        return ' '.join(dict.fromkeys(['umum'] + [w.lower() for w in words]))[:150]
    return 'umum'


def retrieve_topic_knowledge(topic, course_id=None):
    """Best aggregated knowledge for a topic (course-scoped if possible)."""
    if not topic or topic == 'umum':
        return None
    rows = TopicKnowledge.query.filter(TopicKnowledge.topic == topic)
    if course_id:
        rows = rows.filter(TopicKnowledge.course_id == course_id)
    row = rows.order_by(TopicKnowledge.approved_count.desc(), TopicKnowledge.usage_count.desc()).first()
    if not row and course_id:
        row = TopicKnowledge.query.filter_by(topic=topic, course_id=None).order_by(
            TopicKnowledge.approved_count.desc()).first()
    return row


def build_knowledge_context(topic, course_id, max_chars=2500):
    row = retrieve_topic_knowledge(topic, course_id)
    if not row:
        return None
    parts = [f"Pengetahuan terakumulasi tentang topik \"{row.topic}\":",
             f"Konsep kunci: {row.key_concept or ''}"]
    if row.correct_answer_explanation:
        parts.append(f"Penjelasan terakumulasi: {row.correct_answer_explanation}")
    if row.misconception:
        parts.append(f"Kesalahan umum teramati: {row.misconception}")
    if row.recommended_material:
        parts.append(f"Rujukan materi: {row.recommended_material}")
    joined = '\n'.join(parts)
    return joined[:max_chars]


def _val(obj, key):
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None) or None


def store_topic_knowledge(question_topic, course_id, material_id, explanation, approved=False):
    """Aggregate an explanation's knowledge into topic_knowledge."""
    if not question_topic or question_topic == 'umum':
        return None
    try:
        row = TopicKnowledge.query.filter_by(
            topic=question_topic,
            course_id=course_id if course_id else None,
        ).first()
        if not row:
            row = TopicKnowledge(
                topic=question_topic,
                course_id=course_id if course_id else None,
            )
            db.session.add(row)
            row.source_count = 1
        else:
            row.source_count = (row.source_count or 1) + 1
        if approved:
            row.approved_count = (row.approved_count or 0) + 1
        # keep most recent / most authoritative content
        row.key_concept = _val(explanation, 'key_concept') or row.key_concept
        row.correct_answer_explanation = _val(explanation, 'correct_answer_explanation') or row.correct_answer_explanation
        row.misconception = _val(explanation, 'misconception') or row.misconception
        row.recommended_material = _val(explanation, 'recommended_material') or row.recommended_material
        row.source_material_id = material_id or row.source_material_id
        row.updated_at = datetime.utcnow()
        db.session.commit()
        return row
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def find_similar_approved(question_text, course_id, exclude_ids=None):
    """Reuse approved explanation from another question in the same course."""
    if not course_id or not question_text:
        return None
    words = set(w.lower() for w in re.findall(r'[a-zA-Z]{3,}', question_text))
    if len(words) < 2:
        return None
    try:
        exps = QuizExplanation.query.filter(
            QuizExplanation.status.in_(('APPROVED', 'TEACHER_APPROVED')),
            QuizExplanation.student_id.is_(None),
        ).all()
    except Exception:
        return None
    best, best_score, inter = None, 1, 0
    for e in exps:
        if exclude_ids and e.id in exclude_ids:
            continue
        qtext = e.question.text if e.question else None
        if not qtext:
            continue
        quiz = e.question.quiz if e.question else None
        ec = quiz.course_id if quiz else None
        if ec and ec != course_id:
            continue
        owords = set(w.lower() for w in re.findall(r'[a-zA-Z]{3,}', qtext))
        inter = len(words & owords)
        if inter >= best_score:
            best_score, best = inter, e
    if inter and inter >= 2 and best:
        return best
    return None


def approved_reuse_context(candidate, max_chars=1800):
    if not candidate:
        return None
    return (
        f"Terdapat pembahasan yang sudah disetujui untuk soal serupa. "
        f"Gunakan sebagai panduan keahlian (jaga struktur penjelasan serupa):\n"
        f"Konsep kunci: {candidate.key_concept or ''}\n"
        f"Penjelasan: {candidate.correct_answer_explanation or ''}"
    )[:max_chars]