# ============================================================
# Storage service - Cloudflare R2 (S3-compatible) with a local
# dev fallback. The ONLY module that talks to object storage.
#
# Providers:
#   r2    -> permanent storage in a PRIVATE Cloudflare R2 bucket
#   local -> legacy uploads/ folder, development only
#
# Credentials live exclusively in environment variables:
#   STORAGE_PROVIDER=r2
#   R2_ACCOUNT_ID=...
#   R2_BUCKET=...
#   R2_ACCESS_KEY_ID=...
#   R2_SECRET_ACCESS_KEY=...
#   R2_PRESIGN_EXPIRES=7200   (optional, seconds)
# ============================================================
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename


class StorageError(Exception):
    """Raised when the storage backend cannot complete an operation."""


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
    """'r2' when selected AND fully configured, otherwise 'local'."""
    if (_env('STORAGE_PROVIDER', '').lower() == 'r2'
            and _env('R2_ACCOUNT_ID') and _env('R2_BUCKET')
            and _env('R2_ACCESS_KEY_ID') and _env('R2_SECRET_ACCESS_KEY')):
        return 'r2'
    return 'local'


def content_type_for(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return _CONTENT_TYPES.get(ext, 'application/octet-stream')


def object_key(category, teacher_id, filename):
    """e-bio-x/materials/teacher/71/ab12..._materi.pdf
    (teacher segment omitted when teacher_id is unknown)"""
    original = secure_filename(filename or '') or 'file'
    unique = f"{uuid.uuid4().hex}_{original}"
    if teacher_id is not None:
        return f"e-bio-x/{category}/teacher/{teacher_id}/{unique}"
    return f"e-bio-x/{category}/{unique}"


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
# Core operations
# ------------------------------------------------------------------

def put_bytes(key, data, content_type=None):
    provider = active_provider()
    try:
        if provider == 'r2':
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
        raise StorageError(f'Gagal mengunggah ke storage: {e}') from e
    return key


def get_bytes(key):
    try:
        if active_provider() == 'r2':
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
    try:
        if active_provider() == 'r2':
            _client().head_object(Bucket=_bucket(), Key=key)
            return True
        return os.path.exists(_local_path(key))
    except Exception:
        return False


def delete_key(key):
    if not key:
        return False
    deleted = False
    try:
        if active_provider() == 'r2':
            _client().delete_object(Bucket=_bucket(), Key=key)
            deleted = True
    except Exception:
        deleted = False
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
    """Short-lived authenticated URL for <img>/<video>/download tags."""
    if not key:
        return None
    if expires is None:
        try:
            expires = int(_env('R2_PRESIGN_EXPIRES', '7200'))
        except ValueError:
            expires = 7200
    if active_provider() == 'r2':
        try:
            return _client().generate_presigned_url(
                'get_object',
                Params={'Bucket': _bucket(), 'Key': key},
                ExpiresIn=expires,
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
             /uploads/<name>, {host}/uploads/<name>.
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
    return None


def out_url(url):
    """Serialize stored url for API responses: swap /api/files/<key>
    with a presigned GET so browser media tags work without headers.
    Legacy /uploads urls are returned unchanged."""
    key = resolve_key(url)
    if key and str(url).lstrip().startswith((URL_PREFIX, 'http')) \
            and '/api/files/' in str(url):
        return presigned_get(key)
    return url


def delete_url(url):
    """Delete whatever object a stored url points at (any era of urls)."""
    key = resolve_key(url)
    if key:
        return delete_key(key)
    return False
