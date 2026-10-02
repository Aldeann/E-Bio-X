# ============================================================
# TAHAP 5 - ML & recommendation API controller.
#
# Privacy rules:
#   - student: only own profile / own recommendations.
#   - teacher/admin: ml analytics scoped to their own students.
#   - training/predict endpoints are teacher/admin protected; students
#     can never trigger training.
# ============================================================
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.user import User
from src.models.enrollment import Enrollment
from src.config.database import db
from src.ml import ml_config as cfg
from src.ml import model_manager, feature_service, decision_tree, kmeans as kmeans_mod
from src.ml import cluster_interpreter, profile as profile_mod, recommendation as rec_service
from src.ml import recommendation_evaluation as rec_eval
from src.services import learning_analytics_service as analytics


def _user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _student():
    user = _user()
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    if user.role != 'student':
        return None, (jsonify({'error': 'Endpoint ini khusus siswa'}), 403)
    return user, None


def _teacher():
    user = _user()
    if not user:
        return None, (jsonify({'error': 'User not found'}), 404)
    if user.role not in ('teacher', 'admin'):
        return None, (jsonify({'error': 'Endpoint ini khusus guru'}), 403)
    return user, None


# ============================================================
# MODEL SCOPE RESOLUTION
#
# Models are trained per class (ml_models.teacher_id). A student may sit
# in several classes, so "whose model speaks for this student" has to be
# answered explicitly - and the answer travels with the response, because
# a pooled model presented as if it were the class's own model is exactly
# the misrepresentation this scoping exists to prevent.
#
# THE NEWEST-MODEL-WINS RULE, and what it costs:
#
# Two teachers whose classes overlap each train their own model, from
# slightly different student lists. A student in both can therefore get a
# slightly different answer depending on which class is used. Measured on
# the current data: of 66 students enrolled under both teachers, 3 sit on
# a tree boundary and get a different mastery label, 0 get a different
# profile name. (Raw cluster NUMBERS differ for all 66, but cluster
# numbering is arbitrary per model and is never shown to a user.)
#
# This is a deliberate trade-off, not a bug:
#   one pooled model  -> every student sees the same label, but each
#                        teacher's class figures are shaped by students
#                        they never taught
#   per-class models  -> 3 students may see a different badge, but each
#                        class figure really comes from that class
#
# A teacher's own page always uses that teacher's model; no teacher ever
# sees another class's numbers. Changing this rule is a product
# decision, not a cleanup: the options are to show both models side by
# side, or to let the teacher pick. See docs/ML_DOCUMENTATION.md 8.2.
# ============================================================
def _newest_class_record(student_id, model_type='decision_tree'):
    """Newest class-trained model OF THIS TYPE among the student's teachers.

    Resolved per model type on purpose. Mastery comes from the tree and
    grouping from K-Means, and the two are trained independently - one can
    be READY while the other is INSUFFICIENT_DATA. Picking the K-Means
    artifact with the tree's class would let a pooled (or another
    teacher's) cluster label ride under a class-scope note.
    """
    best = None
    for tid in analytics.student_teacher_ids(student_id):
        rec = model_manager.latest_record(
            model_type, tid, allow_pooled_fallback=False)
        if rec is None:
            continue
        # Newest wins; lowest teacher id breaks a tie so two classes
        # trained in the same second still resolve the same way every time.
        if best is None or (rec.trained_at, -rec.teacher_id) > (best.trained_at, -best.teacher_id):
            best = rec
    return best


_MODEL_LABEL = {
    'decision_tree': 'penguasaan (Decision Tree)',
    'kmeans': 'pengelompokan (K-Means)',
}


def _scope_info(teacher_id, model_type='decision_tree', available=True):
    """Human-readable statement of which model's numbers these are.

    Carries `model_type` because a profile can show two figures - a
    mastery label and a cluster name - from two different models, and each
    one has to be able to say where it came from.
    """
    what = _MODEL_LABEL.get(model_type, model_type)
    if not available:
        return {
            'scope': 'none',
            'teacher_id': None,
            'teacher_name': None,
            'model_type': model_type,
            'note': f'Model {what} belum tersedia.',
        }
    if teacher_id is None:
        return {
            'scope': 'pooled',
            'teacher_id': None,
            'teacher_name': None,
            'model_type': model_type,
            'note': (f'Angka {what} ini berasal dari model yang dilatih dari '
                     'seluruh siswa sistem, karena kelas Anda belum punya '
                     'model sendiri. Jadi ini belum khusus untuk kelas Anda.'),
        }
    teacher = User.query.get(teacher_id)
    return {
        'scope': 'class',
        'teacher_id': teacher_id,
        'teacher_name': teacher.name if teacher else None,
        'model_type': model_type,
        'note': (f'Model {what} ini dilatih dari siswa kelas '
                 f'{teacher.name if teacher else teacher_id} saja.'),
    }


def _load_for_student(student):
    """(dt, km, dt_scope, km_scope) for a student's profile.

    The tree and the clustering are chosen SEPARATELY so each figure's
    provenance is its own: a class K-Means is not denied because another
    class happened to train a newer tree, and a pooled K-Means is never
    reported as the student's class model. The pooled artifact is loaded
    explicitly (not as a silent fallback) only when the student's teachers
    have none of that model type, and `_scope_info` says which one it was.
    """
    dt_rec = _newest_class_record(student.id, 'decision_tree')
    km_rec = _newest_class_record(student.id, 'kmeans')
    dt_tid = dt_rec.teacher_id if dt_rec is not None else None
    km_tid = km_rec.teacher_id if km_rec is not None else None
    dt = (model_manager.load_artifact('decision_tree', teacher_id=dt_tid,
                                      allow_pooled_fallback=False)
          if dt_tid is not None else None)
    km = (model_manager.load_artifact('kmeans', teacher_id=km_tid,
                                      allow_pooled_fallback=False)
          if km_tid is not None else None)
    if dt is None:
        dt = model_manager.load_artifact('decision_tree', teacher_id=None)
        dt_tid = None
    if km is None:
        km = model_manager.load_artifact('kmeans', teacher_id=None)
        km_tid = None
    dt_scope = _scope_info(dt_tid, 'decision_tree', available=dt is not None)
    km_scope = _scope_info(km_tid, 'kmeans', available=km is not None)
    return dt, km, dt_scope, km_scope


# ============================================================
# STUDENT: learning profile & recommendations
# ============================================================
@jwt_required()
def get_student_learning_profile():
    user, err = _student()
    if err:
        return err
    dt_artifact, km_artifact, dt_scope, km_scope = _load_for_student(user)
    result = profile_mod.generate_profile(user, dt_artifact, km_artifact)
    result['model_scope'] = dt_scope
    result['cluster_scope'] = km_scope
    return jsonify(result), 200


@jwt_required()
def get_student_recommendations():
    user, err = _student()
    if err:
        return err
    dt_artifact, km_artifact, dt_scope, km_scope = _load_for_student(user)
    p = profile_mod.generate_profile(user, dt_artifact, km_artifact)
    p['model_scope'] = dt_scope
    p['cluster_scope'] = km_scope

    if p['status'] == cfg.STATUS_READY and p.get('summary'):
        row = feature_service.aggregate_student_features(user) or {}
        # No model_version is passed: the Decision Tree shaped the profile
        # label above, NOT the order of these materials. Stamping the
        # tree's version on a rule-ranked list implied otherwise.
        recommended = rec_service.recommend_for_student(user, student_row=row)
        return jsonify({'profile': p, 'status': cfg.STATUS_READY,
                        'recommendations': recommended,
                        'ranking_method': 'rule',
                        'model_scope': dt_scope,
                        'cluster_scope': km_scope}), 200

    fallback = rec_service.fallback_recommendations(user)
    return jsonify({'profile': p, 'status': p['status'],
                    'recommendations': fallback,
                    'ranking_method': 'fallback',
                    'mode': 'fallback',
                    'model_scope': dt_scope,
                    'cluster_scope': km_scope}), 200


@jwt_required()
def post_recommendation_click():
    user, err = _student()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    material_id = data.get('material_id')
    if not material_id:
        return jsonify({'error': 'material_id wajib diisi'}), 400
    from src.models.material import Material
    material = Material.query.get(int(material_id))
    if not material or material.status != 'published':
        return jsonify({'error': 'Materi tidak ditemukan atau belum dipublikasikan'}), 404
    try:
        rec_service.mark_clicked(user.id, material.id)
    except Exception:
        db.session.rollback()
    return jsonify({'message': 'Klik rekomendasi tercatat'}), 200


# ============================================================
# TEACHER/ADMIN: ML analytics (scoped to own students)
# ============================================================
# What a teacher is looking at, in one sentence, per scope. Rendered in
# the UI so nobody has to guess whether the numbers are their class's.
_SCOPE_NOTE = {
    'class': ('Model dilatih hanya dari siswa kelas Anda, jadi angka di '
              'halaman ini benar-benar menggambarkan kelas ini.'),
    'pooled': ('Kelas Anda belum punya model sendiri, jadi angka ini memakai '
               'model gabungan seluruh sistem. Baru jadi indikasi, bukan '
               'kesimpulan khusus kelas Anda.'),
    'none': ('Belum ada model yang bisa dipakai. Latih model dulu lewat '
             'tombol Training.'),
}


def _load_for_teacher(teacher):
    """(dt, km, scope, km_scope) for a teacher's own class view.

    `scope` describes the mastery model; `km_scope` describes the cluster
    model on its own, because a class can have a tree but no K-Means (or
    the K-Means can be the pooled fallback while the tree is the class's
    own). Each figure then says which model produced it.
    """
    if teacher.role == 'admin':
        # An admin owns no class. Show the pooled model and label it as
        # such rather than borrowing an arbitrary teacher's class model.
        dt = model_manager.load_artifact('decision_tree', teacher_id=None)
        km = model_manager.load_artifact('kmeans', teacher_id=None)
        return (dt, km, ('pooled' if dt else 'none'),
                _scope_info(None, 'kmeans', available=km is not None))
    dt = model_manager.load_artifact('decision_tree', teacher_id=teacher.id)
    km = model_manager.load_artifact('kmeans', teacher_id=teacher.id)
    scope = model_manager.resolve_scope('decision_tree', teacher.id)
    km_rec = model_manager.latest_record('kmeans', teacher.id)
    km_scope = _scope_info(km_rec.teacher_id if km_rec is not None else None,
                           'kmeans', available=km is not None)
    return dt, km, scope, km_scope


def _scope_message(analyzed, insufficient, total):
    """One honest sentence about how much of this class was analysable."""
    if not total:
        return ('Kelas Anda belum memiliki siswa terdaftar, sehingga belum '
                'ada yang bisa dianalisis.')
    if insufficient == 0:
        return (f'Semua {total} siswa kelas Anda punya data cukup untuk '
                'dianalisis.')
    return (f'{analyzed} dari {total} siswa kelas Anda punya data cukup. '
            f'{insufficient} siswa lainnya belum - ML tidak bisa menilai '
            'mereka tanpa data belajar yang sebenarnya.')


def _ml_insights(teacher):
    students = analytics.teacher_student_users(teacher.id)
    if not students:
        # This teacher currently has no students, so every class figure is
        # a hard zero rather than "not enough data". Saying only
        # "INSUFFICIENT_DATA" reads like a broken model when the real
        # cause is an empty class - a distinction worth making before
        # someone debugs the wrong thing.
        return {
            'signals': 0, 'analyzed': 0, 'insufficient_data': 0,
            'mastery_distribution': {}, 'profile_distribution': {},
            'top_recommendations': [], 'topics_needing_reinforcement': [],
            'model': None, 'clusters': None,
            'scope_status': 'NO_STUDENTS',
            'scope_message': (
                'Kelas Anda belum memiliki siswa yang terdaftar, sehingga '
                'belum ada yang bisa dianalisis. Tambahkan siswa ke kelas '
                ' terlebih dahulu.'),
        }

    dt_artifact, km_artifact, scope, _km_scope = _load_for_teacher(teacher)

    mastery_dist = {}
    profile_dist = {}
    insufficient = 0
    analyzed = 0
    # interpret_clusters() is the same for every student, so building it
    # once per request instead of once per student.
    profile_labels = (cluster_interpreter.interpret_clusters(km_artifact)
                      if km_artifact else [])

    for s in students:
        row = feature_service.aggregate_student_features(s)
        if row is None:
            insufficient += 1
            continue
        analyzed += 1
        if dt_artifact:
            label = decision_tree.predict_row(row, dt_artifact)[0]
            if label:
                mastery_dist[label] = mastery_dist.get(label, 0) + 1
        if km_artifact:
            cid = kmeans_mod.assign_cluster(row, km_artifact)
            if cid is not None:
                for prof in profile_labels:
                    if prof['cluster_id'] == cid:
                        profile_dist[prof['label']] = profile_dist.get(prof['label'], 0) + 1
                        break

    model_info = _model_info(teacher)
    if model_info is not None:
        # The class numbers below are this teacher's students; the model
        # behind them is either their own class model or, when the class is
        # too small to train one, the pooled fallback. Say which.
        model_info['training_scope'] = scope
        model_info['training_scope_note'] = _SCOPE_NOTE[scope]
        model_info['class_students'] = len(students)
        model_info['class_analyzed'] = analyzed
    clusters_info = _clusters_info(teacher)
    top_recommendations = _top_recommendations(teacher)
    topics = [t for t in analytics.teacher_topics(teacher.id)
              if t['mastery']['label'] in ('Kurang', 'Cukup')]
    topics.sort(key=lambda t: t['average_progress'])
    topics_needing = [{'topic': t['topic'], 'average_progress': t['average_progress'],
                       'mastery_label': t['mastery']['label'],
                       'materials': t['materials']} for t in topics[:5]]

    return {
        'signals': analyzed + insufficient,
        'analyzed': analyzed,
        'insufficient_data': insufficient,
        'mastery_distribution': mastery_dist,
        'profile_distribution': profile_dist,
        'top_recommendations': top_recommendations,
        'topics_needing_reinforcement': topics_needing,
        'model': model_info,
        'clusters': clusters_info,
        'scope_status': 'READY',
        'scope_message': _scope_message(analyzed, insufficient, len(students)),
    }


def _model_info(teacher):
    record = model_manager.latest_record('decision_tree', teacher.id)
    if not record:
        return None
    return {
        'status': cfg.STATUS_READY,
        'model_type': 'decision_tree',
        'model_version': record.model_version,
        'feature_version': record.feature_version,
        'trained_at': record.trained_at.isoformat() + 'Z' if record.trained_at else None,
        'training_sample_count': record.training_sample_count,
        # Which students the model was actually fitted on. Without this,
        # the class figures around it look like the class produced them.
        'trained_on': 'class' if record.teacher_id is not None else 'pooled',
        'trained_on_teacher_id': record.teacher_id,
        'metrics': record.metrics_json,
        'evaluation_note': (record.metrics_json or {}).get('evaluation_note'),
    }


def _clusters_info(teacher):
    info = model_manager.latest_record('kmeans', teacher.id)
    artifact = model_manager.load_artifact('kmeans', teacher_id=teacher.id)
    if not info or not artifact:
        return None
    profiles = cluster_interpreter.interpret_clusters(artifact)
    return {
        'status': cfg.STATUS_READY,
        'model_type': 'kmeans',
        'model_version': info.model_version,
        'trained_at': info.trained_at.isoformat() + 'Z' if info.trained_at else None,
        'trained_on': 'class' if info.teacher_id is not None else 'pooled',
        'trained_on_teacher_id': info.teacher_id,
        # The cluster names are ranked against THIS model's own centroids,
        # so "Active Learner" here is relative to this class and is not a
        # system-wide yardstick. Saying so prevents two classes' names
        # being read as directly comparable.
        'interpretation_scope': 'class' if info.teacher_id is not None else 'pooled',
        'interpretation_note': ('Nama klaster dinilai dari centroid model ini '
                                'sendiri (relatif terhadap kelas ini), jadi '
                                'tidak dimaksudkan untuk dibandingkan langsung '
                                'dengan nama klaster kelas lain.'),
        'training_scope': 'class' if info.teacher_id is not None else 'pooled',
        'training_scope_note': _SCOPE_NOTE['class' if info.teacher_id is not None else 'pooled'],
        'k': artifact.get('k'),
        'silhouette': artifact.get('silhouette'),
        'silhouettes': artifact.get('silhouettes'),
        'n_samples': artifact.get('sample_count'),
        'profiles': profiles,
        'silhouette_note': 'Nilai silhouette digunakan untuk melihat seberapa baik data terpisah dalam cluster.',
    }


def _top_recommendations(teacher):
    from src.models.recommendation import Recommendation
    student_ids = analytics.teacher_student_ids(teacher.id)
    if not student_ids:
        return []
    rows = Recommendation.query.filter(Recommendation.student_id.in_(student_ids)).all()
    agg = {}
    for r in rows:
        if not r.material:
            continue
        bucket = agg.setdefault(r.material_id, {'count': 0, 'score_sum': 0.0,
                                                'title': r.material.title,
                                                'topic': r.material.topic})
        bucket['count'] += 1
        bucket['score_sum'] += (r.recommendation_score or 0.0)
    out = []
    for mid, b in agg.items():
        out.append({'material_id': mid, 'title': b['title'], 'topic': b['topic'],
                    'count': b['count'],
                    'average_score': round(b['score_sum'] / b['count'], 4)})
    out.sort(key=lambda x: (-x['count'], -x['average_score']))
    return out[:5]


@jwt_required()
def get_teacher_ml_analytics():
    teacher, err = _teacher()
    if err:
        return err
    result = _ml_insights(teacher)
    return jsonify(result), 200


# ============================================================
# TRAINING / PREDICTION (protected, teacher/admin)
# ============================================================
def _all_students():
    return User.query.filter_by(role='student').all()


def _fit_one_scope(students, teacher_id, label):
    """Train + save DT and K-Means for exactly this set of students.

    `teacher_id` is the scope written to ml_models.teacher_id: a teacher
    id for that class, None for the pooled system-wide model.
    """
    rows = feature_service.build_dataset(students)
    result = {
        'scope': label,
        'teacher_id': teacher_id,
        'analysis_students': len(students),
        'dataset_rows': len(rows),
    }

    dt_payload = decision_tree.fit_from_rows(rows)
    km_payload = kmeans_mod.fit_from_rows(rows)

    if dt_payload.get('status') == cfg.STATUS_READY:
        meta = model_manager.save_artifact('decision_tree', dt_payload,
                                           teacher_id=teacher_id)
        result['decision_tree'] = {
            'status': cfg.STATUS_READY,
            'model_version': meta['model_version'],
            'metrics': dt_payload.get('metrics'),
            'evaluation_note': dt_payload.get('evaluation_note'),
            'training_sample_count': dt_payload.get('sample_count'),
        }
    else:
        result['decision_tree'] = {'status': dt_payload.get('status'),
                                   'message': dt_payload.get('message'),
                                   'samples': dt_payload.get('samples'),
                                   'min_required': dt_payload.get('min_required')}

    if km_payload.get('status') == cfg.STATUS_READY:
        meta = model_manager.save_artifact('kmeans', km_payload,
                                           teacher_id=teacher_id)
        result['kmeans'] = {'status': cfg.STATUS_READY,
                            'model_version': meta['model_version'],
                            'k': km_payload.get('k'),
                            'silhouette': km_payload.get('silhouette'),
                            'silhouettes': km_payload.get('silhouettes'),
                            'training_sample_count': km_payload.get('sample_count')}
    else:
        result['kmeans'] = {'status': km_payload.get('status'),
                            'message': km_payload.get('message'),
                            'samples': km_payload.get('samples'),
                            'min_required': km_payload.get('min_required')}
    return result


def _train_pipeline(actor):
    """Train models.

    A teacher trains their own class only. Training on everyone would let
    a teacher's class figures be shaped by students they have never seen,
    which is the thing per-class scoping exists to prevent.

    An admin trains the pooled fallback plus one model per teacher, so a
    single button leaves every class with its own model.
    """
    if actor.role == 'admin':
        pooled = _fit_one_scope(_all_students(), None, 'pooled')
        classes = []
        for t in sorted(User.query.filter_by(role='teacher').all(),
                        key=lambda u: u.id):
            students = analytics.teacher_student_users(t.id)
            entry = _fit_one_scope(students, t.id, t.name)
            entry['students_in_class'] = len(students)
            classes.append(entry)
        out = dict(pooled)
        out['scope'] = 'pooled'
        out['classes'] = classes
        out['trained_class_count'] = sum(
            1 for c in classes
            if c['decision_tree'].get('status') == cfg.STATUS_READY)
        return out

    students = analytics.teacher_student_users(actor.id)
    out = _fit_one_scope(students, actor.id, actor.name)
    # A copy, not `out` itself: nesting the same dict inside itself is a
    # circular reference and jsonify refuses to serialise it.
    out['classes'] = [dict(out)]
    out['students_in_class'] = len(students)
    out['trained_class_count'] = 1 if out['decision_tree'].get('status') == cfg.STATUS_READY else 0
    return out


@jwt_required()
def train_ml():
    actor, err = _teacher()
    if err:
        return err
    result = _train_pipeline(actor)
    # Mirror the payload under `details` as well. The teacher UI reads
    # `details.decision_tree`, which was never present in the response, so
    # the training result panel has been silently dead.
    return jsonify({**result, 'details': result}), 200


# ============================================================
# RETRAIN (alias of train — semantic re-use)
# ============================================================
@jwt_required()
def retrain_ml():
    actor, err = _teacher()
    if err:
        return err
    result = _train_pipeline(actor)
    return jsonify({**result, 'details': result}), 200


# ============================================================
# PREDICT single student (teacher/admin, must share a course)
# ============================================================
@jwt_required()
def predict_student(student_id):
    teacher, err = _teacher()
    if err:
        return err
    student = User.query.get(int(student_id)) if str(student_id).isdigit() else None
    if not student or student.role != 'student':
        return jsonify({'error': 'Siswa tidak ditemukan'}), 404
    # ownership check: student must be among teacher's own students
    my_student_ids = set(analytics.teacher_student_ids(teacher.id))
    if student.id not in my_student_ids:
        return jsonify({'error': 'Anda tidak memiliki akses ke data siswa ini'}), 403
    dt_artifact, km_artifact, scope, km_scope = _load_for_teacher(teacher)
    result = profile_mod.generate_profile(student, dt_artifact, km_artifact)
    result['model_scope'] = _scope_info(
        None if scope == 'pooled' else teacher.id)
    result['cluster_scope'] = km_scope
    return jsonify(result), 200


# ============================================================
# TEACHER ML ANALYTICS — mastery breakdown
# ============================================================
@jwt_required()
def get_teacher_ml_mastery():
    teacher, err = _teacher()
    if err:
        return err
    insights = _ml_insights(teacher)
    return jsonify({
        'mastery_distribution': insights['mastery_distribution'],
        'analyzed': insights['analyzed'],
        'insufficient_data': insights['insufficient_data'],
    }), 200


# ============================================================
# TEACHER ML ANALYTICS — cluster breakdown
# ============================================================
@jwt_required()
def get_teacher_ml_clusters():
    teacher, err = _teacher()
    if err:
        return err
    clusters = _clusters_info(teacher)
    if not clusters:
        return jsonify({'status': cfg.STATUS_MODEL_UNAVAILABLE, 'message': 'Model belum tersedia'}), 200
    return jsonify(clusters), 200


# ============================================================
# RECOMMENDATION CLOSED-LOOP EVALUATION (teacher/admin)
# Reads back clicked_at / completed_at that the recommendation layer
# already records, so REC_WEIGHTS can be judged on real outcomes
# instead of being taken on faith. Observational, never causal.
# ============================================================
@jwt_required()
def get_recommendation_evaluation():
    user, err = _teacher()
    if err:
        return err
    # admin sees the whole system; a teacher only sees their own students.
    scope_teacher = None if user.role == 'admin' else user
    return jsonify(rec_eval.evaluate_recommendations(teacher=scope_teacher)), 200