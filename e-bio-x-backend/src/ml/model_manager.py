# ============================================================
# TAHAP 5 - Model storage & versioning.
#
# Training is a SEPARATE step from prediction. Models are stored
# on disk (joblib) with a version + metadata row in `ml_models`,
# so the web app never retrains on a request.
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


def _artifact_path(model_type, version):
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', f'{model_type}_v{version}')
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


def save_artifact(model_type, payload, feature_version=None):
    version = next_version(model_type)
    path = _artifact_path(model_type, version)
    payload = dict(payload)
    payload['_meta'] = {
        'model_type': model_type,
        'model_version': version,
        'feature_version': feature_version or cfg.DEFAULT_FEATURE_VERSION,
        'trained_at': datetime.utcnow().isoformat(),
        'saved_at': path,
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
    )
    db.session.add(record)
    db.session.commit()
    _clear()
    return payload['_meta']


def latest_record(model_type):
    return MlModel.query.filter_by(model_type=model_type).order_by(
        MlModel.trained_at.desc(), MlModel.id.desc()).first()


@lru_cache(maxsize=16)
def _cached_load(path):
    return joblib.load(path)


def load_artifact(model_type, version=None):
    """Load latest (or specific) artifact. Cached to avoid disk IO per request."""
    if version is None:
        record = latest_record(model_type)
        if not record:
            return None
        version = record.model_version
    path = _artifact_path(model_type, version)
    if not os.path.exists(path):
        return None
    return _cached_load(path)


def _clear():
    _cached_load.cache_clear()


def list_models():
    rows = MlModel.query.order_by(MlModel.trained_at.desc()).all()
    return [{
        'model_type': r.model_type,
        'model_version': r.model_version,
        'feature_version': r.feature_version,
        'trained_at': r.trained_at.isoformat() + 'Z' if r.trained_at else None,
        'training_sample_count': r.training_sample_count,
        'metrics': r.metrics_json,
        'model_path': r.model_path,
    } for r in rows]