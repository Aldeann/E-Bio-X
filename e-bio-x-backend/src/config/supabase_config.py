# ============================================================
# Centralized Supabase Storage configuration.
# The ONLY module allowed to read SUPABASE_* credentials.
# Values never leave the backend; never log them.
#
# Required environment variables (see .env.example):
#   SUPABASE_URL              e.g. https://xxxx.supabase.co
#   SUPABASE_SERVICE_ROLE_KEY service-role secret (backend only!)
#   SUPABASE_STORAGE_BUCKET   default: e-bio-x-materials
# ============================================================
import os

from flask import current_app

DEFAULT_BUCKET = 'e-bio-x-materials'


def _get(name):
    try:
        return current_app.config.get(name) or os.environ.get(name) or None
    except Exception:
        return os.environ.get(name) or None


def supabase_url():
    return (_get('SUPABASE_URL') or '').rstrip('/')


def service_role_key():
    return _get('SUPABASE_SERVICE_ROLE_KEY')


def bucket():
    return _get('SUPABASE_STORAGE_BUCKET') or DEFAULT_BUCKET


def is_configured():
    return bool(supabase_url() and service_role_key() and bucket())


def presign_expires():
    try:
        return int(_get('SUPABASE_SIGNED_URL_EXPIRES') or 7200)
    except ValueError:
        return 7200
