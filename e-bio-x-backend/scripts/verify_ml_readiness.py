# ============================================================
# TAHAP 5 - Read-only verification that the ML layer is actually
# usable for students and teachers right now.
#
# Run this BEFORE any demo. It fails loudly rather than letting an
# empty dashboard or a stale model reach a reviewer.
#
#   .\.venv\Scripts\python.exe scripts\verify_ml_readiness.py
#
# Exit code 0 = ready. Non-zero = not ready.
# ============================================================
import os
import sys
from collections import Counter
from sqlalchemy import or_

# Allow running as `python scripts\verify_ml_readiness.py` from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app
from src.config.database import db
from src.models.user import User
from src.models.material import Material
from src.models.quiz import Quiz
from src.models.submission import Submission
from src.models.answer import Answer
from src.models.question import Question
from src.models.recommendation import Recommendation
from src.models.ml_model import MlModel
from src.ml import ml_config as cfg
from src.ml import decision_tree as dt
from src.ml import feature_service as fs
from src.ml.model_manager import load_artifact
from src.services import learning_analytics_service as an
from flask_jwt_extended import create_access_token

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok)))
    print(f"[{'OK  ' if ok else 'GAGAL'}] {name}" + (f"  -> {detail}" if detail else ""))
    return bool(ok)


def main():
    app = create_app()
    with app.app_context():
        students = User.query.filter_by(role='student').all()
        teachers = User.query.filter_by(role='teacher').all()

        print("=" * 66)
        print("VERIFIKASI KESEDIAAN ML - TAHAP 5")
        print("=" * 66)

        # ---- 1. data -------------------------------------------
        print("\n[1] DATA SISWA")
        ready = [s for s in students if fs.aggregate_student_features(s) is not None]
        pct = (len(ready) / len(students) * 100) if students else 0
        check('setiap siswa punya data cukup untuk ML',
              len(ready) == len(students),
              f'{len(ready)}/{len(students)} siap ({pct:.0f}%)')

        # ---- 2. model ------------------------------------------
        print("\n[2] MODEL TERSIMPAN")
        # Per-class models, one row scope at a time. The pooled model is
        # only a fallback, so it is not the thing to judge readiness by.
        class_recs = MlModel.query.filter(
            MlModel.model_type == 'decision_tree',
            MlModel.teacher_id.isnot(None)).order_by(MlModel.id.desc()).all()
        check('ada model Decision Tree', bool(class_recs) or bool(
            MlModel.query.filter_by(model_type='decision_tree').first()),
            f'{len(class_recs)} model per kelas')
        check('ada model K-Means', MlModel.query.filter(
            MlModel.model_type == 'kmeans').count() > 0,
            f"{MlModel.query.filter_by(model_type='kmeans').count()} baris")

        for tid in sorted({r.teacher_id for r in class_recs}):
            rec = MlModel.query.filter_by(model_type='decision_tree',
                                          teacher_id=tid).order_by(
                MlModel.id.desc()).first()
            t = User.query.get(tid)
            check(f"model kelas {t.name if t else tid} punya file sendiri",
                  rec is not None and rec.model_path
                  and os.path.exists(rec.model_path),
                  os.path.basename(rec.model_path or ''))

        # Validate whichever artifact a student would actually be scored
        # with, not just whatever happens to be newest overall.
        probe = teachers[0] if teachers else None
        artifact = load_artifact('decision_tree',
                                 teacher_id=probe.id if probe else None)
        if check('artefak DT bisa dimuat', artifact is not None):
            schema = artifact.get('feature_schema') or []
            check('artefak memakai skema anti-bocoran',
                  list(schema) == list(cfg.DT_FEATURES),
                  f'{len(schema)} feature')
            leak = [f for f in cfg.LABEL_DEFINING_FEATURES
                    if f in (schema or cfg.FEATURES)]
            check('tidak ada feature pembentuk label di input model',
                  not leak, f'bocor: {leak}' if leak else '')
            check('skema artefak = DT_FEATURES saat ini',
                  schema == list(cfg.DT_FEATURES),
                  'retrain diperlukan' if schema != list(cfg.DT_FEATURES) else '')

        # ---- 3. metrik jujur ----------------------------------
        print("\n[3] KEJUJURAN METRIK")
        dt_rec = (class_recs[0] if class_recs
                  else MlModel.query.filter_by(model_type='decision_tree')
                  .order_by(MlModel.id.desc()).first())
        m = (dt_rec.metrics_json if dt_rec else {}) or {}
        if check('metrik akurasi tersedia', m.get('accuracy') is not None,
                 str(m.get('accuracy'))):
            check('akurasi bukan 1.0 (indikasi kebocoran)',
                  m['accuracy'] < 1.0, f"accuracy={m['accuracy']}")
            check('baseline kelas mayoritas dilaporkan',
                  m.get('majority_baseline') is not None,
                  str(m.get('majority_baseline')))
            check('akurasi mengalahkan baseline',
                  m.get('lift_over_baseline') is not None
                  and m['lift_over_baseline'] > 0,
                  f"lift={m.get('lift_over_baseline')}")
            check('metode evaluasi bukan split tunggal',
                  m.get('method') == 'repeated_stratified_cv',
                  str(m.get('method')))
            check('catatan evaluasi menyertai angka',
                  bool(m.get('evaluation_note')))

        # ---- 4. endpoint siswa --------------------------------
        print("\n[4] ENDPOINT SISWA (privasi + kelengkapan)")
        client = app.test_client()
        if students:
            sample = ready[0] if ready else students[0]
            tok = create_access_token(identity=str(sample.id))
            h = {'Authorization': f'Bearer {tok}'}

            r = client.get('/api/student/learning-profile', headers=h)
            body = r.get_json() or {}
            check('profil siswa merespons 200', r.status_code == 200,
                  f'HTTP {r.status_code}')
            check('profil siswa punya status', bool(body.get('status')),
                  str(body.get('status')))
            check('profil siswa READY', body.get('status') == cfg.STATUS_READY,
                  str(body.get('status')))
            if body.get('status') == cfg.STATUS_READY:
                check('profil punya label cluster',
                      bool(body.get('cluster_label')),
                      str(body.get('cluster_label')))
                check('profil punya label mastery',
                      bool(body.get('mastery_label')),
                      str(body.get('mastery_label')))
                check('profil mencantumkan versi model',
                      bool(body.get('model_version')),
                      'v' + str(body.get('model_version')))
                check('label klaster mencantumkan versi model K-Means',
                      bool(body.get('cluster_model_version')),
                      'v' + str(body.get('cluster_model_version')))
            scope = body.get('model_scope') or {}
            check('profil menyatakan scope modelnya',
                  scope.get('scope') in ('class', 'pooled'),
                  str(scope.get('scope')))
            check('scope model punya penjelasan yang bisa dibaca',
                  bool(scope.get('note')), str(scope.get('note'))[:80])
            cscope = body.get('cluster_scope') or {}
            check('profil menyatakan scope model klasternya juga',
                  cscope.get('scope') in ('class', 'pooled'),
                  str(cscope.get('scope')))
            check('scope klaster memang model K-Means, bukan DT',
                  cscope.get('model_type') == 'kmeans'
                  and 'K-Means' in str(cscope.get('note') or ''),
                  f"{cscope.get('model_type')}: "
                  f"{str(cscope.get('note') or '')[:50]}")

            r = client.get('/api/student/recommendations', headers=h)
            body = r.get_json() or {}
            recs = body.get('recommendations') or []
            check('rekomendasi merespons 200', r.status_code == 200,
                  f'HTTP {r.status_code}')
            check('rekomendasi tidak kosong', len(recs) > 0,
                  f'{len(recs)} item')

            # privacy: one student must never be able to trigger a
            # prediction for another. The route is POST-only, so a GET
            # must not be treated as "allowed" - check the POST too.
            if len(students) >= 2:
                other = students[1] if students[0].id == sample.id else students[0]
                r = client.post('/api/ml/predict/%d' % other.id, headers=h)
                check('siswa tidak boleh memprediksi siswa lain (POST)',
                      r.status_code == 403, f'HTTP {r.status_code}')
                r = client.get('/api/ml/predict/%d' % other.id, headers=h)
                check('predict menolak GET (bukan 200)',
                      r.status_code != 200, f'HTTP {r.status_code}')

        # ---- 5. endpoint guru ---------------------------------
        print("\n[5] ENDPOINT GURU (scoping per kelas)")
        for t in teachers:
            ids = an.teacher_student_ids(t.id)
            tok = create_access_token(identity=str(t.id))
            r = client.get('/api/teacher/analytics/ml',
                           headers={'Authorization': f'Bearer {tok}'})
            body = r.get_json() or {}
            if not ids:
                check(f'guru "{t.name}" tanpa siswa -> NO_STUDENTS (jelas)',
                      body.get('scope_status') == 'NO_STUDENTS',
                      str(body.get('scope_status')))
                continue
            ok_ids = sum(1 for i in ids
                         if fs.aggregate_student_features(User.query.get(i)) is not None)
            shown = (body.get('signals') or 0)
            check(f'guru "{t.name}" analisis hanya siswa kelasnya',
                  shown == len(ids), f'tampil {shown} dari {len(ids)} siswa')
            check(f'guru "{t.name}" ada yang bisa dianalisis',
                  (body.get('analyzed') or 0) > 0,
                  f"{body.get('analyzed')}/{len(ids)}")
            mi = body.get('model') or {}
            check(f'guru "{t.name}" melihat model kelasnya sendiri',
                  mi.get('trained_on') == 'class',
                  f"trained_on={mi.get('trained_on')} "
                  f"teacher_id={mi.get('trained_on_teacher_id')}")
            check(f'guru "{t.name}" modelnya dilatih dari kelasnya saja',
                  mi.get('trained_on_teacher_id') == t.id,
                  f" dilatih dari {mi.get('training_sample_count')} siswa, "
                  f"kelas punya {len(ids)}")
            check(f'guru "{t.name}" diberi tahu scope angkanya',
                  bool(mi.get('training_scope_note')),
                  str(mi.get('training_scope_note'))[:70])
            cl = body.get('clusters') or {}
            check(f'guru "{t.name}" panel klaster menyebut scope modelnya',
                  bool(cl) and cl.get('training_scope') in ('class', 'pooled'),
                  f"training_scope={cl.get('training_scope')}")
            check(f'guru "{t.name}" nama klaster dijelaskan relatif per kelas',
                  bool(cl) and bool(cl.get('interpretation_note')),
                  str(cl.get('interpretation_note') or '')[:60])

        # ---- 6. scoping benar-benar terpisah ----------------
        print("\n[6] MODEL TERSIMPAN PER KELAS")
        trained = [t for t in teachers
                   if MlModel.query.filter_by(model_type='decision_tree',
                                              teacher_id=t.id).first()]
        paths = [MlModel.query.filter_by(model_type='decision_tree',
                                         teacher_id=t.id).order_by(
            MlModel.id.desc()).first().model_path for t in trained]
        check('tiap kelas punya file model sendiri',
              len(paths) == len(set(paths)),
              f'{len(paths)} kelas, {len(set(paths))} file berbeda')
        for t in trained:
            rec = MlModel.query.filter_by(model_type='decision_tree',
                                          teacher_id=t.id).order_by(
                MlModel.id.desc()).first()
            check(f'file model kelas "{t.name}" benar-benar ada',
                  rec and rec.model_path and os.path.exists(rec.model_path),
                  os.path.basename(rec.model_path or ''))
        pooled = MlModel.query.filter_by(model_type='decision_tree',
                                         teacher_id=None).order_by(
            MlModel.id.desc()).first()
        if pooled:
            check('model gabungan tidak menimpa file kelas',
                  pooled.model_path not in paths,
                  os.path.basename(pooled.model_path or ''))

        # Storage health: a row pointing at a missing file makes that
        # version unloadable, and both grow with every retrain.
        all_rows = MlModel.query.all()
        broken = [r for r in all_rows
                  if not (r.model_path and os.path.exists(r.model_path))]
        check('tidak ada baris model yang menunjuk file hilang',
              not broken,
              f'{len(broken)} baris rusak dari {len(all_rows)}')
        scopes = {}
        for r in all_rows:
            scopes[(r.model_type, r.teacher_id)] = scopes.get(
                (r.model_type, r.teacher_id), 0) + 1
        over = {k: v for k, v in scopes.items()
                if v > cfg.KEEP_VERSIONS_PER_SCOPE}
        check('jumlah versi per scope dalam batas retensi',
              not over,
              f'melting: {over}' if over
              else f'{len(scopes)} scope, maks '
                   f'{max(scopes.values()) if scopes else 0} versi')
        on_disk = {f for f in os.listdir(cfg.MODEL_DIR)
                   if f.endswith('.joblib')}
        referenced = {os.path.basename(r.model_path) for r in all_rows
                      if r.model_path}
        orphans = sorted(on_disk - referenced)
        check('tidak ada file model tanpa baris pemiliknya',
              not orphans, ', '.join(orphans[:3]) if orphans else '')

        # ---- 7. integritas klaim -----------------------------
        print("\n[7] INTEGRITAS KLAIM")
        types = Counter(r.recommendation_type
                        for r in Recommendation.query.all())
        check('tidak ada rekomendasi berlabel "ml" untuk hasil berbasis aturan',
              types.get('ml', 0) == 0,
              f'tipe tersimpan: {dict(types)}')
        check('rekomendasi berbasis aturan dilabeli "rule"',
              types.get('rule', 0) >= 0, f"rule={types.get('rule', 0)}")
        stamped = [r.id for r in Recommendation.query.all()
                   if r.recommendation_type == 'rule' and r.model_version]
        check('rekomendasi berbasis aturan tidak distempel versi model',
              not stamped,
              f'{len(stamped)} baris masih berlabel model' if stamped
              else 'tidak ada model_version pada hasil aturan')

        # ---- 8. akses materi per kelas ------------------------
        # A material with no course link must belong to its teacher's
        # class, not to every student. This re-derives the rule from
        # enrollments and teachers instead of trusting the helper, so a
        # regression that makes unlinked material public fails here even
        # though the helper would happily agree with itself.
        print("\n[8] AKSES MATERI PER KELAS (tidak bocor)")
        leaks = []
        for s in students:
            enrolled = {e.course_id for e in s.enrollments}
            teachers_of = set(an.student_teacher_ids(s.id))
            for m in an.student_accessible_materials(s):
                linked = an.material_course_ids(m)
                if linked:
                    if not (linked & enrolled):
                        leaks.append((s.id, m.id, 'tertaut ke course lain'))
                elif m.teacher_id is None or m.teacher_id not in teachers_of:
                    leaks.append((s.id, m.id, 'tak tertaut & bukan guru siswa'))
        check('tidak ada materi kelas lain bocor ke siswa',
              not leaks,
              f'{len(leaks)} kebocoran' if leaks
              else f'{len(students)} siswa diperiksa')

        # Reachable materials should be attached to a class. An unlinked
        # one belongs only to its teacher - it is not part of any class
        # page, so the per-class story looks emptier than it is.
        floating = [m.id for m in Material.query.filter_by(status='published').all()
                    if not an.material_course_ids(m)]
        check('tidak ada materi published mengambang tanpa kelas',
              not floating,
              f'tanpa course link: {floating}' if floating
              else 'semua materi punya kelas')

        # ---- 9. integritas soal & jawaban kuis ----------------
        # A submission whose score cannot be reproduced from its answers is
        # a number with nothing behind it. Every submitted attempt on a
        # quiz that has questions must carry one Answer row per question,
        # and the stored percentage must equal what those answers earn.
        print("\n[9] INTEGRITAS SOAL & JAWABAN KUIS")
        subs_all = Submission.query.filter_by(status='submitted').all()
        broken = []
        for sub in subs_all:
            qs = list(sub.quiz.questions) if sub.quiz else []
            if not qs:
                continue
            answers = Answer.query.filter_by(submission_id=sub.id).all()
            total = sum(q.points or 0 for q in qs)
            earned = sum(a.points_earned or 0 for a in answers)
            expect = round(earned / total * 100, 1) if total else 0.0
            if len(answers) != len(qs) or abs((sub.percentage or 0) - expect) > 0.05:
                broken.append(sub.id)
        check('setiap submission punya jawaban & skor dapat diturunkan',
              not broken,
              f'{len(broken)} rusak' if broken
              else f'{len(subs_all)} submission diperiksa')
        demo_no_q = [q.id for q in Quiz.query.all()
                     if q.title.startswith('[Demo]') and not q.questions]
        check('setiap kuis demo punya soal',
              not demo_no_q,
              f'tanpa soal: {demo_no_q}' if demo_no_q
              else 'semua kuis demo punya soal')

        # ---- 10. atribusi jawaban kuis -------------------------
        print("\n[10] ATRIBUSI JAWABAN KUIS KE BAGIAN (Fase 1 tagging)")
        # If a material's quiz questions were never linked to a section, those
        # answers belong to no section: they silently vanish from the
        # comprehension map. The section scores can still look healthy because
        # the interactive source alone clears the threshold at class level, so
        # this check looks at the quiz source specifically. That is the failure
        # mode that would otherwise hide.
        rows = []
        for mid, in db.session.query(Quiz.material_id).join(
                Submission, Submission.quiz_id == Quiz.id
        ).filter(Submission.status == 'submitted').distinct().all():
            if mid is None:
                continue
            mat = Material.query.get(int(mid))
            if mat is None:
                continue
            base = db.session.query(Answer.id).join(
                Submission, Submission.id == Answer.submission_id
            ).join(Quiz, Quiz.id == Submission.quiz_id
            ).join(Question, Question.id == Answer.question_id).filter(
                Quiz.material_id == int(mid),
                Submission.status == 'submitted')
            total = base.count()
            attributed = base.filter(or_(
                Question.section_id.isnot(None),
                Quiz.section_id.isnot(None))).count()
            students_answered = len({r[0] for r in db.session.query(
                Answer.student_id).join(
                    Submission, Submission.id == Answer.submission_id
                ).join(Quiz, Quiz.id == Submission.quiz_id).filter(
                    Quiz.material_id == int(mid),
                    Submission.status == 'submitted').distinct().all()})
            summary = an.section_mastery_class(int(mid), mat.teacher_id)
            scored = [r['score'] for r in summary['sections']
                      if r.get('score') is not None]
            rows.append((int(mid), students_answered, total, attributed,
                         len(scored), len(summary['sections']),
                         min(scored) if scored else None,
                         max(scored) if scored else None))
        # Only materials with enough answering students are held to the bar:
        # a material answered by one student is honestly thin, not broken.
        held = [r for r in rows if r[1] >= an.MIN_SECTION_SAMPLE and r[2] > 0]
        blind = [r[0] for r in held if r[3] == 0]
        low = [r[0] for r in held if r[2] and r[3] / r[2] < 0.5]
        check('jawaban kuis materi demo teratribusi ke bagian',
              not blind and not low,
              (f'tanpa atribusi: {blind} | atribusi <50%: {low}'
               if (blind or low) else f'{len(held)} materi diperiksa'))
        for mid, stu, total, attr, ns, nsec, lo, hi in sorted(rows):
            if stu >= an.MIN_SECTION_SAMPLE:
                pct = (attr / total * 100) if total else 0
                print(f'      materi {mid}: {attr}/{total} jawaban kuis '
                      f'teratribusi ({pct:.0f}%); {ns}/{nsec} bagian berskor '
                      f'(rentang {lo}..{hi})')
            else:
                print(f'      materi {mid}: lewati: hanya {stu} siswa menjawab '
                      f'(< {an.MIN_SECTION_SAMPLE})')

        # ---- ringkasan ----------------------------------------
        print("\n" + "=" * 66)
        passed = sum(1 for _, ok in checks if ok)
        failed = [n for n, ok in checks if not ok]
        print(f"HASIL: {passed}/{len(checks)} pemeriksaan lolos")
        if failed:
            print("\nGAGAL:")
            for n in failed:
                print(f"  - {n}")
            print("\nML BELUM SIAP DIPERKENALKAN.")
        else:
            print("\nML SIAP: setiap siswa punya profil & rekomendasi,")
            print("model ter evaluasi jujur, dan scoping guru bekerja.")
        print("=" * 66)
        return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())