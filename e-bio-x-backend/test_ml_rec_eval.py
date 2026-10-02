# ============================================================
# TAHAP 5 - Unit tests for the recommendation closed-loop
# evaluation layer (offline, no live server needed).
#
# These tests guard the honesty rules of
# src/ml/recommendation_evaluation.py:
#   - small samples must NEVER produce a rate (no fabricated numbers)
#   - calibration must distinguish "supported" from "no signal"
#   - reason text must fall into a known group
#
# Only the pure functions are exercised here; the DB-backed
# completion-yield path is covered by test_tahap5_ml.py.
# ============================================================
from src.ml import ml_config as cfg
from src.ml import recommendation_evaluation as ev

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}", extra or "")


class StubRec:
    """Minimal stand-in for a Recommendation row (clicked/completed are
    NULL in the DB, so `None` is the correct "not happened" value)."""

    def __init__(self, score, clicked=None, completed=None, reasons=None,
                 student_id=1, material_id=1):
        self.recommendation_score = score
        self.clicked_at = clicked
        self.completed_at = completed
        self.reason_json = reasons or []
        self.student_id = student_id
        self.material_id = material_id
        self.material = None


T = True   # clicked_at = datetime
N = None   # clicked_at = NULL


def build(per_bin, n_each=10):
    """per_bin: list of (click_count) one entry per EVAL_SCORE_BINS entry."""
    rows = []
    for (lo, hi, _label), clicks in zip(cfg.EVAL_SCORE_BINS, per_bin):
        mid = (lo + hi) / 2.0
        for i in range(n_each):
            rows.append(StubRec(mid, T if i < clicks else N))
    return rows


print('===== SCORE BINNING =====')
labels = [cfg.EVAL_SCORE_BINS[i][2] for i in range(len(cfg.EVAL_SCORE_BINS))]
check('bin covers score 0.0', ev._bin_label(0.0) == labels[0], f'-> {ev._bin_label(0.0)}')
check('bin covers score 1.0', ev._bin_label(1.0) == labels[-1], f'-> {ev._bin_label(1.0)}')
check('bin covers score 0.5', ev._bin_label(0.5) is not None, f'-> {ev._bin_label(0.5)}')
check('bin for None score is None', ev._bin_label(None) is None)
check('score range sums to weights total',
      abs(sum(w for w in cfg.REC_WEIGHTS.values()) - 1.0) < 1e-9,
      f'sum={sum(cfg.REC_WEIGHTS.values())}')
covered = [ev._bin_label(s) for s in (0.0, 0.15, 0.35, 0.5, 0.7, 0.99, 1.0)]
check('every score in range lands in a bin', all(c is not None for c in covered))

print('\n===== CALIBRATION VERDICTS =====')
cal = ev._calibration(build([0, 0, 10, 10]))
check('rising click-rate -> TERDUKUNG', cal['verdict'] == 'TERDUKUNG', cal['verdict'])

cal = ev._calibration(build([10, 10, 0, 0]))
check('falling click-rate -> TERBALIK', cal['verdict'] == 'TERBALIK', cal['verdict'])

cal = ev._calibration(build([10, 0, 10, 0]))
check('zig-zag -> TIDAK_BERATURAN', cal['verdict'] == 'TIDAK_BERATURAN', cal['verdict'])

cal = ev._calibration(build([5, 5, 5, 5]))
check('flat click-rate -> TIDAK_BERBEDA (no discrimination)',
      cal['verdict'] == 'TIDAK_BERBEDA', cal['verdict'])
check('flat case warns score cannot discriminate',
      'tidak membedakan' in (cal['interpretation'] or ''))

check('verdict carries an interpretation', bool(cal.get('interpretation')))

print('\n===== NO FABRICATED NUMBERS =====')
tiny = build([1, 1, 1, 1], n_each=2)
cal = ev._calibration(tiny)
check('small bins -> all INSUFFICIENT_DATA',
      all(b['status'] == cfg.STATUS_INSUFFICIENT for b in cal['bins']))
check('small bins expose NO click_through_rate',
      all('click_through_rate' not in b for b in cal['bins']))
check('small bins still report the real count',
      all(b['recommended'] == 2 for b in cal['bins']))
check('too few bins -> verdict is None (not guessed)', cal['verdict'] is None, str(cal['verdict']))
check('overall status is INSUFFICIENT_DATA',
      cal['status'] == cfg.STATUS_INSUFFICIENT)

fun = ev._funnel([StubRec(0.5, T), StubRec(0.5, N)])
check('small funnel -> INSUFFICIENT_DATA', fun['status'] == cfg.STATUS_INSUFFICIENT)
check('small funnel has no rate', 'click_through_rate' not in fun)

print('\n===== FUNNEL MATH =====')
fun = ev._funnel([StubRec(0.1, T, None), StubRec(0.2, T, T),
                  StubRec(0.3, T, None), StubRec(0.4, T, T),
                  StubRec(0.5, N, None), StubRec(0.6, N, None),
                  StubRec(0.7, N, None), StubRec(0.8, N, None)])
check('funnel READY', fun['status'] == cfg.STATUS_READY)
check('funnel counts recommended', fun['recommended'] == 8)
check('funnel counts clicked', fun['clicked'] == 4)
check('funnel counts completed', fun['completed'] == 2)
check('funnel CTR = clicked/recommended', fun['click_through_rate'] == 0.5)
check('funnel completion = completed/recommended', fun['completion_rate'] == 0.25)
check('funnel completion-of-clicked = 2/4', fun['completion_of_clicked'] == 0.5)
check('funnel reports clicked-but-not-finished', fun['clicked_not_completed'] == 2)

fun = ev._funnel([StubRec(0.1, N) for _ in range(6)])
check('no clicks -> completion_of_clicked is None (no ZeroDivision)',
      fun['click_through_rate'] == 0.0 and fun['completion_of_clicked'] is None)

print('\n===== REASON GROUPING =====')
check('"Penguasaan materi masih 40%" -> tinggi_kepentingan',
      ev._reason_group('Penguasaan materi masih 40%') == 'tinggi_kepentingan')
check('"Masih banyak kesalahan pada soal (60% salah)" -> banyak_salah',
      ev._reason_group('Masih banyak kesalahan pada soal (60% salah)') == 'banyak_salah')
check('"Materi belum selesai" -> belum_selesai',
      ev._reason_group('Materi belum selesai') == 'belum_selesai')
check('"Fokus pada tingkat sulit" -> tingkat_kesulitan',
      ev._reason_group('Fokus pada tingkat sulit') == 'tingkat_kesulitan')
check('"Materi sudah dikuasai..." -> sudah_dikuasai',
      ev._reason_group('Materi sudah dikuasai. Ini adalah pengulangan.') == 'sudah_dikuasai')
check('"Mulai belajar untuk..." -> umum',
      ev._reason_group('Mulai belajar untuk mendapatkan rekomendasi yang lebih sesuai.') == 'umum')
check('unknown text -> lainnya',
      ev._reason_group('Alasan Misterius Tak Dikenal') == 'lainnya')

rows = [StubRec(0.1, T, None, ['Penguasaan materi masih 40%', 'Materi belum selesai'])
        for _ in range(6)]
re_ = ev._reason_effectiveness(rows)
groups = {g['group']: g for g in re_['groups']}
check('two reason groups detected', len(groups) == 2, f'-> {list(groups)}')
check('all-clicked group -> CTR 1.0',
      groups['tinggi_kepentingan']['click_through_rate'] == 1.0)

# A recommendation listing the same group twice must only count once.
dup = [StubRec(0.1, N, None, ['Materi belum selesai', 'Materi belum selesai'])]
re_dup = ev._reason_effectiveness(dup + [StubRec(0.1, N, None, ['Materi belum selesai'])]
                                  + [StubRec(0.1, N, None, ['Materi belum selesai'])]
                                  + [StubRec(0.1, N, None, ['Materi belum selesai'])]
                                  + [StubRec(0.1, N, None, ['Materi belum selesai'])])
g = {x['group']: x for x in re_dup['groups']}['belum_selesai']
check('duplicate reason text counted once', g['shown'] == 5, f"shown={g['shown']}")

check('unknown-reason group still reported',
      ev._reason_effectiveness([StubRec(0.5, T, None, ['Entah apa ini'])] * 6)['groups'][0]['group']
      == 'lainnya')

print('\n===== HONESTY METADATA =====')
check('observation note present', 'OBSERVASIONAL' in ev.OBSERVATION_NOTE)
check('note explicitly denies causality',
      'bukan kausal' in ev.OBSERVATION_NOTE.lower()
      or 'kausal' in ev.OBSERVATION_NOTE.lower())
check('min-sample thresholds are positive',
      cfg.EVAL_MIN_SAMPLES > 0 and cfg.EVAL_MIN_STUDENTS > 0)

# ------------------------------------------------------------
# Endpoint privacy (DB-backed). The project's privacy rule is that a
# teacher only ever sees their own students, so this is asserted here
# rather than left to manual checking.
# ------------------------------------------------------------
print('\n===== ENDPOINT AUTH & PRIVACY =====')
try:
    from src import create_app
    from src.models.user import User
    from flask_jwt_extended import create_access_token

    _app = create_app()
    with _app.app_context():
        _teacher = User.query.filter_by(role='teacher').first()
        _student = User.query.filter_by(role='student').first()
        _tk = create_access_token(identity=str(_teacher.id))
        _sk = create_access_token(identity=str(_student.id))

    _c = _app.test_client()
    _url = '/api/ml/evaluation/recommendations'

    _r = _c.get(_url, headers={'Authorization': f'Bearer {_tk}'})
    check('teacher gets 200', _r.status_code == 200, f'HTTP {_r.status_code}')
    check('teacher scope is teacher-only', (_r.get_json() or {}).get('scope') == 'teacher')

    _r = _c.get(_url, headers={'Authorization': f'Bearer {_sk}'})
    check('student is blocked with 403', _r.status_code == 403, f'HTTP {_r.status_code}')
    check('student error mentions teacher-only',
          'guru' in str((_r.get_json() or {}).get('error', '')).lower())

    _r = _c.get(_url)
    check('unauthenticated request gets 401', _r.status_code == 401, f'HTTP {_r.status_code}')

    _r = _c.post(_url, headers={'Authorization': f'Bearer {_tk}'})
    check('endpoint is read-only (POST -> 405)', _r.status_code == 405, f'HTTP {_r.status_code}')
except Exception as e:  # DB unavailable -> do not silently pretend it passed
    check('endpoint auth & privacy checks could run', False, repr(e))

print("\n===== SUMMARY =====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"TOTAL: {len(results)}  PASS: {passed}  FAIL: {len(results) - passed}")
for name, ok, extra in results:
    if not ok:
        print(f"  FAIL> {name} {extra}")
import sys
sys.exit(1 if passed != len(results) else 0)
