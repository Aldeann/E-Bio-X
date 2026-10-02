# ============================================================
# TAHAP 5 - Model storage & versioning.
#
# Training is a SEPARATE step from prediction. Models are stored
# on disk (joblib) with a version + metadata row in `ml_models`,
# so the web app never retrains on a request.
#
# SCOPING: every model belongs to exactly one scope.
#   teacher_id = <id>  trained from that teacher's students only, so the
#                     class figures describe that class and nobody else's.
#   teacher_id = NULL   pooled model from every student in the system.
#                     A fallback for classes too small to train their own;
#                     anything read from it is labelled as such.
#
# Version numbers stay on one monotonic counter across all scopes. Two
# models with the same version string would make "which model produced
# this number?" ambiguous, and per-scope counters would leave a teacher
# looking like they are on v1.0 while the system is on v13.0.
# ============================================================
import os
import re
import joblib
from datetime import datetime
from functools import lru_cache

from src.config.database import db
from src.models.ml_model import MlModel
from src.ml import ml_config as cfg


def _ensure_dir():
    os.makedirs(cfg.MODEL_DIR, exist_ok=True)
    return cfg.MODEL_DIR


def scope_tag(teacher_id):
    """Filename fragment that keeps each class's artifact separate."""
    return '' if teacher_id is None else f'class{teacher_id}_'


def _artifact_path(model_type, version, teacher_id=None):
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_',
                  f'{model_type}_{scope_tag(teacher_id)}v{version}')
    return os.path.join(_ensure_dir(), f'{safe}.joblib')


def next_version(model_type):
    """Monotonic version for a model type (increments each retrain)."""
    rows = MlModel.query.filter_by(model_type=model_type).with_entities(MlModel.model_version).all()
    majors = []
    for (v,) in rows:
        m = re.match(r'^(\d+)', v or '')
        if m:
            majors.append(int(m.group(1)))
    n = (max(majors) if majors else 0) + 1
    return f'{n}.0'


def save_artifact(model_type, payload, feature_version=None, teacher_id=None):
    version = next_version(model_type)
    path = _artifact_path(model_type, version, teacher_id)
    payload = dict(payload)
    payload['_meta'] = {
        'model_type': model_type,
        'model_version': version,
        'feature_version': feature_version or cfg.DEFAULT_FEATURE_VERSION,
        'trained_at': datetime.utcnow().isoformat(),
        'saved_at': path,
        'teacher_id': teacher_id,
        'scope': 'pooled' if teacher_id is None else 'class',
    }
    joblib.dump(payload, path)

    record = MlModel(
        model_type=model_type,
        model_version=version,
        feature_version=feature_version or cfg.DEFAULT_FEATURE_VERSION,
        trained_at=datetime.utcnow(),
        training_sample_count=payload.get('meta', {}).get('sample_count') or payload.get('sample_count') or 0,
        metrics_json=payload.get('metrics'),
        model_path=path,
        teacher_id=teacher_id,
    )
    db.session.add(record)
    db.session.commit()
    _clear()
    prune_old_versions(model_type, teacher_id)
    return payload['_meta']


def prune_old_versions(model_type, teacher_id=None, keep=None):
    """Drop versions beyond the retention window for one scope.

    Scoped deliberately: a busy class must not be able to delete the model
    a quiet class depends on, and the two never share a filename.

    The file is removed only after its row is gone, so a failed unlink
    leaves an orphaned file (harmless) rather than a row pointing at
    nothing (which would make that version unloadable).
    """
    keep = keep or cfg.KEEP_VERSIONS_PER_SCOPE
    if keep < 1:
        return []
    stale = (MlModel.query
             .filter(MlModel.model_type == model_type,
                     MlModel.teacher_id == teacher_id)
             .order_by(MlModel.trained_at.desc(), MlModel.id.desc())
             .all())
    doomed = stale[keep:]
    paths = []
    for rec in doomed:
        if rec.model_path:
            paths.append(rec.model_path)
        db.session.delete(rec)
    if doomed:
        db.session.commit()
        for p in paths:
            try:
                # A shared path would mean two rows claim one file; keep
                # it rather than break the other scope.
                still_used = MlModel.query.filter_by(model_path=p).first()
                if still_used is None and os.path.exists(p):
                    os.remove(p)
            except OSError:
                # A locked or already-removed file must not abort a
                # training run that has already committed.
                pass
    return [r.model_version for r in doomed]


def latest_record(model_type, teacher_id=None, allow_pooled_fallback=True):
    """Newest record for a scope.

    Prefers the requested class. When that class has never been trained,
    `allow_pooled_fallback` decides whether to hand back the pooled model
    instead - callers are expected to report which one they got, because
    a pooled model silently presented as a class model is exactly the
    misrepresentation this scoping exists to prevent.
    """
    record = MlModel.query.filter_by(model_type=model_type, teacher_id=teacher_id).order_by(
        MlModel.trained_at.desc(), MlModel.id.desc()).first()
    if record is not None:
        return record
    if teacher_id is not None and allow_pooled_fallback:
        return MlModel.query.filter_by(model_type=model_type, teacher_id=None).order_by(
            MlModel.trained_at.desc(), MlModel.id.desc()).first()
    return None


def resolve_scope(model_type, teacher_id=None, allow_pooled_fallback=True):
    """Which scope a load would actually return: 'class' | 'pooled' | 'none'.

    Separate from load_artifact so a caller can label the answer without
    having to load the artifact just to find out.
    """
    record = latest_record(model_type, teacher_id, allow_pooled_fallback)
    if record is None:
        return 'none'
    return 'pooled' if record.teacher_id is None else 'class'


@lru_cache(maxsize=32)
def _cached_load(path):
    return joblib.load(path)


def load_artifact(model_type, version=None, teacher_id=None, allow_pooled_fallback=True):
    """Load latest (or specific) artifact. Cached to avoid disk IO per request."""
    if version is None:
        record = latest_record(model_type, teacher_id, allow_pooled_fallback)
        if record is None:
            return None
    else:
        q = MlModel.query.filter_by(model_type=model_type, model_version=version)
        if teacher_id is not None:
            q = q.filter(MlModel.teacher_id == teacher_id)
        record = q.order_by(MlModel.id.desc()).first()
        if record is None:
            path = _artifact_path(model_type, version, teacher_id)
            return _cached_load(path) if os.path.exists(path) else None

    path = record.model_path or _artifact_path(
        model_type, record.model_version, record.teacher_id)
    if not path or not os.path.exists(path):
        return None
    return _cached_load(path)


def _clear():
    _cached_load.cache_clear()


def list_models(teacher_id=None, include_all=False):
    q = MlModel.query
    if not include_all:
        if teacher_id is None:
            q = q.filter(MlModel.teacher_id.is_(None))
        else:
            q = q.filter(MlModel.teacher_id == teacher_id)
    rows = q.order_by(MlModel.trained_at.desc()).all()
    return [{
        'model_type': r.model_type,
        'model_version': r.model_version,
        'feature_version': r.feature_version,
        'trained_at': r.trained_at.isoformat() + 'Z' if r.trained_at else None,
        'training_sample_count': r.training_sample_count,
        'metrics': r.metrics_json,
        'model_path': r.model_path,
        'teacher_id': r.teacher_id,
        'scope': 'pooled' if r.is_pooled else 'class',
    } for r in rows]