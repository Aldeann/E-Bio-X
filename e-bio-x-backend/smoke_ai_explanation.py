import json
import sys

from src import app
from src.config.database import db

app.config['TESTING'] = True
client = app.test_client()

results = []


def call(name, method, url, token=None, body=None, expect=None):
    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    kwargs = {'headers': headers}
    if body is not None:
        kwargs['json'] = body
    rv = client.open(url, method=method, **kwargs)
    try:
        data = rv.get_json()
    except Exception:
        data = None
    ok = (expect is None) or (rv.status_code == expect)
    results.append((name, ok, rv.status_code, data))
    return rv.status_code, data


def login(email, password):
    _, d = call('login', 'POST', '/api/login', body={'email': email, 'password': password}, expect=200)
    return d['access_token']


QUESTION_ID = None
QUESTION_ID2 = None
ATTEMPT_ID = None
QUIZ_ID = None


def _raw(method, url, token=None, body=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    rv = client.open(url, method=method, headers=headers, json=body)
    return rv.status_code, rv.get_json(silent=True)


def build_fixture(teacher_token, student_token):
    """Buat kuis sementara (materi demo milik guru) + 1 attempt murid.

    Semua test explanation dijalankan terhadap fixture ini sehingga
    kuis/materi milik pengguna tidak pernah tersentuh.
    """
    global QUESTION_ID, QUESTION_ID2, ATTEMPT_ID, QUIZ_ID
    with app.app_context():
        from src.models.user import User
        guru = User.query.filter_by(email='guru1@ebiox.com').first()
        from src.models.material import Material
        mat = Material.query.filter(Material.title.like('[Demo] %'),
                                    Material.teacher_id == guru.id).first()
        assert mat is not None, 'materi demo tidak ditemukan - jalankan scripts/seed_ml_activity.py dulu'
        material_id = mat.id
        # bersihkan fixture liar dari run yang terputus
        from src.models.quiz import Quiz
        for stray in Quiz.query.filter(Quiz.title == '[Smoke] AI Explanation Fixture').all():
            db.session.delete(stray)
        db.session.commit()

    st, d = _raw('POST', '/api/teacher/quizzes', teacher_token,
                 {'title': '[Smoke] AI Explanation Fixture', 'material_id': material_id,
                  'duration': 5, 'passing_grade': 50})
    assert st == 201, f'fixture create quiz: {st} {d}'
    QUIZ_ID = d['quiz']['id']

    def add_q(text):
        st, d = _raw('POST', f'/api/teacher/quizzes/{QUIZ_ID}/questions', teacher_token,
                     {'question_text': text, 'question_type': 'multiple_choice',
                      'difficulty': 'medium',
                      'options': [{'option_text': 'Benar', 'is_correct': True},
                                  {'option_text': 'Salah', 'is_correct': False}]})
        assert st == 201, f'fixture add question: {st} {d}'
        q = d['question']
        correct = next(o['option_id'] for o in q['options'] if o['is_correct'])
        wrong = next(o['option_id'] for o in q['options'] if not o['is_correct'])
        return q['question_id'], correct, wrong

    QUESTION_ID, q1_correct, _ = add_q('Smoke Q1: sel adalah unit terkecil kehidupan?')
    QUESTION_ID2, q2_correct, q2_wrong = add_q('Smoke Q2: virus memiliki sel tubuh sendiri?')

    st, _d = _raw('POST', f'/api/teacher/quizzes/{QUIZ_ID}/publish', teacher_token,
                  {'status': 'published'})
    assert st == 200, f'fixture publish: {st}'

    st, d = _raw('POST', f'/api/student/quizzes/{QUIZ_ID}/start', student_token, {})
    assert st == 201, f'fixture start attempt: {st} {d}'
    ATTEMPT_ID = d['attempt_id']
    # Q1 dijawab benar, Q2 dijawab salah agar analisis personal punya variasi
    for qid, opt in ((QUESTION_ID, q1_correct), (QUESTION_ID2, q2_wrong)):
        st, _d = _raw('POST', f'/api/student/attempts/{ATTEMPT_ID}/answer',
                      student_token, {'question_id': qid, 'selected_option_id': opt})
        assert st == 200, f'fixture answer: {st}'
    st, _d = _raw('POST', f'/api/student/attempts/{ATTEMPT_ID}/submit', student_token, {})
    assert st == 200, f'fixture submit: {st}'
    print(f'fixture ok: quiz={QUIZ_ID} questions=({QUESTION_ID},{QUESTION_ID2}) attempt={ATTEMPT_ID}')


def cleanup_fixture(teacher_token):
    if QUIZ_ID:
        _raw('DELETE', f'/api/teacher/quizzes/{QUIZ_ID}', teacher_token)


print('== LOGIN ==')
T = login('guru1@ebiox.com', '123123123')
S = login('murid1@ebiox.com', '123123123')
print('tokens ok')
build_fixture(T, S)
import atexit
atexit.register(cleanup_fixture, T)

print('== TEST 1: teacher generate explanation for question (rule-based fallback) ==')
st, d = call('gen-q1', 'POST', f'/api/questions/{QUESTION_ID}/explanation/generate', token=T, body={}, expect=201)
expl = d.get('explanation', {})
print('  status =', expl.get('status'), 'generated_by =', expl.get('generated_by'))
assert expl.get('status') == 'AI_GENERATED', expl.get('status')

print('== TEST 2: student GET while AI_GENERATED (expect 403) ==')
call('student-view-pending', 'GET', f'/api/questions/{QUESTION_ID}/explanation', token=S, expect=403)

print('== TEST 3: approve by teacher ==')
st, d = call('approve-q1', 'POST', f'/api/quiz/explanations/{expl["id"]}/approve', token=T, body={}, expect=200)
assert d['explanation']['status'] == 'APPROVED', d['explanation']['status']

print('== TEST 4: teacher regenerate an APPROVED explanation ==')
st, d = call('regen-q1', 'POST', f'/api/quiz/explanations/{expl["id"]}/regenerate', token=T, body={}, expect=200)
assert d['explanation']['status'] == 'AI_GENERATED', d['explanation']['status']

print('== TEST 5: student GET after regenerate (expect 403 until re-approved) ==')
call('student-view-regen', 'GET', f'/api/questions/{QUESTION_ID}/explanation', token=S, expect=403)

print('== TEST 6: teacher reject ==')
st, d = call('reject-q1', 'POST', f'/api/quiz/explanations/{expl["id"]}/reject', token=T, body={}, expect=200)
assert d['explanation']['status'] == 'REJECTED', d['explanation']['status']

print('== TEST 7: student GET rejected (expect 403) ==')
call('student-view-rejected', 'GET', f'/api/questions/{QUESTION_ID}/explanation', token=S, expect=403)

print('== TEST 8: teacher re-approve ==')
st, d = call('reapprove-q1', 'POST', f'/api/quiz/explanations/{expl["id"]}/approve', token=T, body={}, expect=200)
assert d['explanation']['status'] == 'APPROVED', d['explanation']['status']
assert d['explanation']['edited_by_teacher'] is False

print('== TEST 9: student GET approved explanation ==')
st, d = call('student-view-approved', 'GET', f'/api/questions/{QUESTION_ID}/explanation', token=S, expect=200)
e = d.get('explanation', {})
print('  summary =', (e.get('summary') or '')[:60])
assert e.get('status') == 'APPROVED'
assert e.get('option_explanations') and len(e['option_explanations']) == 2
print('  personal =', json.dumps(e.get('personal'), ensure_ascii=False)[:120])

print('== TEST 10: student GET attempt explanations (validates is_correct/analysis) ==')
st, d = call('attempt-expl', 'GET', f'/api/student/attempts/{ATTEMPT_ID}/explanations', token=S, expect=200)
res = d.get('results', [])
print('  results len =', len(res))
assert len(res) == 2
for r in res:
    print('   q', r['question_id'], 'status', r['status'], 'answer', r['answer'], 'is_correct', r.get('is_correct'))
assert res[0]['status'] == 'APPROVED'

print('== TEST 11: student submits feedback (expect 200) ==')
call('feedback-ok', 'POST', f'/api/quiz/explanations/{expl["id"]}/feedback', token=S,
     body={'rating': 'helpful', 'reason': 'penjelasan jelas'}, expect=200)
call('feedback-bad', 'POST', f'/api/quiz/explanations/{expl["id"]}/feedback', token=S,
     body={'rating': 'bogus'}, expect=400)

print('== TEST 12: recommended material click logging ==')
call('material-click', 'POST', f'/api/quiz/explanations/{expl["id"]}/material-click', token=S, body={}, expect=200)

print('== TEST 13: teacher dashboard ==')
st, d = call('teacher-dash', 'GET', '/api/teacher/quiz/explanations', token=T, expect=200)
print('  summary =', json.dumps(d.get('summary', {}), ensure_ascii=False)[:120])
assert 'summary' in d

print('== TEST 14: teacher edit explanation ==')
st, d = call('teacher-edit', 'PUT', f'/api/quiz/explanations/{expl["id"]}', token=T,
             body={'summary': 'Pembahasan suntingan guru untuk Q1.', 'correct_answer_explanation': 'Jawaban benar adalah A.'}, expect=200)
assert d['explanation']['edited_by_teacher'] is True
assert d['explanation']['summary'] == 'Pembahasan suntingan guru untuk Q1.'

print('== TEST 15: student generates (expect 403) ==')
call('student-gen', 'POST', f'/api/questions/{QUESTION_ID}/explanation/generate', token=S, body={}, expect=403)

print('== TEST 16: student GET edited-but-approved summary ==')
st, d = call('student-view-edited', 'GET', f'/api/questions/{QUESTION_ID}/explanation', token=S, expect=200)
assert 'Pembahasan suntingan guru' in d['explanation']['summary']

print('== TEST 17: batch generate for both questions ==')
st, d = call('batch-gen', 'POST', '/api/quiz/explanations/batch', token=T,
             body={'question_ids': [QUESTION_ID, QUESTION_ID2]}, expect=200)
print('  total =', d.get('total'), 'generated =', d.get('generated'), 'results =', d.get('results'))
assert d.get('total') == 2

print('== TEST 18: manual teacher explanation for question 67 (TEACHER_APPROVED) ==')
st, d = call('manual-q2', 'POST', f'/api/questions/{QUESTION_ID2}/explanation/manual', token=T,
             body={'summary': 'Pembahasan manual guru untuk Q2.',
                   'correct_answer_explanation': 'Kunci jawaban Q2 adalah B.',
                   'option_explanations': [
                       {'option': 'A', 'is_correct': False, 'explanation': 'A salah.'},
                       {'option': 'B', 'is_correct': True, 'explanation': 'B benar.'},
                   ]}, expect=201)
res = d.get('explanation', {})
print('  status =', res.get('status'))
assert res.get('status') == 'TEACHER_APPROVED', res.get('status')

print('== TEST 19: student can view TEACHER_APPROVED ==')
call('student-view-teacher-approved', 'GET', f'/api/questions/{QUESTION_ID2}/explanation', token=S, expect=200)

print('== TEST 20: regenerate TEACHER_APPROVED (expect 409) ==')
st, d = call('regen-teacher-approved', 'POST', f'/api/quiz/explanations/{res["id"]}/regenerate', token=T, body={}, expect=409)
print('  blocked with status', st)

print()
print('============== SUMMARY ==============')
fails = 0

for name, ok, status, data in results:
    mark = 'PASS' if ok else 'FAIL'
    if not ok:
        fails += 1
    print(f'{mark:4} {name:<28} status={status:<4} {json.dumps(data, ensure_ascii=False)[:160]}')
print(f'TOTAL={len(results)} FAIL={fails}')
sys.exit(1 if fails else 0)