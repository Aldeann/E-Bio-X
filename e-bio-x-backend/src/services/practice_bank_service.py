"""Practice-question drafts for material sections (Fase 3).

A draft is a practice question the AI proposed for ONE material section that
the teacher picked. Nothing in here decides what a student sees: every draft is
stored as ``status='DRAFT'`` and a teacher has to approve it first.

There is deliberately no rule-based fallback here. The explanation engine has one
because it can ground itself on an authoritative answer key; a question that
does not exist yet has no key to ground on. When the provider is missing or
fails, the caller gets an honest error instead of invented questions.

``section`` and ``topic`` are copied from the section record by the controller,
never read from the model's output. That keeps the conservative Fase 1 mapping
rule intact: a draft can only belong to the section the teacher chose.
"""
import json
import os
import re
import time

from sqlalchemy import func

from src.config.database import db
from src.models.material import Material
from src.models.question_bank import QuestionBank

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

PROMPT_VERSION = 'sec-draft-v1'
DEFAULT_COUNT = 3
MAX_COUNT = 10
VALID_DIFFICULTIES = ('easy', 'medium', 'hard')

DIFFICULTY_LABEL = {
    'easy': 'Mudah',
    'medium': 'Sedang',
    'hard': 'Sulit',
}

# Questions about the section itself ("apa isi bagian ini?") are not practice.
# They show up when a section carries little real text, so they are dropped here
# and counted for the caller instead of being stored as review fodder.
_META_QUESTION_RE = re.compile(
    r'(apa (materi|isi|topik|bagian)|bagian ini|materi ini|yang disajikan|'
    r'menyajikan|mengenai (materi|bagian)|pada (materi|bagian) (ini|tersebut)|'
    r'dari teks|menurut teks)',
    re.I,
)

SYSTEM_PROMPT = (
    "You are an assessment author for Indonesian senior high school biology "
    "(SMA).\n"
    "You write practice questions for exactly ONE section of a learning "
    "material.\n"
    "Rules you must follow:\n"
    "- Use only facts stated in the provided section text. Do not add outside "
    "knowledge, and do not guess numbers or names that are not in the text.\n"
    "- Every question must be answerable from the section text alone.\n"
    "- Ask about the biology content itself. Never ask what the section or the "
    "material is about, never refer to 'the text', 'the section', or what is "
    "'presented'. Such questions are useless for practice and are discarded.\n"
    "- Exactly one option is correct.\n"
    "- Every wrong option must express the same realistic student "
    "misconception, not random nonsense.\n"
    "- Write in clear Indonesian.\n"
    "- Reply with a JSON object only. No markdown, no commentary.\n"
)

SCHEMA_HINT = (
    'Return exactly this JSON shape:\n'
    '{"questions": [\n'
    '  {\n'
    '    "question_text": "pertanyaan",\n'
    '    "options": [\n'
    '      {"option_text": "opsi", "is_correct": true, "feedback": "alasan '
    'singkat"},\n'
    '      {"option_text": "pengecoh", "is_correct": false, "feedback": '
    '"kesalahpahaman yang dituju pengecoh ini"}\n'
    '    ],\n'
    '    "explanation": "alasan mengapa jawaban benar itu benar",\n'
    '    "misconception": "kesalahpahaman utama yang diuji"\n'
    '  }\n'
    ']}\n'
    'Use 4 options per question. "feedback" is one short sentence per option.'
)


class DraftUnavailable(RuntimeError):
    """No AI provider configured, so no draft can be produced."""


class DraftFailed(RuntimeError):
    """The provider was reachable but did not return usable questions."""


# ---------------------------------------------------------------- provider

def ai_available():
    return bool(os.getenv('AI_API_KEY')) and requests is not None


def model_name():
    return os.getenv('AI_MODEL') or 'gpt-4o-mini'


def _base_url():
    return (os.getenv('AI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')


def _strip_html(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', str(text))
    return re.sub(r'\s+', ' ', text).strip()


def _parse_json(content):
    content = (content or '').strip()
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r'\{.*\}', content, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


# ---------------------------------------------------------------- prompting

def _content_text(content):
    """Readable text of one material content, or '' when it carries none.

    The key is `content` for the authoring payloads (text/heading/box), while
    the seeded placeholder rows use `text`. Both are checked so a section never
    looks empty while it actually holds material.
    """
    data = content.data or {}
    if not isinstance(data, dict):
        return ''
    for key in ('content', 'html', 'text', 'title', 'caption', 'name', 'question'):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return _strip_html(value)
    return ''


def section_body(section):
    """Plain text of the section's own contents (empty string when there is none)."""
    body = []
    for content in (section.contents or []):
        text = _content_text(content)
        if not text and content.type in ('interactive', 'quiz', 'question'):
            data = content.data or {}
            questions = data.get('questions') if isinstance(data, dict) else None
            if isinstance(questions, list):
                text = _strip_html(' | '.join(
                    q.get('question', '') for q in questions
                    if isinstance(q, dict) and q.get('question')
                ))
        if text:
            body.append(text)
    return "\n".join(body)


def section_context(section, material, max_chars=2500):
    """Text handed to the AI: the section the teacher chose, nothing else.

    Keyword scoring is deliberately absent here. In the explanation engine the
    section is picked by relevance; here the teacher already picked it, so
    including a neighbouring section would only invite off-topic questions.
    """
    parts = []
    if material:
        parts.append(f"Judul materi: {material.title}")
        if material.class_level:
            parts.append(f"Kelas: {material.class_level}")
        if material.learning_objectives:
            parts.append(
                "Tujuan pembelajaran materi:\n" + _strip_html(material.learning_objectives)
            )
    parts.append(f"Bagian materi: {section.title or '(tanpa judul)'}")

    body = section_body(section)
    if body:
        parts.append("Isi bagian:\n" + body)
    else:
        parts.append("Isi bagian: (bagian ini belum memiliki teks)")

    joined = "\n\n".join(parts)
    return joined[:max_chars]


def build_prompt(section, material, count, difficulty):
    label = DIFFICULTY_LABEL.get(difficulty, DIFFICULTY_LABEL['medium'])
    lines = [
        f"Tulis {count} soal latihan pilihan ganda.",
        f"Tingkat kesulitan: {label}.",
        section_context(section, material),
        SCHEMA_HINT,
    ]
    return "\n\n".join(lines)


def generate_drafts(section, material, count=DEFAULT_COUNT, difficulty='medium'):
    """Return (drafts, dropped) or raise DraftUnavailable/DraftFailed.

    ``drafts`` is a list of raw dicts, ``dropped`` counts answers the model
    produced but that are not usable practice questions. Whether a draft is
    storable is decided by the caller with the same validator used for
    teacher-written questions, so a malformed AI answer is dropped instead of
    saved.
    """
    if not ai_available():
        raise DraftUnavailable(
            'AI belum dikonfigurasi. Set AI_API_KEY (dan AI_BASE_URL/AI_MODEL) '
            'untuk membuat draf, atau tulis soal sendiri dan tautkan ke bagian ini.'
        )

    count = max(1, min(int(count or DEFAULT_COUNT), MAX_COUNT))
    if difficulty not in VALID_DIFFICULTIES:
        difficulty = 'medium'

    headers = {
        'Authorization': f'Bearer {os.getenv("AI_API_KEY")}',
        'Content-Type': 'application/json',
    }
    body = {
        'model': model_name(),
        'temperature': 0.4,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': build_prompt(section, material, count, difficulty)},
        ],
    }
    url = f'{_base_url()}/chat/completions'

    last_error = None
    dropped_total = 0
    # Providers fail transiently (capacity, rate limit). Three tries with a
    # short backoff costs a few seconds and saves the teacher a re-click.
    for attempt, pause in enumerate((2, 4, 0)):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=90)
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content']
        except Exception as exc:
            last_error = _describe(exc)
            if pause:
                time.sleep(pause)
            continue
        data = _parse_json(content)
        items, dropped = _draft_items(data)
        dropped_total += dropped
        if items:
            return items[:count], dropped_total
        last_error = 'format jawaban tidak valid'
        if pause:
            time.sleep(1)
    raise DraftFailed(f'Layanan AI tidak bisa dipakai ({last_error}).')


def _describe(exc):
    """Short, honest description of a provider failure for the teacher."""
    response = getattr(exc, 'response', None)
    if response is None:
        return type(exc).__name__
    code = response.status_code
    if code in (429, 500, 502, 503, 504):
        return f'HTTP {code}, penyedia AI sedang sibuk - coba lagi beberapa saat lagi'
    return f'HTTP {code} dari penyedia AI'


def _draft_items(data):
    """Return (items, dropped). ``dropped`` counts unusable answers."""
    if isinstance(data, dict):
        data = data.get('questions')
    if not isinstance(data, list):
        return [], 0
    items = []
    dropped = 0
    for raw in data:
        if not isinstance(raw, dict):
            dropped += 1
            continue
        text = _strip_html(raw.get('question_text') or raw.get('question') or '')
        options = []
        for opt in (raw.get('options') or []):
            if not isinstance(opt, dict):
                continue
            opt_text = _strip_html(opt.get('option_text') or opt.get('text') or '')
            if not opt_text:
                continue
            options.append({
                'option_text': opt_text,
                'is_correct': bool(opt.get('is_correct')),
                'feedback': _strip_html(opt.get('feedback') or opt.get('explanation') or '') or None,
            })
        if not text or not options:
            dropped += 1
            continue
        if _META_QUESTION_RE.search(text):
            dropped += 1
            continue
        items.append({
            'question_text': text,
            'options': options,
            'explanation': _strip_html(raw.get('explanation') or '') or None,
            'misconception': _strip_html(raw.get('misconception') or '') or None,
        })
    return items, dropped


# ---------------------------------------------------------------- coverage

def section_rows(user, material_id=None):
    """Every material section the teacher owns, with raw draft counts.

    The counts are exactly what is stored (approved / draft / rejected). No
    score or ratio is derived here: a section with no questions is reported as
    zero questions, not as a low or high value.
    """
    if user.role == 'admin':
        materials = Material.query.all()
        owner_id = None
    else:
        materials = Material.query.filter_by(teacher_id=user.id).all()
        owner_id = user.id

    if material_id is not None:
        materials = [m for m in materials if m.id == int(material_id)]

    counts = {}
    query = db.session.query(
        QuestionBank.section_id.label('section_id'),
        QuestionBank.status.label('status'),
        func.count(QuestionBank.id).label('n'),
    ).filter(QuestionBank.section_id.isnot(None))
    if owner_id is not None:
        query = query.filter(QuestionBank.teacher_id == owner_id)
    for section_id, status, n in query.group_by(QuestionBank.section_id, QuestionBank.status).all():
        counts.setdefault(section_id, {})[status] = n

    rows = []
    for material in materials:
        for section in (material.sections or []):
            bucket = counts.get(section.id, {})
            rows.append({
                'section_id': section.id,
                'title': section.title,
                'position': section.position,
                'material_id': material.id,
                'material_title': material.title,
                'approved_count': bucket.get('APPROVED', 0),
                'draft_count': bucket.get('DRAFT', 0),
                'rejected_count': bucket.get('REJECTED', 0),
            })
    rows.sort(key=lambda r: (r['material_title'].lower(), r['position'], r['section_id']))
    return rows


def practice_ready(section_id):
    """True when a section has at least one teacher-approved practice question."""
    return QuestionBank.query.filter_by(
        section_id=section_id,
        status='APPROVED',
    ).count() > 0