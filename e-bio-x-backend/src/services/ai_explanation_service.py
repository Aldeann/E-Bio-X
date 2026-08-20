"""AI Quiz Explanation Engine (Prompt 12).

Provider-abstraction service. The answer key is ALWAYS authoritative and comes
from the teacher / question bank; AI (or the deterministic fallback) only
produces EXPLANATION text, never answers.

- If AI_API_KEY is configured: calls an OpenAI-compatible chat-completions API.
- Otherwise (or on AI failure): a safe rule-based generator grounded on the
  question, the answer key, and available material context. It never invents
  scientific facts beyond the provided context.
"""
import json
import re
import os
from datetime import datetime

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

PROMPT_VERSION = 'p12-1'
REQUIRED_FIELDS = [
    'summary',
    'correct_answer_explanation',
    'student_answer_analysis',
    'option_explanations',
    'key_concept',
    'misconception',
    'recommended_material',
]

SYSTEM_PROMPT = (
    "You are an educational biology explanation assistant for high school "
    "students (SMA, Fase E).\n"
    "Your task is to explain a quiz question based only on the provided "
    "question, answer key, and relevant learning material.\n"
    "The answer key is authoritative and must not be changed.\n"
    "Do not invent facts unsupported by the provided context.\n"
    "Explain why the correct answer is correct.\n"
    "Explain why each incorrect option is incorrect.\n"
    "If the student's answer is incorrect, explain the likely conceptual "
    "error carefully without making unsupported diagnoses.\n"
    "Use clear Indonesian suitable for high school students.\n"
    "Return ONLY valid JSON matching the required schema."
)

SCHEMA_HINT = (
    'Required JSON schema (no extra top-level keys):\n'
    '{\n'
    '  "summary": "short overall explanation (2-4 sentences)",\n'
    '  "correct_answer_explanation": "why the correct answer is correct",\n'
    '  "student_answer_analysis": "generic note about a student answer; '
    'specific per-student analysis is handled separately",\n'
    '  "option_explanations": [{"option": "A", "is_correct": true, '
    '"explanation": "short"}],\n'
    '  "key_concept": "core concept (1-2 sentences)",\n'
    '  "misconception": "possible misconception, or empty string if none",\n'
    '  "recommended_material": "material title to restudy or empty string"\n'
    '}\n'
    'option_explanations must contain exactly one entry per option letter '
    '(A, B, C, ...). Exactly one entry must have is_correct=true and it must '
    'match the provided correct answer letter.'
)


def option_letters(option_count):
    return [chr(ord('A') + i) for i in range(option_count)]


def correct_letter(options):
    """options = list of (letter, is_correct) or (letter, text, is_correct).
    Returns the correct letter."""
    for item in options:
        is_correct = item[1] if len(item) == 2 else item[2]
        if is_correct:
            return item[0]
    return None


def _strip_html(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', str(text))
    return re.sub(r'\s+', ' ', text).strip()


def build_material_context(material, question_text, max_chars=6000):
    """Retrieve only the relevant material parts (keyword-scored sections)."""
    if not material:
        return None
    ctx = []
    ctx.append(f"Judul Materi: {material.title}")
    if material.topic:
        ctx.append(f"Topik: {material.topic}")
    if material.learning_objectives:
        ctx.append(f"Tujuan Pembelajaran:\n{_strip_html(material.learning_objectives)}")

    keywords = list(dict.fromkeys(w for w in re.findall(r'[a-zA-Z]{3,}', (question_text or '').lower())))

    scored = []
    for sec in material.sections or []:
        sec_text = sec.title or ''
        for content in (sec.contents or []):
            if content.type in ('text', 'heading', 'box', 'link'):
                data = content.data or {}
                sec_text += ' ' + _strip_html(data.get('html') or data.get('text') or data.get('url') or '')
            elif content.type in ('video', 'pdf'):
                data = content.data or {}
                sec_text += ' ' + _strip_html(data.get('title') or data.get('caption') or data.get('name') or '')
        score = sum(1 for kw in keywords if kw in sec_text.lower())
        scored.append((score, sec.title or '', sec_text))

    scored.sort(key=lambda x: (-x[0], 0))
    picked = [s for s in scored if s[0] > 0]
    if not picked and scored:
        picked = scored[:1]  # fallback to first section so there is SOME context
    for _, title, sec_text in picked[:3]:
        snippet = sec_text[:1400]
        if title:
            ctx.append(f"Bagian Materi - {title}:\n{snippet}")
    joined = "\n\n".join(ctx)
    return joined[:max_chars]


class AIExplanationService:
    def __init__(self):
        self.api_key = os.getenv('AI_API_KEY') or ''
        self.base_url = (os.getenv('AI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
        self.model = os.getenv('AI_MODEL') or 'gpt-4o-mini'

    def available(self):
        return bool(self.api_key) and requests is not None

    # -------------------------------------------------------------
    # Public entry
    # -------------------------------------------------------------
    def generate(self, payload):
        """payload: dict with question/options/correct_answer/student_answer/
        question_type/difficulty/topic/related_material/material_context.
        Returns (result_dict, generated_by, model_name)."""
        if self.available():
            try:
                data = self._call_provider(payload)
                if data:
                    return data, 'ai', self.model
            except Exception:
                pass  # fall back to rule-based; errors are logged by caller
        return self._rule_based(payload), 'rule_based', None

    # -------------------------------------------------------------
    # Provider (OpenAI-compatible chat completions)
    # -------------------------------------------------------------
    def _call_provider(self, payload):
        user_text = self._build_user_prompt(payload)
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        body = {
            'model': self.model,
            'temperature': 0.3,
            'messages': [
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': user_text},
            ],
        }
        url = f'{self.base_url}/chat/completions'
        for attempt in range(2):
            resp = requests.post(url, headers=headers, json=body, timeout=90)
            resp.raise_for_status()
            content = resp.json()['choices'][0]['message']['content']
            data = self._parse_json(content)
            if data is not None:
                return data
        return None

    @staticmethod
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

    @staticmethod
    def _build_user_prompt(payload):
        lines = []
        lines.append(f"Question text:\n{payload.get('question_text')}")
        lines.append(f"Question type: {payload.get('question_type')}")
        lines.append(f"Difficulty: {payload.get('difficulty')}")
        if payload.get('topic'):
            lines.append(f"Topic: {payload['topic']}")
        lines.append("Options (letter: text):")
        for opt in payload.get('options', []):
            letter, text = opt[0], opt[1]
            lines.append(f"{letter}: {text}")
        lines.append(f"Correct answer (authoritative, from answer key): {payload.get('correct_answer')}")
        if payload.get('student_answer') is not None:
            lines.append(f"Student answer: {payload['student_answer']}")
        ctx = payload.get('material_context')
        if ctx:
            lines.append(f"Relevant learning material (use this as the primary context; do not invent content outside it):\n{ctx}")
        else:
            lines.append("Relevant learning material: (none provided). Do not fabricate scientific facts.")
        lines.append(SCHEMA_HINT)
        return "\n\n".join(lines)

    # -------------------------------------------------------------
    # Safe rule-based fallback (honest, grounded on the answer key)
    # -------------------------------------------------------------
    def _rule_based(self, payload):
        options = payload.get('options') or []  # list of (letter, text, is_correct)
        letters = [o[0] for o in options]
        correct = payload.get('correct_answer')
        correct_text = next((o[1] for o in options if o[0] == correct), '')
        student_answer = payload.get('student_answer')
        topic = payload.get('topic')
        material_title = payload.get('material_title') or (
            payload.get('material_context') or ''
        ).split('\n')[0].replace('Judul Materi: ', '')

        option_explanations = []
        for letter, text, is_correct in options:
            if is_correct:
                explanation = f"Benar. Pilihan {letter} sesuai dengan kunci jawaban yang ditetapkan."
            else:
                explanation = f"Pilihan {letter} bukan kunci jawaban untuk soal ini."
            option_explanations.append({
                'option': letter,
                'is_correct': bool(is_correct),
                'explanation': explanation,
            })

        summary = f"Kunci jawaban soal ini adalah {correct}."
        if student_answer and student_answer != correct:
            summary += f" Jawaban Anda ({student_answer}) kurang tepat; pelajari kembali konsep yang ditanyakan."
        elif student_answer:
            summary += " Jawaban Anda benar."

        correct_expl = f"Kunci jawaban yang benar adalah {correct}."
        if correct_text:
            correct_expl += f" Pilihan ini menyatakan: \"{correct_text}\"."
        if material_title:
            correct_expl += f" Pembahasan lebih lanjut dapat dipelajari pada materi \"{material_title}\"."

        if student_answer and student_answer != correct:
            sel = next((o for o in options if o[0] == student_answer), None)
            analysis = f"Jawaban Anda ({student_answer}) kurang tepat."
            if sel:
                analysis += f" Pilihan yang Anda pilih berbunyi \"{sel[1]}\", dan bukan kunci jawaban."
            analysis += f" Kunci jawaban yang benar adalah {correct}."
        else:
            analysis = ""

        key_concept = topic or material_title or "Konsep utama sesuai kunci jawaban soal."
        if material_title:
            key_concept = f"Konsep utama: {topic or 'topik soal'} — pelajari pada materi \"{material_title}\"."

        misconception = ""
        if student_answer and student_answer != correct:
            misconception = (
                "Kesalahan ini dapat berkaitan dengan kurang tepatnya pemahaman "
                "konsep pada topik yang ditanyakan. Gunakan pembahasan dan materi "
                "terkait untuk mengulang konsepnya."
            )

        return {
            'summary': summary,
            'correct_answer_explanation': correct_expl,
            'student_answer_analysis': analysis,
            'option_explanations': option_explanations,
            'key_concept': key_concept,
            'misconception': misconception,
            'recommended_material': material_title or '',
        }


# -------------------------------------------------------------
# Output validation (BAGIAN AL/AM)
# -------------------------------------------------------------
def validate_explanation(data, options, correct_letter):
    """options = list of (letter, text, is_correct). Returns (ok, error)."""
    if not isinstance(data, dict):
        return False, 'Output AI bukan objek JSON'
    missing = [f for f in REQUIRED_FIELDS if not data.get(f) and f not in ('misconception', 'student_answer_analysis', 'recommended_material')]
    if missing:
        return False, f'Field wajib tidak ada: {", ".join(missing)}'

    oes = data.get('option_explanations')
    if not isinstance(oes, list) or len(oes) != len(options):
        return False, 'Jumlah option_explanations tidak sesuai jumlah pilihan'

    db_correct = correct_letter
    ai_correct = None
    seen = set()
    for oe in oes:
        if not isinstance(oe, dict) or 'option' not in oe:
            return False, 'Format option_explanations tidak valid'
        letter = str(oe.get('option')).upper()
        if letter in seen:
            return False, 'Ada pilihan ganda pada option_explanations'
        seen.add(letter)
        if letter not in [o[0] for o in options]:
            return False, f'Pilihan {letter} tidak dikenali'
        if oe.get('is_correct'):
            if ai_correct is not None:
                return False, 'Terlalu banyak pilihan ditandai benar'
            ai_correct = letter

    if ai_correct is None or ai_correct != db_correct:
        return False, 'Jawaban benar AI tidak cocok dengan kunci jawaban database'

    for oe in oes:
        expected = (str(oe.get('option')).upper() == db_correct)
        if bool(oe.get('is_correct')) != expected:
            return False, 'Penanda is_correct tidak konsisten dengan kunci jawaban'

    return True, None


def make_stale_status(existing, current_version):
    if existing.material_version and current_version and existing.material_version != current_version:
        if existing.status in ('APPROVED', 'TEACHER_APPROVED'):
            return True
    return False


def stamp_time(obj, attr='updated_at'):
    setattr(obj, attr, datetime.utcnow())
