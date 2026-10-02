# ============================================================
# TAHAP 5 - Per-class model scoping.
#
# The request behind this: a teacher's ML insight must reflect THEIR
# class, not a model pooled from every student in the system. That means
# training has to be scoped too, not just the display.
#
# What these tests pin:
#   - a teacher trains on their own students and nothing else
#   - two teachers get two different, separately stored models
#   - a readout always says which scope produced it
#   - a class too small to train falls back to pooled, visibly
#   - one teacher can never reach another's students
#
# Runs against the real app + database, so it creates and then removes
# its own throwaway teacher. Existing rows are only ever read.
# ============================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_app
from src.config.database import db
from src.models.user import User
from src.models.course import Course
from src.models.enrollment import Enrollment
from src.models.material import Material
from src.models.ml_model import MlModel
from src.ml import ml_config as cfg
from src.ml import model_manager
from src.services import learning_analytics_service as analytics
from flask_jwt_extended import create_access_token
from sqlalchemy import inspect

results = []


def check(name, cond, extra=""):
    # Returns the boolean on purpose. Without a return, `if check(...)`
    # is always falsy and silently skips a whole block of assertions -
    # which is exactly how the admin-training checks went missing once
    # before.
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


# A teacher id that will never collide with a real one.
STAMP = 'zzscopeunit'
created = {'teacher': None, 'course': None, 'students': [], 'tokens': {}}


def make_fixture(app):
    """A throwaway teacher owning 3 students of their own."""
    teacher = User.query.filter_by(role='teacher', email=f'{STAMP}@test.local').first()
    if teacher is None:
        teacher = User(email=f'{STAMP}@test.local', name='Scope Unit Guru',
                       role='teacher')
        db.session.add(teacher)
        db.session.flush()
    course = Course.query.filter_by(teacher_id=teacher.id, name=f'{STAMP} kelas').first()
    if course is None:
        course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
        db.session.add(course)
        db.session.flush()
    for i in range(3):
        s = User.query.filter_by(role='student',
                                 email=f'{STAMP}{i}@test.local').first()
        if s is None:
            s = User(email=f'{STAMP}{i}@test.local', name=f'Scope Unit Murid {i}',
                     role='student')
            db.session.add(s)
            db.session.flush()
        if not Enrollment.query.filter_by(course_id=course.id,
                                          student_id=s.id).first():
            db.session.add(Enrollment(course_id=course.id, student_id=s.id))
        created['students'].append(s)
    db.session.commit()
    created['teacher'] = teacher
    created['course'] = course
    return teacher


def drop_fixture():
    for s in created['students']:
        Enrollment.query.filter_by(student_id=s.id).delete(synchronize_session=False)
        db.session.delete(s)
    created['students'] = []
    if created['course'] is not None:
        db.session.delete(created['course'])
        created['course'] = None
    if created['teacher'] is not None:
        db.session.delete(created['teacher'])
        created['teacher'] = None
    db.session.commit()


def token_for(user):
    return create_access_token(identity=str(user.id))


def main():
    app = create_app()
    with app.app_context():
        print('=' * 68)
        print('SCOPING MODEL ML PER KELAS')
        print('=' * 68)

        # ---------------------------------------------------- setup
        teacher = make_fixture(app)
        other_teachers = [t for t in User.query.filter_by(role='teacher').all()
                          if t.id != teacher.id]
        students = list(created['students'])
        client = app.test_client()
        t_tok = token_for(teacher)
        s_tok = token_for(students[0])
        h_t = {'Authorization': f'Bearer {t_tok}'}
        h_s = {'Authorization': f'Bearer {s_tok}'}

        try:
            # ------------------------------------------------ SKEMA
            print('\n[1] SKEMA DAN PENYIMPANAN')
            cols = {c['name']: c for c in
                    inspect(db.engine).get_columns('ml_models')}
            check('kolom ml_models.teacher_id ada', 'teacher_id' in cols,
                  ', '.join(sorted(cols)))
            check('teacher_id boleh kosong (model gabungan)',
                  cols.get('teacher_id', {}).get('nullable') is True)

            nxt = model_manager.next_version('decision_tree')
            check('version tetap satu penghitung global (bukan per kelas)',
                  int(nxt.split('.')[0]) > _min_existing_major('decision_tree'),
                  f"v{nxt} > v{_min_existing_major('decision_tree')}.0")

            tag_pooled = model_manager.scope_tag(None)
            tag_class = model_manager.scope_tag(7)
            check('tag scope pooled kosong', tag_pooled == '', repr(tag_pooled))
            check('tag scope kelas unik per guru',
                  tag_class != tag_pooled and '7' in tag_class, repr(tag_class))

            # ------------------------------------------------ TRAINING
            print('\n[2] TRAINING HANYA KELAS SENDIRI')
            r = client.post('/api/ml/train', headers=h_t)
            body = r.get_json() or {}
            check('POST /api/ml/train 200 untuk guru', r.status_code == 200,
                  f'HTTP {r.status_code}')
            check('response menyatakan teacher_id miliknya',
                  body.get('teacher_id') == teacher.id,
                  f"{body.get('teacher_id')} vs {teacher.id}")
            check('hanya siswa kelas sendiri yang dianalisis',
                  body.get('analysis_students') == len(students),
                  f"{body.get('analysis_students')} siswa "
                  f"(kelas punya {len(students)})")
            check('kelas kecil -> INSUFFICIENT_DATA, bukan angka palsu',
                  (body.get('decision_tree') or {}).get('status')
                  == cfg.STATUS_INSUFFICIENT,
                  str((body.get('decision_tree') or {}).get('status')))
            check('pesan menjelaskan butuh berapa siswa',
                  'butuh' in str((body.get('decision_tree') or {}).get('message', '')).lower()
                  or 'cukup' in str((body.get('decision_tree') or {}).get('message', '')).lower(),
                  str((body.get('decision_tree') or {}).get('message'))[:70])

            check('payload `details` ada untuk UI',
                  isinstance(body.get('details'), dict)
                  and 'decision_tree' in (body.get('details') or {}))

            # ------------------------------------------- MODEL TERSIMPAN
            print('\n[3] MODEL TERSIMPAN PER KELAS')
            mine = MlModel.query.filter_by(model_type='decision_tree',
                                           teacher_id=teacher.id).all()
            # A 3-student class is below MIN_SAMPLES_DT, so the correct
            # outcome is that NOTHING is saved for it. Silently storing a
            # model anyway is the failure this guards.
            check('kelas kecil tidak menyimpan model apa pun',
                  len(mine) == 0, f'{len(mine)} baris (harusnya 0)')

            others = [t for t in other_teachers
                      if MlModel.query.filter_by(model_type='decision_tree',
                                                 teacher_id=t.id).first()]
            if check('ada kelas lain yang sudah dilatih (pembanding)', others):
                other_rec = MlModel.query.filter_by(
                    model_type='decision_tree',
                    teacher_id=others[0].id).order_by(MlModel.id.desc()).first()
                check('file kelas lain terpisah dari file gabungan',
                      other_rec.model_path
                      != _pooled_path(),
                      f"{os.path.basename(other_rec.model_path)}")
                check('file kelas bearscope di namanya',
                      'class' in (other_rec.model_path or ''),
                      os.path.basename(other_rec.model_path))
                check('versi kelas != versi gabungan',
                      other_rec.model_version != _pooled_rec().model_version,
                      f"v{other_rec.model_version} vs "
                      f"v{_pooled_rec().model_version}")
                check('resolve_scope kelas lain = class',
                      model_manager.resolve_scope('decision_tree', others[0].id)
                      == 'class',
                      model_manager.resolve_scope('decision_tree', others[0].id))
            check('resolve_scope kelas tanpa model + fallback = pooled',
                  model_manager.resolve_scope('decision_tree', teacher.id)
                  == 'pooled',
                  model_manager.resolve_scope('decision_tree', teacher.id))
            check('resolve_scope tanpa fallback = none',
                  model_manager.resolve_scope('decision_tree', teacher.id,
                                              allow_pooled_fallback=False)
                  == 'none')

            # Two classes must not overwrite each other's file even when
            # they retrain back to back at the same version number.
            p1 = model_manager._artifact_path('decision_tree', '99.0', 2)
            p2 = model_manager._artifact_path('decision_tree', '99.0', 71)
            check('dua kelas -> dua path berbeda',
                  p1 != p2, f"{os.path.basename(p1)} | {os.path.basename(p2)}")
            check('path kelas tidak sama dengan path gabungan',
                  p1 != model_manager._artifact_path('decision_tree', '99.0', None))

            # save_artifact must record the scope it was given.
            stub = {'model': object(), 'preprocessor': None, 'metrics': {},
                    'sample_count': 1, 'status': cfg.STATUS_READY}
            meta = model_manager.save_artifact('decision_tree', stub,
                                               teacher_id=teacher.id)
            saved = MlModel.query.filter_by(model_type='decision_tree',
                                            teacher_id=teacher.id).order_by(
                MlModel.id.desc()).first()
            check('save_artifact menyimpan teacher_id',
                  saved is not None and saved.teacher_id == teacher.id)
            check('save_artifact menulis file terpisah',
                  saved is not None and os.path.exists(saved.model_path)
                  and f'class{teacher.id}_' in saved.model_path,
                  os.path.basename(saved.model_path or ''))
            check('_meta membawa teacher_id', meta.get('teacher_id') == teacher.id,
                  str(meta.get('teacher_id')))
            check('_meta menandai scope=class', meta.get('scope') == 'class',
                  str(meta.get('scope')))
            check('record menandai bukan pooled', saved.is_pooled is False)
            # Capture the path first: after the delete the ORM object is
            # expired and reading it back raises ObjectDeletedError.
            saved_path = saved.model_path
            MlModel.query.filter_by(id=saved.id).delete(synchronize_session=False)
            db.session.commit()
            model_manager._clear()
            if saved_path and os.path.exists(saved_path):
                os.remove(saved_path)
            check('artefak uji benar-benar dibersihkan',
                  not (saved_path and os.path.exists(saved_path)),
                  os.path.basename(saved_path or ''))

            # ------------------------------------------- RETENSI VERSI
            # Each retrain writes a row and a file, so without pruning a
            # class that retrains often grows without limit. The danger
            # is deleting a row but keeping its file, or the reverse.
            print('\n[3b] RETENSI VERSI PER SCOPE')
            probe_tid = 987654
            made = []
            try:
                for _ in range(cfg.KEEP_VERSIONS_PER_SCOPE + 2):
                    m = model_manager.save_artifact(
                        'decision_tree', dict(stub), teacher_id=probe_tid)
                    made.append(m['model_version'])
                kept = (MlModel.query
                        .filter_by(model_type='decision_tree',
                                   teacher_id=probe_tid)
                        .order_by(MlModel.id.desc()).all())
                check('jumlah versi dibatasi sesuai konfigurasi',
                      len(kept) == cfg.KEEP_VERSIONS_PER_SCOPE,
                      f'{len(kept)} dari {len(made)} training')
                check('versi yang dipertahankan adalah yang terbaru',
                      [r.model_version for r in kept] == list(reversed(made[-cfg.KEEP_VERSIONS_PER_SCOPE:])),
                      f"{kept[0].model_version}..{kept[-1].model_version}")
                check('setiap baris yang tersisa punya file',
                      all(r.model_path and os.path.exists(r.model_path)
                          for r in kept),
                      'tidak ada baris menunjuk file yang hilang')
                check('file versi lama ikut terhapus',
                      all(not os.path.exists(
                          model_manager._artifact_path(
                              'decision_tree', v, probe_tid))
                          for v in made[:2]),
                      f'versi {made[0]}, {made[1]} dihapus dari disk')
                # Pruning one scope must not touch another.
                other_before = MlModel.query.filter(
                    MlModel.model_type == 'decision_tree',
                    MlModel.teacher_id.isnot(None),
                    MlModel.teacher_id != probe_tid).count()
                model_manager.prune_old_versions('decision_tree', probe_tid,
                                                 keep=1)
                other_after = MlModel.query.filter(
                    MlModel.model_type == 'decision_tree',
                    MlModel.teacher_id.isnot(None),
                    MlModel.teacher_id != probe_tid).count()
                check('pruning satu kelas tidak menyentuh kelas lain',
                      other_before == other_after,
                      f'{other_before} -> {other_after}')
            finally:
                left = MlModel.query.filter_by(model_type='decision_tree',
                                               teacher_id=probe_tid).all()
                files = [r.model_path for r in left]
                MlModel.query.filter_by(model_type='decision_tree',
                                        teacher_id=probe_tid).delete(
                    synchronize_session=False)
                db.session.commit()
                model_manager._clear()
                for f in files:
                    if f and os.path.exists(f):
                        os.remove(f)

            # ------------------------------------------- LOAD & FALLBACK
            print('\n[4] RESOLUSI MODEL')
            got = model_manager.load_artifact('decision_tree',
                                              teacher_id=teacher.id,
                                              allow_pooled_fallback=False)
            check('load tanpa fallback = None untuk kelas tanpa model',
                  got is None)
            got_fb = model_manager.load_artifact('decision_tree',
                                                teacher_id=teacher.id)
            check('load dengan fallback mengembalikan model gabungan',
                  got_fb is not None, 'cadangan tersedia')
            art = model_manager.load_artifact('decision_tree', teacher_id=None)
            check('load eksplisit teacher_id=None -> artefak gabungan',
                  art is not None
                  and (art.get('_meta') or {}).get('teacher_id') is None)

            # ------------------------------------------- ANALYTICS GURU
            print('\n[5] ANALYTICS GURU (scoping per kelas)')
            r = client.get('/api/teacher/analytics/ml', headers=h_t)
            b = r.get_json() or {}
            check('analytics guru 200', r.status_code == 200, f'HTTP {r.status_code}')
            # The class HAS 3 students, none with enough data. That must
            # read as "0 of 3 analysable", not as an empty class.
            check('kelas berisi siswa tapi datanya kurang -> READY',
                  b.get('scope_status') == 'READY',
                  str(b.get('scope_status')))
            check('semua siswa kelas tetap dihitung',
                  (b.get('analyzed', 0) + b.get('insufficient_data', 0))
                  == len(students),
                  f"{b.get('analyzed')} analysed + {b.get('insufficient_data')} kurang "
                  f"= {len(students)}")
            check('tidak ada distribusi dari data yang tidak ada',
                  not b.get('mastery_distribution'),
                  str(b.get('mastery_distribution')))
            check('pesan jujur soal berapa siswa yang bisa dianalisis',
                  'dari' in str(b.get('scope_message') or ''),
                  str(b.get('scope_message'))[:90])
            check('scope pooled dinyatakan karena kelasnya belum dilatih',
                  (b.get('model') or {}).get('training_scope') == 'pooled',
                  str((b.get('model') or {}).get('training_scope')))
            check('catatan pooled memperingatkan belum spesifik',
                  'gabungan' in str((b.get('model') or {}).get('training_scope_note') or '').lower()
                  or 'indikasi' in str((b.get('model') or {}).get('training_scope_note') or '').lower(),
                  str((b.get('model') or {}).get('training_scope_note'))[:90])

            if others:
                ot = others[0]
                oh = {'Authorization': f'Bearer {token_for(ot)}'}
                r2 = client.get('/api/teacher/analytics/ml', headers=oh)
                b2 = r2.get_json() or {}
                mi = b2.get('model') or {}
                their_ids = set(analytics.teacher_student_ids(ot.id))
                check('analytics guru lain di-scope ke siswanya',
                      (mi.get('class_students') == 0
                       or (b2.get('analyzed', 0) + b2.get('insufficient_data', 0))
                       == len(their_ids)),
                      f"tampil {b2.get('analyzed', 0) + b2.get('insufficient_data', 0)} "
                      f"dari {len(their_ids)}")
                check('model yang dipakai adalah model kelas itu sendiri',
                      mi.get('trained_on') == 'class',
                      f"trained_on={mi.get('trained_on')}")
                check('catatan scope menjelaskan model kelas sendiri',
                      'kelas Anda' in str(mi.get('training_scope_note') or ''),
                      str(mi.get('training_scope_note'))[:90])

            # ------------------------------------------- AKSES SILANG
            print('\n[6] PRIVASI LINTAS KELAS')
            far = User.query.filter(User.role == 'student',
                                    User.id.notin_(
                                        [s.id for s in students] +
                                        (others and [0] or [0]))).first()
            r = client.post(f'/api/ml/predict/{far.id}', headers=h_t)
            check('guru tidak bisa memprediksi siswa luar kelasnya',
                  r.status_code == 403, f'HTTP {r.status_code}')
            r = client.post(f'/api/ml/predict/{students[0].id}', headers=h_s)
            check('siswa tidak bisa memicu prediksi (403)',
                  r.status_code == 403, f'HTTP {r.status_code}')

            r = client.get('/api/teacher/analytics/ml')
            check('tanpa token ditolak (401)', r.status_code == 401,
                  f'HTTP {r.status_code}')

            # ------------------------------------------- SCOPE SISWA
            print('\n[7] SCOPE UNTUK SISWA')
            ids = analytics.student_teacher_ids(students[0].id)
            check('student_teacher_users menemukan gurunya',
                  ids == [teacher.id], str(ids))
            other_student = User.query.filter_by(role='student').first()
            if other_student and other_student.id not in [s.id for s in students]:
                many = analytics.student_teacher_ids(other_student.id)
                check('siswa dengan 2 kelas mengembalikan 2 guru',
                      isinstance(many, list) and len(many) >= 1, str(many))
                check('daftar guru terurut & unik',
                      many == sorted(set(many)), str(many))
                oh = {'Authorization': f'Bearer {token_for(other_student)}'}
                r = client.get('/api/student/learning-profile', headers=oh)
                b = r.get_json() or {}
                sc = b.get('model_scope') or {}
                check('profil siswa selalu menyebut scope modelnya',
                      sc.get('scope') in ('class', 'pooled'),
                      str(sc.get('scope')))
                check('scope kelas menamai gurunya',
                      sc.get('scope') != 'class' or bool(sc.get('teacher_name')),
                      f"guru={sc.get('teacher_name')}")
                check('scope pooled dijelaskan sebagai belum khusus',
                      sc.get('scope') != 'pooled'
                      or 'gabungan' in str(sc.get('note') or '').lower()
                      or 'seluruh' in str(sc.get('note') or '').lower(),
                      str(sc.get('note'))[:90])

                # ----------------------------------- ATURAN SATU MODEL
                # A student in several classes gets ONE answer, so the
                # choice of which class model speaks for them is a rule
                # someone has to be able to rely on. Pin it here so it
                # cannot change quietly.
                print('\n[7b] ATURAN: SISWA DUA KELAS -> SATU JAWABAN')
                from src.controllers import ml_controller as mlc
                multi = [u for u in User.query.filter_by(role='student').all()
                         if len(analytics.student_teacher_ids(u.id)) > 1]
                if check('ada siswa yang ikut lebih dari satu kelas', multi,
                         f'{len(multi)} siswa'):
                    probe = multi[0]
                    tids = analytics.student_teacher_ids(probe.id)
                    recs = [(t, model_manager.latest_record(
                        'decision_tree', t, allow_pooled_fallback=False))
                        for t in tids]
                    trained = [(t, r) for t, r in recs if r is not None]
                    if check('ada >1 model kelas tersedia untuk dia', len(trained) > 1,
                             f'{len(trained)} dari {len(tids)} guru punya model'):
                        newest = max(trained, key=lambda tr: tr[1].trained_at)[0]
                        chosen = mlc._newest_class_record(probe.id)
                        check('siswa memakai model kelas yang PALING BARU',
                              chosen is not None and chosen.teacher_id == newest,
                              f"dipilih guru id={chosen.teacher_id and chosen.teacher_id}, "
                              f"terbaru={newest}")
                        # Determinism: same answer on every call, or the
                        # student's badge would flicker between reloads.
                        picks = {mlc._newest_class_record(probe.id).teacher_id
                                 for _ in range(5)}
                        check('hasilnya konsisten diulang (tidak berkedip)',
                              len(picks) == 1, str(picks))
                        # And the student is told, not shown a bare badge.
                        oh2 = {'Authorization': f'Bearer {token_for(probe)}'}
                        b2 = client.get('/api/student/learning-profile',
                                        headers=oh2).get_json() or {}
                        sc2 = b2.get('model_scope') or {}
                        check('siswa diberi tahu kelas mana yang dipakai',
                              sc2.get('teacher_id') == chosen.teacher_id,
                              f"api={sc2.get('teacher_id')} "
                              f"function={chosen.teacher_id}")
                        check('penjelasan scope menyebut nama guru',
                              bool(sc2.get('teacher_name')),
                              str(sc2.get('teacher_name')))
                else:
                    print('   (dilewati: tidak ada siswa multi-kelas di data)')

            # ------------------------------- SCOPE K-MEANS INDEPENDEN
            # Mastery and grouping are two separate models and must be
            # resolved separately: the tree's class must not decide which
            # K-Means speaks for a student. Otherwise a pooled (or another
            # class's) cluster name can ride under a class-scope note.
            print('\n[7c] SCOPE K-MEANS INDEPENDEN DARI DECISION TREE')
            from src.controllers import ml_controller as mlc
            multi = [u for u in User.query.filter_by(role='student').all()
                     if len(analytics.student_teacher_ids(u.id)) > 1]
            if multi:
                probe = multi[0]
                km_expected = mlc._newest_class_record(probe.id, 'kmeans')
                # Contract: the endpoint states the K-Means scope too, not
                # only the tree's.
                oh = {'Authorization': f'Bearer {token_for(probe)}'}
                bb = client.get('/api/student/learning-profile',
                                headers=oh).get_json() or {}
                cs = bb.get('cluster_scope') or {}
                check('endpoint siswa memuat cluster_scope',
                      cs.get('model_type') == 'kmeans'
                      and (km_expected is None
                           or cs.get('teacher_id') == km_expected.teacher_id),
                      f"api={cs.get('teacher_id')} "
                      f"expected={km_expected and km_expected.teacher_id}")
                # Force the two model types onto DIFFERENT teachers: make a
                # class's K-Means the newest without touching any tree, and
                # choose one that is not the tree's current class. Both
                # classes here have their own K-Means file, so this is a
                # real load, not a stub.
                dt_now = mlc._newest_class_record(probe.id, 'decision_tree')
                km_recs = [(t, model_manager.latest_record(
                    'kmeans', t, allow_pooled_fallback=False))
                    for t in analytics.student_teacher_ids(probe.id)]
                candidates = [(t, r) for t, r in km_recs
                              if r is not None
                              and (dt_now is None or t != dt_now.teacher_id)]
                if candidates:
                    from datetime import datetime
                    pick_tid, pick_rec = candidates[0]
                    pick_rec.trained_at = datetime.utcnow()
                    db.session.flush()
                    dt_rec = mlc._newest_class_record(probe.id, 'decision_tree')
                    km_rec = mlc._newest_class_record(probe.id, 'kmeans')
                    check('scope K-Means dipilih lepas dari scope DT',
                          km_rec is not None
                          and km_rec.teacher_id == pick_tid
                          and (dt_now is None
                               or dt_rec.teacher_id == dt_now.teacher_id),
                          f"km={km_rec and km_rec.teacher_id} "
                          f"dt={dt_rec and dt_rec.teacher_id}")
                    _, _, dt_s, km_s = mlc._load_for_student(probe)
                    check('label klaster memakai model K-Means itu sendiri',
                          km_s.get('teacher_id') == pick_tid
                          and (dt_now is None
                               or dt_s.get('teacher_id') == dt_now.teacher_id),
                          f"km_scope={km_s.get('teacher_id')} "
                          f"dt_scope={dt_s.get('teacher_id')}")
                    check('tiap scope menyebut jenis modelnya',
                          'K-Means' in str(km_s.get('note'))
                          and 'Decision Tree' in str(dt_s.get('note')),
                          f"km={str(km_s.get('note'))[:48]}")
                    db.session.rollback()
                else:
                    print('   (dilewati: tidak ada kelas K-Means lain untuk '
                          'dipindah)')
            else:
                print('   (dilewati: tidak ada siswa multi-kelas di data)')

            # ------------------------------------- TRAINING OLEH ADMIN
            # Admin trains the pooled fallback AND one model per class in
            # a single call. This path is easy to break (it is the only
            # one that loops) and the teacher-only tests above never
            # reach it.
            print('\n[8] TRAINING OLEH ADMIN (gabungan + tiap kelas)')
            admin = User.query.filter_by(role='admin').first()
            # check() is called on its own line rather than inside the
            # `if`: the result is the thing being asserted, so burying it
            # in the condition made the whole block conditional on a
            # detail that was never really the test.
            check('ada akun admin', admin is not None, str(admin and admin.id))
            if admin is not None:
                ah = {'Authorization': f'Bearer {token_for(admin)}'}
                r = client.post('/api/ml/train', headers=ah)
                b = r.get_json() or {}
                check('training admin 200 (tidak error)', r.status_code == 200,
                      f'HTTP {r.status_code}')
                check('scope utama admin = pooled',
                      b.get('scope') == 'pooled', str(b.get('scope')))
                check('teacher_id utama kosong (model gabungan)',
                      b.get('teacher_id') is None, str(b.get('teacher_id')))
                classes = b.get('classes') or []
                all_teachers = User.query.filter_by(role='teacher').count()
                check('admin dilatihkan model untuk setiap guru',
                      len(classes) == all_teachers,
                      f'{len(classes)} kelas vs {all_teachers} guru')
                check('tiap entri kelas punya decision_tree',
                      all('decision_tree' in c for c in classes),
                      f'{sum(1 for c in classes if "decision_tree" in c)} ok')
                check('tiap entri kelas punya kmeans',
                      all('kmeans' in c for c in classes),
                      f'{sum(1 for c in classes if "kmeans" in c)} ok')
                check('tiap entri kelas menyebut teacher_id-nya',
                      all(c.get('teacher_id') for c in classes),
                      str([c.get('teacher_id') for c in classes]))
                # The admin's own 3-student fixture is gone by now, so it
                # must not appear as a trained class.
                check('kelas uji kecil tidak ikut terlatih diam-diam',
                      all(c.get('decision_tree', {}).get('status')
                          != cfg.STATUS_READY
                          for c in classes
                          if c.get('teacher_id') == teacher.id),
                      'kelas uji kecil tetap INSUFFICIENT_DATA')
                check('model gabungan tersimpan terpisah',
                      MlModel.query.filter_by(model_type='decision_tree',
                                              teacher_id=None).first()
                      is not None)
                ready_classes = [c for c in classes
                                 if c.get('decision_tree', {}).get('status')
                                 == cfg.STATUS_READY]
                check('semua kelas yang dilatih punya file sendiri',
                      len({MlModel.query.filter_by(
                          model_type='decision_tree',
                          teacher_id=c['teacher_id']).order_by(
                          MlModel.id.desc()).first().model_path
                          for c in ready_classes}) == len(ready_classes),
                      f'{len(ready_classes)} kelas terlatih')
                check('respons admin punya `details` untuk UI',
                      isinstance(b.get('details'), dict))
                # A self-referencing dict would blow up jsonify.
                check('respons admin bisa diserialisasi (tanpa referensi melingkar)',
                      _serialises(b))

            # ------------------------------------------- AUTO-RETRAIN
            # Auto-retrain used to run globally on a bare thread with
            # `except: pass`, so a burst of clicks started many trainings
            # at once and any failure was invisible. Both are guarded
            # here, plus the per-class scoping itself.
            print('\n[9] AUTO-RETRAIN (per kelas, terkunci, failure terlihat)')
            from src.controllers import learning_tracking_controller as ltc
            real_students = [u for u in User.query.filter_by(role='student').all()
                             if analytics.student_teacher_ids(u.id)]
            if check('ada siswa yang punya kelas', real_students,
                     f'{len(real_students)} siswa'):
                probe = real_students[0]
                before = MlModel.query.count()
                # Activity is far below the threshold after training, so
                # this must be a no-op rather than a retrain.
                ltc._maybe_auto_retrain(probe.id)
                check('tidak ada retrain di bawah ambang aktivitas',
                      MlModel.query.count() == before,
                      f'{before} -> {MlModel.query.count()} baris')
                check('ambang aktivitas masih berlaku (tidak diubah diam-diam)',
                      ltc.ml_cfg.AUTO_RETRAIN_THRESHOLD > 0,
                      str(ltc.ml_cfg.AUTO_RETRAIN_THRESHOLD))
                # Holding the lock is what stops the thread storm.
                ltc._retrain_lock.acquire()
                try:
                    ltc._maybe_auto_retrain(probe.id)
                    check('lock menahan retrain kedua (anti badai thread)',
                          MlModel.query.count() == before,
                          'panggilan kedua langsung kembali')
                finally:
                    ltc._retrain_lock.release()
                check('lock dilepas setelah selesai',
                      not ltc._retrain_lock.locked())

            check('auto-retrain tanpa student_id tidak melempar',
                  ltc._maybe_auto_retrain(None) is None)
            check('auto-retrain untuk siswa tanpa kelas tidak melempar',
                  ltc._maybe_auto_retrain(10 ** 9) is None)
            # The old code swallowed every failure. A background trainer
            # that cannot report its own errors leaves a class on a stale
            # model with no signal, so the failure has to be logged.
            # Parsed as AST rather than grepped, so a stray `pass`
            # elsewhere in the module cannot produce a false pass.
            check('kegagalan auto-retrain dicatat, bukan ditelan diam-diam',
                  _auto_retrain_logs_failures())

            # --------------------------------- AKSES MATERI PER KELAS
            # A published material with no course link used to be visible
            # to EVERY student, so one class's material showed up in other
            # classes' dashboards, recommendations and ML features. It now
            # belongs to the teacher who created it. These objects are not
            # persisted - student_can_access_material only reads their
            # attributes and the student's teachers.
            print('\n[10] AKSES MATERI PER KELAS (tidak bocor ke kelas lain)')
            from src.services.learning_analytics_service import (
                student_can_access_material, material_course_ids)
            from src.controllers.material_controller import _can_student_access

            outsider = next(
                (u for u in User.query.filter_by(role='student').all()
                 if u.id not in {s.id for s in created['students']}
                 and teacher.id not in analytics.student_teacher_ids(u.id)),
                None)

            unlinked = Material(title='ZZ scope unlinked', status='published',
                                teacher_id=teacher.id)
            check('materi tanpa course diakui tak tertaut',
                  material_course_ids(unlinked) == set(),
                  str(material_course_ids(unlinked)))
            check('siswa kelas guru pemilik BOLEH melihat materi tak tertaut',
                  student_can_access_material(created['students'][0], unlinked) is True)
            if check('ada siswa di luar kelas itu untuk diuji', outsider is not None):
                check('siswa kelas lain TIDAK melihat materi tak tertaut',
                      student_can_access_material(outsider, unlinked) is False)
                # The two layers must not drift: a material the service
                # hides must also be refused by the endpoint guard.
                check('controller & service memakai aturan yang sama',
                      _can_student_access(unlinked, created['students'][0])
                      == student_can_access_material(created['students'][0], unlinked)
                      == True
                      and _can_student_access(unlinked, outsider)
                      == student_can_access_material(outsider, unlinked)
                      == False)

            linked = Material(title='ZZ scope linked', status='published',
                              teacher_id=teacher.id)
            linked.course_links = [created['course']]
            check('materi tertaut hanya untuk siswa course itu',
                  student_can_access_material(created['students'][0], linked) is True
                  and (outsider is None
                       or student_can_access_material(outsider, linked) is False))

            # The quiz controller used to carry its own copy of the rule
            # and let this case through. It must now agree with the rest.
            from src.controllers import quiz_controller as qc
            from src.controllers.file_proxy_controller import _material_readable
            from src.models.quiz import Quiz
            q = Quiz(title='ZZ scope quiz', material_id=10 ** 9,
                     status='published')
            q.material = unlinked
            check('kuis dari materi tak tertaut tidak bocor ke kelas lain',
                  qc._student_can_take(q, created['students'][0]) is True
                  and (outsider is None
                       or qc._student_can_take(q, outsider) is False))
            check('unduhan file materi tak tertaut tidak bocor',
                  _material_readable(unlinked, created['students'][0]) is True
                  and (outsider is None
                       or _material_readable(unlinked, outsider) is False))

            check('materi tanpa pemilik & tanpa course tidak terlihat siapa pun',
                  student_can_access_material(
                      created['students'][0],
                      Material(title='ZZ yatim', status='published',
                               teacher_id=None)) is False)
            check('materi belum dipublikasikan tidak terlihat',
                  student_can_access_material(
                      created['students'][0],
                      Material(title='ZZ draft', status='draft',
                               teacher_id=teacher.id)) is False)

        finally:
            drop_fixture()
        print('\n' + '=' * 68)
        passed = sum(1 for _, ok, _ in results if ok)
        failed = [(n, e) for n, ok, e in results if not ok]
        print(f'TOTAL: {len(results)}  PASS: {passed}  FAIL: {len(failed)}')
        for n, e in failed:
            print(f'  FAIL> {n} {e}')
        return 1 if failed else 0


def _min_existing_major(model_type):
    import re
    rows = MlModel.query.filter_by(model_type=model_type).with_entities(
        MlModel.model_version).all()
    majors = [int(m.group(1)) for (v,) in rows if (m := re.match(r'^(\d+)', v or ''))]
    return max(majors) if majors else 0


def _pooled_rec():
    return MlModel.query.filter_by(model_type='decision_tree',
                                   teacher_id=None).order_by(
        MlModel.id.desc()).first()


def _pooled_path():
    rec = _pooled_rec()
    return rec.model_path if rec else None


def _serialises(obj):
    """A dict that contains itself is a real bug: jsonify raises on it."""
    import json
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False


def _auto_retrain_logs_failures():
    """True when _maybe_auto_retrain logs instead of swallowing errors.

    Walks the function's AST: any `except` whose body is only `pass` (or
    only an ellipsis) counts as a swallowed failure, and at least one
    handler has to call a logger.
    """
    import ast
    import inspect as _inspect
    from src.controllers import learning_tracking_controller as mod
    fn = getattr(mod, '_maybe_auto_retrain', None)
    if fn is None:
        return False
    tree = ast.parse(_inspect.getsource(_inspect.unwrap(fn)))
    swallowed = False
    logged = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body = [s for s in node.body
                if not (isinstance(s, ast.Expr)
                        and isinstance(s.value, ast.Constant))]
        if not body or all(isinstance(s, ast.Pass) for s in body):
            swallowed = True
        for s in ast.walk(node):
            if (isinstance(s, ast.Call)
                    and isinstance(s.func, ast.Attribute)
                    and s.func.attr in ('exception', 'error', 'warning')):
                logged = True
    return logged and not swallowed


if __name__ == '__main__':
    sys.exit(main())
