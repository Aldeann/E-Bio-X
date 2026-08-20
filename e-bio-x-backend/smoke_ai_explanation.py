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


QUESTION_ID = 66
QUESTION_ID2 = 67
ATTEMPT_ID = 30
BANK_ID = 1
MATERIAL_ID = 28

print('== LOGIN ==')
T = login('guru1@ebiox.com', '123123123')
S = login('murid1@ebiox.com', '123123123')
print('tokens ok')

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