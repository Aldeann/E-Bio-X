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


print('== LOGIN ==')
T = login('guru1@ebiox.com', '123123123')
S = login('murid1@ebiox.com', '123123123')
print('tokens ok')

print('== find common course ==')
_, tc = call('teacher-courses', 'GET', '/api/courses/teacher', token=T, expect=200)
_, sc = call('student-courses', 'GET', '/api/courses/student', token=S, expect=200)
tc = tc if isinstance(tc, list) else tc.get('courses', [])
sc = sc if isinstance(sc, list) else sc.get('courses', [])
teacher_ids = [c['id'] for c in tc]
student_ids = [c['id'] for c in sc]
common = [cid for cid in teacher_ids if cid in student_ids]
course_id = common[0] if common else None
print('course_id =', course_id)

print('== forums list ==')
call('forums-list', 'GET', '/api/forums', token=T, expect=200)

print('== create forum ==')
st, d = call('forum-create', 'POST', '/api/forums', token=T, body={
    'type': 'GENERAL_DISCUSSION',
    'title': 'Pembahasan Bab Sel (smoke)',
    'description': 'Diskusi umum tentang sel',
    'course_id': course_id,
    'visibility': 'COURSE',
    'status': 'ACTIVE',
}, expect=201)
forum = d['forum']
forum_id = forum['id']
print('forum_id =', forum_id)

print('== forum detail (student) ==')
call('forum-detail', 'GET', f'/api/forums/{forum_id}', token=S, expect=200)

print('== create post (student) ==')
st, d = call('post-create', 'POST', f'/api/forums/{forum_id}/posts', token=S,
             body={'content': 'Saya ingin bertanya tentang membran sel dan fungsinya.'}, expect=201)
post_id = d['post']['id']
print('post_id =', post_id)

print('== idempotency ==')
st, d = call('post-idem', 'POST', f'/api/forums/{forum_id}/posts', token=S,
             body={'content': 'Test idempotency key.', 'request_id': 'dup-001'}, expect=201)
st, d = call('post-idem-dup', 'POST', f'/api/forums/{forum_id}/posts', token=S,
             body={'content': 'Harus ditolak.', 'request_id': 'dup-001'}, expect=400)
print('dup blocked status =', st)

print('== reply (teacher) ==')
st, d = call('reply-create', 'POST', f'/api/posts/{post_id}/replies', token=T,
             body={'content': 'Membran sel tersusun dari fosfolipid bilayer dan protein.'}, expect=201)
reply_id = d['post']['id']
print('reply_id =', reply_id)

print('== reaction add/toggle ==')
call('reaction-add', 'POST', f'/api/posts/{reply_id}/reactions', token=S, body={'reaction_type': 'like'}, expect=200)
call('reaction-toggle-off', 'POST', f'/api/posts/{reply_id}/reactions', token=S, body={'reaction_type': 'like'}, expect=200)

print('== student notifications ==')
call('notifications', 'GET', '/api/notifications', token=S, expect=200)

print('== student analytics ==')
call('student-analytics', 'GET', '/api/student/forum/analytics', token=S, expect=200)

print('== teacher analytics ==')
call('teacher-analytics', 'GET', '/api/teacher/forum/analytics', token=T, expect=200)

print('== settings ==')
call('settings-get', 'GET', '/api/forum/settings', token=T, expect=200)
call('settings-set', 'PUT', '/api/forum/settings', token=T, body={'allow_student_forum_creation': False}, expect=200)
call('settings-get2', 'GET', '/api/forum/settings', token=S, expect=200)

print('== best answer ==')
call('best-answer', 'POST', f'/api/posts/{reply_id}/best-answer', token=T, expect=200)
_, d = call('student-analytics2', 'GET', '/api/student/forum/analytics', token=S, expect=200)
print('  student best_answers =', d.get('best_answers'), 'xp =', d.get('xp'))

print('== feedback ==')
call('feedback-add', 'POST', f'/api/posts/{post_id}/feedback', token=T,
     body={'feedback': 'Pertanyaan bagus, lanjutkan!'}, expect=201)

print('== presentation flow ==')
st, d = call('presentation-create', 'POST', '/api/forums', token=T, body={
    'type': 'PRESENTATION',
    'title': 'Presentasi Kelompok DNA (smoke)',
    'description': 'Praktik presentasi kelas',
    'course_id': course_id,
    'visibility': 'CLASS',
    'status': 'ACTIVE',
    'presentation_group_name': 'Kelompok 1',
    'presenter_id': 1,  # check: may be invalid; will fallback to group members
}, expect=201)
pf = d.get('forum')
pf_id = pf['id'] if pf else None
print('presentation_forum =', pf_id)

if pf_id:
    st, d = call('presenter-question', 'POST', f'/api/forums/{pf_id}/questions', token=S,
                 body={'content': 'Apa perbedaan DNA dan RNA?'}, expect=201)
    qpost = d.get('post')
    qid = qpost['question']['id'] if qpost and qpost.get('question') else None
    print('  question id =', qid)
    if qid:
        call('question-answer', 'POST', f'/api/questions/{qid}/answer', token=T,
             body={'content': 'DNA double helix, RNA single strand dengan gula ribosa.'}, expect=201)
        call('presenter-dashboard', 'GET', f'/api/forums/{pf_id}/presenter-dashboard', token=T, expect=200)

print('== lock forum ==')
st, d = call('forum-lock', 'POST', f'/api/forums/{forum_id}/lock', token=T, expect=200)
print('  lock ->', d)

print('== post in closed (student, expect 403) ==')
call('post-in-closed', 'POST', f'/api/forums/{forum_id}/posts', token=S,
     body={'content': 'Posting setelah ditutup harus ditolak'}, expect=403)

print('== moderation queue ==')
call('moderation-queue', 'GET', '/api/teacher/forum/moderation', token=T, expect=200)

print('== mentions suggest ==')
call('mentions-suggest', 'GET', f'/api/forum/mentions/suggest?forum_id={forum_id}', token=S, expect=200)

print('== report post ==')
sc, d = call('report-post', 'POST', f'/api/posts/{post_id}/report', token=S,
             body={'reason': 'OFF_TOPIC', 'description': 'smoke test'}, expect=201)

print()
print('============== SUMMARY ==============')
fails = 0
for name, ok, status, data in results:
    mark = 'PASS' if ok else 'FAIL'
    if not ok:
        fails += 1
    print(f'{mark:4} {name:<24} status={status:<4} {json.dumps(data, ensure_ascii=False)[:160]}')
print(f'TOTAL={len(results)} FAIL={fails}')
sys.exit(1 if fails else 0)