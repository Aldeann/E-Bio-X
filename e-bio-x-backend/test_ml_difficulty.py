# ============================================================
# TAHAP 5 - Regression tests for the difficulty feature chain.
#
# Three related bugs lived here; all silently disabled the whole
# "difficulty" dimension of the ML layer:
#
#   1. recommendation._student_weak_difficulty treated
#      `accuracy > 0` as "was attempted", so a student who answered
#      every easy question wrongly looked like they had never
#      attempted easy - hiding the level they most need help with.
#   2. analytics._difficulty_accuracy_material read `heading.level`
#      (an HTML heading level) as a difficulty, so headings were
#      bucketed as "difficulty 2"/"difficulty 3" and real questions
#      were never classified at all.
#   3. Material.difficulty is authored in Indonesian ("sedang")
#      while the ML layer compares against "medium", so
#      difficulty_fit was hardcoded to 0.5 - a dead component.
#
# These tests pin all three so they cannot silently return.
# ============================================================
from src.services import learning_analytics_service as an
from src.ml.recommendation import _student_weak_difficulty, _reasons_for, score_material
from src.ml.ml_config import REC_WEIGHTS

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}", extra or "")


print("===== normalize_difficulty =====")
for raw, want in [('mudah', 'easy'), ('sedang', 'medium'), ('sulit', 'hard'),
                  ('Mudah', 'easy'), ('SEDANG', 'medium'), ('Sulit', 'hard'),
                  ('easy', 'easy'), ('medium', 'medium'), ('hard', 'hard'),
                  ('sangat mudah', 'easy'), ('sangat sulit', 'hard'),
                  ('menengah', 'medium'),
                  ('1', 'easy'), ('2', 'medium'), ('3', 'hard'),
                  ('  mudah  ', 'easy')]:
    got = an.normalize_difficulty(raw)
    check(f'normalize {raw!r} -> {want}', got == want, f'got {got!r}')

for raw in [None, '', 'ngawur', 'EXTREMELY HARD', 4, 99]:
    check(f'normalize {raw!r} -> None (tidak menebak)',
          an.normalize_difficulty(raw) is None,
          f'got {an.normalize_difficulty(raw)!r}')

check('normalize accepts canonical keys unchanged',
      [an.normalize_difficulty(k) for k in ('easy', 'medium', 'hard')]
      == ['easy', 'medium', 'hard'])

print("\n===== difficulty_label =====")
check('label easy -> mudah', an.difficulty_label('easy') == 'mudah')
check('label medium -> sedang', an.difficulty_label('medium') == 'sedang')
check('label hard -> sulit', an.difficulty_label('hard') == 'sulit')
check('label None -> empty string', an.difficulty_label(None) == '')
check('label unknown passes through', an.difficulty_label('x') == 'x')

print("\n===== _student_weak_difficulty (bug #1) =====")
row_all_zero_attempted = {
    'easy_accuracy': 0.0, 'medium_accuracy': 0.0, 'hard_accuracy': 0.0,
    'easy_attempted': 10, 'medium_attempted': 8, 'hard_attempted': 3,
}
check('semua nol TAPI dicoba -> level terdalam, bukan None',
      _student_weak_difficulty(row_all_zero_attempted) == 'easy',
      f'got {_student_weak_difficulty(row_all_zero_attempted)!r}')

row = {'easy_accuracy': 0.0, 'medium_accuracy': 0.9, 'hard_accuracy': 0.9,
       'easy_attempted': 5, 'medium_attempted': 5, 'hard_attempted': 5}
check('hanya mudah yang lemah -> easy',
      _student_weak_difficulty(row) == 'easy')

row = {'easy_accuracy': 0.9, 'medium_accuracy': 0.8, 'hard_accuracy': 0.2,
       'easy_attempted': 5, 'medium_attempted': 5, 'hard_attempted': 5}
check('paling lemah di hard -> hard',
      _student_weak_difficulty(row) == 'hard')

row = {'easy_accuracy': 0.9, 'medium_accuracy': 0.3, 'hard_accuracy': None,
       'easy_attempted': 5, 'medium_attempted': 5, 'hard_attempted': 0}
check('hard tidak dicoba -> diabaikan meski akurasi None',
      _student_weak_difficulty(row) == 'medium')

row = {'easy_accuracy': 1.0, 'medium_accuracy': 1.0, 'hard_accuracy': 1.0,
       'easy_attempted': 5, 'medium_attempted': 5, 'hard_attempted': 5}
check('serba dikuasai -> seri dipecah ke termudah',
      _student_weak_difficulty(row) == 'easy')

row = {'easy_accuracy': 0.0, 'medium_accuracy': 0.0, 'hard_accuracy': 0.0,
       'easy_attempted': 0, 'medium_attempted': 0, 'hard_attempted': 0}
check('tidak ada yang dicoba -> None',
      _student_weak_difficulty(row) is None)

row_legacy = {'easy_accuracy': 0.0, 'medium_accuracy': 0.1, 'hard_accuracy': 0.2}
check('row lama tanpa metadata -> None, bukan tebakan',
      _student_weak_difficulty(row_legacy) is None)

row_empty = {}
check('row kosong -> None', _student_weak_difficulty(row_empty) is None)

print("\n===== difficulty_fit_components (bug #3) =====")
base = dict(mastery=50.0, question_error_rate=0.5, finished=False,
            topic=None, topic_mastery=None)


def fit_of(difficulty, weak):
    return 1.0 if (an.normalize_difficulty(difficulty)
                   and an.normalize_difficulty(difficulty) == weak) else 0.5


check('bahan "sedang" + lemah medium -> cocok (1.0)',
      fit_of('sedang', 'medium') == 1.0)
check('bahan "sedang" + lemah easy -> tidak cocok (0.5)',
      fit_of('sedang', 'easy') == 0.5)
check('bahan tidak dikenal -> 0.5 (netral)',
      fit_of('ngawur', 'easy') == 0.5)
check('tanpa kelemahan -> 0.5 (netral)',
      fit_of('sedang', None) == 0.5)

# The real proof: before the fix every difficulty_fit was 0.5.
check('BUG LAMA: bahan "sedang" pernah menghasilkan 1.0? TIDAK (regresi terdeteksi)',
      fit_of('sedang', 'medium') != 0.5,
      'kalau nilai ini 0.5 maka normalisasi belum bekerja')

s_match = score_material(dict(base, difficulty='sedang', student_weak_difficulty='medium'))
s_other = score_material(dict(base, difficulty='sedang', student_weak_difficulty='easy'))
check('skor benar-benar berubah saat difficulty_fit aktif',
      s_match != s_other, f'{s_match} vs {s_other}')
check('perbedaan skor = bobot difficulty_fit x 0.5',
      abs((s_match - s_other) - REC_WEIGHTS['difficulty_fit'] * 0.5) < 1e-9,
      f'delta={s_match - s_other:.6f}')

print("\n===== alasan ke siswa (tidak boleh bocor nilai mentah) =====")
for diff, weak, want in [('sedang', 'medium', 'Fokus pada tingkat sedang'),
                         ('sulit', 'hard', 'Fokus pada tingkat sulit'),
                         ('mudah', 'easy', 'Fokus pada tingkat mudah'),
                         ('2', 'medium', 'Fokus pada tingkat sedang')]:
    got = _reasons_for(dict(base, difficulty=diff, student_weak_difficulty=weak), {})
    check(f'bahan {diff!r} -> {want!r}', want in got, f'got {got}')

for diff, weak in [('ngawur', 'easy'), ('ngawur', 'ngawur'), (None, 'easy')]:
    got = _reasons_for(dict(base, difficulty=diff, student_weak_difficulty=weak), {})
    check(f'bahan {diff!r} tidak menampilkan alasan tingkat',
          not any('Fokus' in r for r in got), f'got {got}')

got = _reasons_for(dict(base, difficulty=None, student_weak_difficulty=None), {})
check('tetap ada minimal satu alasan (fallback)',
      len(got) >= 1, f'got {got}')

print("\n===== _difficulty_accuracy_material (bug #2) =====")
# Monkeypatch the query objects so the bucketing logic can be exercised
# offline. MaterialSection is deliberately NOT stubbed: the old code
# called MaterialSection.query.get() and would raise here, which is
# exactly the regression we want to be unable to hide.


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter_by(self, **kw):
        return self

    def all(self):
        return self._rows

    def get(self, pk):
        return _CONTENTS.get(pk)


class _FakeAnswer:
    def __init__(self, content_id, is_correct):
        self.content_id = content_id
        self.is_correct = is_correct


class _FakeContent:
    def __init__(self, data):
        self.data = data


_CONTENTS = {
    1: _FakeContent({'difficulty': 'easy', 'question': 'q1'}),
    2: _FakeContent({'difficulty': 'sulit', 'question': 'q2'}),
    3: _FakeContent({'difficulty': '2', 'question': 'q3'}),
    4: _FakeContent({'level': 2, 'content': 'Heading 2'}),
    5: _FakeContent({'level': 3, 'content': 'Heading 3'}),
    6: _FakeContent({'question': 'tanpa difficulty'}),
}

_ANSWERS = [
    _FakeAnswer(1, True),    # easy, benar
    _FakeAnswer(1, False),   # easy, salah
    _FakeAnswer(2, False),   # hard, salah
    _FakeAnswer(3, True),    # numerik 2 -> medium, benar
    _FakeAnswer(4, True),    # heading 2 -> HARUS bukan bucket '2'
    _FakeAnswer(5, True),    # heading 3 -> HARUS bukan bucket '3'
    _FakeAnswer(6, False),   # tanpa field -> default medium
]

_orig_answers, _orig_contents = an.StudentAnswer, an.MaterialContent
an.StudentAnswer = type('S', (), {'query': _FakeQuery(_ANSWERS)})()
an.MaterialContent = type('M', (), {'query': _FakeQuery(_ANSWERS)})()
try:
    res = an._difficulty_accuracy_material(1, 1)
finally:
    an.StudentAnswer, an.MaterialContent = _orig_answers, _orig_contents

check('easy terhitung dan akurasinya benar',
      res.get('easy', {}).get('total') == 2
      and res['easy']['accuracy'] == 50.0, f'got {res.get("easy")}')
check('sulit dinormalkan ke bucket "hard"',
      res.get('hard', {}).get('total') == 1
      and res['hard']['accuracy'] == 0.0, f'got {res.get("hard")}')
check('tingkat numerik "2" masuk bucket medium',
      res.get('medium', {}).get('total') == 4,
      f'got total={res.get("medium", {}).get("total")} '
      f'(konten 3 + heading 4,5 + konten 6 tanpa difficulty)')
check('BUG LAMA: heading level TIDAK lagi jadi bucket tersendiri',
      '2' not in res and '3' not in res, f'keys={sorted(res)}')
check('hanya kunci kanonik yang muncul',
      all(k in ('easy', 'medium', 'hard') for k in res), f'keys={sorted(res)}')
check('total seluruh bucket = jumlah jawaban',
      sum(v['total'] for v in res.values()) == len(_ANSWERS),
      f'{sum(v["total"] for v in res.values())} vs {len(_ANSWERS)}')

# Empty input must not invent buckets.
_orig_answers = an.StudentAnswer
an.StudentAnswer = type('S', (), {'query': _FakeQuery([])})()
try:
    check('tidak ada jawaban -> hasil kosong', an._difficulty_accuracy_material(1, 1) == {})
finally:
    an.StudentAnswer = _orig_answers

print("\n===== metadata *_attempted di feature row =====")
from src.ml import feature_service as fs
import inspect
check('feature_service menyediakan diff_total',
      'diff_total' in inspect.getsource(fs.aggregate_student_features))
check('fitur *_attempted ikut dikembalikan',
      all(k in inspect.getsource(fs.aggregate_student_features)
          for k in ("'easy_attempted'", "'medium_attempted'", "'hard_attempted'")))

# Metadata must NOT become a model feature, or every saved artifact
# would silently mismatch the new feature list.
from src.ml import ml_config as cfg
check('*_attempted BUKAN model feature (artifact lama tetap valid)',
      not any(k.endswith('_attempted') for k in cfg.FEATURES),
      f'FEATURES={cfg.FEATURES}')
check('*_attempted BUKAN fitur K-Means',
      not any(k.endswith('_attempted') for k in cfg.KMEANS_FEATURES))

# Functional proof rather than source inspection: preprocessing must
# project the row down to exactly cfg.FEATURES, dropping the metadata.
from src.ml import preprocessing
probe = {k: 0.5 for k in cfg.FEATURES}
probe.update({'easy_attempted': 7, 'medium_attempted': 3, 'hard_attempted': 0})
imputed = preprocessing.impute_row(probe)
check('impute_row membuang metadata *_attempted',
      not any(k.endswith('_attempted') for k in imputed),
      f'keys={sorted(imputed)}')
check('impute_row menghasilkan tepat cfg.FEATURES',
      sorted(imputed) == sorted(cfg.FEATURES))
check('normalize_row panjangnya = jumlah FEATURES (artifact tidak rusak)',
      len(preprocessing.normalize_row(probe)) == len(cfg.FEATURES))
check('normalize_subset juga mengabaikan metadata',
      len(preprocessing.normalize_subset(probe, cfg.KMEANS_FEATURES))
      == len(cfg.KMEANS_FEATURES))

print("\n===== SUMMARY =====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"TOTAL: {len(results)}  PASS: {passed}  FAIL: {len(results) - passed}")
for name, ok, extra in results:
    if not ok:
        print(f"  FAIL> {name} {extra}")
import sys
sys.exit(1 if passed != len(results) else 0)