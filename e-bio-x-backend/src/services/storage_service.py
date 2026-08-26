# ============================================================
# Storage service - the ONLY module that talks to object storage.
#
# Providers (selected by STORAGE_PROVIDER):
#   supabase -> PRIVATE Supabase Storage bucket (production target)
#               REST API via requests; no supabase-py dependency.
#   r2       -> Cloudflare R2 (S3 API via boto3). KEPT for rollback
#               until Supabase is confirmed live; remove afterwards.
#   local    -> legacy uploads/ folder, development only. Never a
#               permanent storage target.
#
# MySQL stores portable /api/files/<key> urls only - never provider
# urls - so switching providers never invalidates the URL shape.
#
# Supabase env (see src/config/supabase_config.py):
#   SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / SUPABASE_STORAGE_BUCKET
# R2 env:
#   STORAGE_PROVIDER=r2 + R2_ACCOUNT_ID/R2_BUCKET/R2_ACCESS_KEY_ID/
#   R2_SECRET_ACCESS_KEY (+ optional R2_PRESIGN_EXPIRES)
# ============================================================
import os
import uuid

import requests as http_client
from flask import current_app
from werkzeug.utils import secure_filename

from src.config import supabase_config as sb_cfg


class StorageError(Exception):
    """Raised when the storage backend cannot complete an operation."""


def _scrub(msg):
    """Never let provider credentials travel inside error strings."""
    msg = str(msg or '')
    for secret in (sb_cfg.service_role_key(), _env('R2_SECRET_ACCESS_KEY'),
                   _env('R2_ACCESS_KEY_ID')):
        if secret:
            msg = msg.replace(secret, '[redacted]')
    return msg


URL_PREFIX = '/api/files/'

_CONTENT_TYPES = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'txt': 'text/plain',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'webp': 'image/webp',
    'gif': 'image/gif',
    'mp4': 'video/mp4',
}


def _env(name, default=None):
    try:
        return current_app.config.get(name) or os.environ.get(name) or default
    except Exception:
        return os.environ.get(name) or default


def active_provider():
    """Selected AND fully configured provider; falls back to 'local'."""
    chosen = (_env('STORAGE_PROVIDER') or '').lower()
    if chosen == 'supabase' and sb_cfg.is_configured():
        return 'supabase'
    if chosen == 'r2':
        if _env('R2_ACCOUNT_ID') and _env('R2_BUCKET') \
                and _env('R2_ACCESS_KEY_ID') and _env('R2_SECRET_ACCESS_KEY'):
            return 'r2'
    return 'local'


def content_type_for(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return _CONTENT_TYPES.get(ext, 'application/octet-stream')


def object_key(category, teacher_id, filename):
    """Unique, teacher-scoped key. Original name is kept only after a
    uuid prefix so collisions are impossible.

      supabase:  materials/teacher/15/<uuid>_materi.pdf   (bucket = root)
      r2/local:  e-bio-x/materials/teacher/71/<uuid>_materi.pdf
    """
    original = secure_filename(filename or '') or 'file'
    unique = f"{uuid.uuid4().hex}_{original}"
    prefix = '' if active_provider() == 'supabase' else 'e-bio-x/'
    if teacher_id is not None:
        return f"{prefix}{category}/teacher/{teacher_id}/{unique}"
    return f"{prefix}{category}/{unique}"


# ------------------------------------------------------------------
# Supabase Storage (REST)
# ------------------------------------------------------------------

def _sb_headers(extra=None):
    key = sb_cfg.service_role_key()
    h = {
        # new-style keys (sb_secret_...) require the apikey header;
        # legacy JWTs accept both, so always send it
        'apikey': key,
        'Authorization': f'Bearer {key}',
        **(extra or {}),
    }
    return h


def _sb_object_url(key):
    return f"{sb_cfg.supabase_url()}/storage/v1/object/{sb_cfg.bucket()}/{key}"


def _sb_upload(key, data, content_type):
    resp = http_client.post(
        _sb_object_url(key), data=data,
        headers=_sb_headers({'Content-Type': content_type or content_type_for(key)}),
        timeout=120,
    )
    if resp.status_code not in (200, 201):
        raise StorageError(f'Supabase upload gagal (HTTP {resp.status_code})')


def _sb_get(key):
    resp = http_client.get(_sb_object_url(key), headers=_sb_headers(), timeout=60)
    if resp.status_code == 200:
        return resp.content
    # storage quirk: a missing object arrives as HTTP 400 whose BODY
    # carries statusCode 404 / NoSuchKey
    if resp.status_code in (400, 404) and (
            'NoSuchKey' in resp.text or '"404"' in resp.text or 'not_found' in resp.text):
        return None
    raise StorageError(f'Supabase read gagal (HTTP {resp.status_code})')


def _sb_delete(key):
    # NOTE: no Content-Type json header here - a JSON content-type with an
    # empty body is rejected by the storage API (400 InvalidRequest)
    resp = http_client.delete(_sb_object_url(key), headers=_sb_headers(), timeout=60)
    # 200 deleted, 404 already gone - both count as clean
    if resp.status_code in (200, 204, 404):
        return True
    raise StorageError(f'Supabase delete gagal (HTTP {resp.status_code})')


def _sb_exists(key):
    parent, _, name = key.rpartition('/')
    resp = http_client.post(
        f"{sb_cfg.supabase_url()}/storage/v1/object/list/{sb_cfg.bucket()}",
        json={'prefix': f'{parent}/' if parent else '', 'search': name, 'limit': 1},
        headers=_sb_headers({'Content-Type': 'application/json'}),
        timeout=30,
    )
    if resp.status_code != 200:
        return False
    try:
        items = resp.json() or []
    except ValueError:
        return False
    return any(item.get('name') == name for item in items)


def _sb_signed_url(key, expires):
    resp = http_client.post(
        f"{sb_cfg.supabase_url()}/storage/v1/object/sign/{sb_cfg.bucket()}/{key}",
        json={'expiresIn': int(expires)},
        headers=_sb_headers({'Content-Type': 'application/json'}),
        timeout=30,
    )
    if resp.status_code != 200:
        return URL_PREFIX + key  # graceful fallback to authenticated proxy
    path = (resp.json() or {}).get('signedURL') or ''
    if path.startswith('/'):
        return f"{sb_cfg.supabase_url()}/storage/v1{path}"
    if path.startswith('http'):
        return path
    return URL_PREFIX + key


# ------------------------------------------------------------------
# R2 / S3 (rollback provider)
# ------------------------------------------------------------------

def _client():
    if active_provider() != 'r2':
        raise StorageError('Storage R2 belum dikonfigurasi')
    try:
        import boto3
    except ImportError as e:
        raise StorageError('boto3 tidak terpasang di server') from e
    account = _env('R2_ACCOUNT_ID')
    return boto3.client(
        's3',
        endpoint_url=f'https://{account}.r2.cloudflarestorage.com',
        aws_access_key_id=_env('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=_env('R2_SECRET_ACCESS_KEY'),
        region_name='auto',
    )


def _bucket():
    return _env('R2_BUCKET')


def _local_path(key):
    folder = current_app.config.get('UPLOAD_FOLDER') if current_app else None
    if not folder:
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), '..', 'uploads')
    return os.path.join(folder, os.path.basename(key))


# ------------------------------------------------------------------
# Core operations (provider-agnostic)
# ------------------------------------------------------------------

def put_bytes(key, data, content_type=None):
    provider = active_provider()
    try:
        if provider == 'supabase':
            _sb_upload(key, data, content_type or content_type_for(key))
        elif provider == 'r2':
            _client().put_object(
                Bucket=_bucket(), Key=key, Body=data,
                ContentType=content_type or content_type_for(key),
            )
        else:
            os.makedirs(os.path.dirname(_local_path(key)), exist_ok=True)
            with open(_local_path(key), 'wb') as f:
                f.write(data)
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f'Gagal mengunggah ke storage: {_scrub(e)}') from e
    return key


def get_bytes(key):
    provider = active_provider()
    try:
        if provider == 'supabase':
            return _sb_get(key)
        if provider == 'r2':
            resp = _client().get_object(Bucket=_bucket(), Key=key)
            return resp['Body'].read()
        path = _local_path(key)
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as f:
            return f.read()
    except StorageError:
        raise
    except Exception:
        return None


def exists(key):
    provider = active_provider()
    try:
        if provider == 'supabase':
            return _sb_exists(key)
        if provider == 'r2':
            _client().head_object(Bucket=_bucket(), Key=key)
            return True
        return os.path.exists(_local_path(key))
    except Exception:
        return False


def delete_key(key):
    if not key:
        return False
    deleted = False
    provider = active_provider()
    try:
        if provider == 'supabase':
            deleted = _sb_delete(key)
        elif provider == 'r2':
            _client().delete_object(Bucket=_bucket(), Key=key)
            deleted = True
    except StorageError as e:
        print('Storage delete failed:', _scrub(e))
    except Exception as e:
        print('Storage delete failed:', _scrub(e))
    # legacy local copy cleanup (old uploads / local provider)
    try:
        path = _local_path(key)
        if os.path.exists(path):
            os.remove(path)
            deleted = True
    except Exception:
        pass
    return deleted


def presigned_get(key, expires=None):
    """Short-lived signed URL for <img>/<video>/download tags."""
    if not key:
        return None
    if expires is None:
        expires = sb_cfg.presign_expires() \
            if active_provider() == 'supabase' else 7200
    if active_provider() == 'supabase':
        return _sb_signed_url(key, expires)
    if active_provider() == 'r2':
        try:
            return _client().generate_presigned_url(
                'get_object',
                Params={'Bucket': _bucket(), 'Key': key},
                ExpiresIn=int(_env('R2_PRESIGN_EXPIRES', str(expires))),
            )
        except Exception:
            return URL_PREFIX + key
    return URL_PREFIX + key


# ------------------------------------------------------------------
# URL helpers (portable URLs stored in MySQL)
# ------------------------------------------------------------------

def public_url(key):
    """Canonical portable form stored in the database."""
    return URL_PREFIX + key


def resolve_key(url):
    """Extract the storage key from any url shape we have ever stored.

    Handles: /api/files/<key>, {host}/api/files/<key>,
             /uploads/<name>, {host}/uploads/<name>,
             Supabase signed/public URLs.
    Returns None for foreign urls.
    """
    if not url:
        return None
    u = str(url).split('?')[0]
    for marker in (URL_PREFIX, '/uploads/'):
        idx = u.find(marker)
        if idx != -1:
            tail = u[idx + len(marker):].lstrip('/')
            return tail or None
    # Supabase signed URL: .../object/sign/<bucket>/<key>
    # Supabase public URL: .../object/public/<bucket>/<key>
    if 'supabase' in u and '/object/' in u:
        for marker in ('/object/sign/', '/object/public/'):
            idx = u.find(marker)
            if idx != -1:
                # Skip bucket name, extract key
                rest = u[idx + len(marker):]
                parts = rest.split('/', 1)
                if len(parts) == 2:
                    return parts[1] or None
    return None


def out_url(url):
    """Serialize stored url for API responses: re-sign via signed GET
    so browser media tags work without headers.
    Handles /api/files/, /uploads/, and Supabase signed/public URLs.
    Legacy /uploads urls are returned unchanged."""
    key = resolve_key(url)
    if key:
        if str(url).strip().startswith('/uploads/'):
            return url
        return presigned_get(key)
    return url


def delete_url(url):
    """Delete whatever object a stored url points at (any era of urls)."""
    key = resolve_key(url)
    if key:
        return delete_key(key)
    return False

