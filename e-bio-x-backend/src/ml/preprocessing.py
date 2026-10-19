# ============================================================
# TAHAP 5 - Preprocessing.
#
# ONE scaler is fitted on the training data and then persisted.
# Prediction reuses the exact same scaler + feature order, so the
# preprocessing never differs between training and prediction.
# ============================================================
import numpy as np
from sklearn.preprocessing import StandardScaler

from src.ml import ml_config as cfg


def impute_row(row):
    """Fill missing/null with 0 (a neutral value for these features)."""
    return {f: (row.get(f) if row.get(f) is not None else 0.0) for f in cfg.FEATURES}


def normalize_row(row):
    """Turn a feature dict into a numeric list aligned to cfg.FEATURES."""
    r = impute_row(row)
    return [float(r[f]) for f in cfg.FEATURES]


def normalize_subset(row, subset):
    """Normalize for a feature subset (e.g. K-Means) keeping order stable.

    Sebuah fitur yang tercatat di artefak LAMA tapi sudah tidak ada di
    cfg.FEATURES saat ini dibaca sebagai 0.0, bukan membuat KeyError.
    Artefak yang dilatih sebelum feature_version 1.1 masih membawa
    `interactive_accuracy` di subset tersimpannya; kolom itu kini sudah tidak
    ada di baris mana pun, dan nilainya memang 0.0 untuk semua siswa, jadi
    0.0 mereproduksi persis apa yang selalu dilihat model itu. Ini sejalan
    dengan decision_tree._vector yang sejak awal membaca fitur yang hilang
    sebagai 0.0.

    Tanpa pengaman ini, assign_cluster melempar KeyError pada artefak v1.0
    dan meruntuhkan halaman profil siswa - kegagalan yang tidak terlihat
    sampai deploy, dan bukan gejala "model perlu dilatih ulang" yang bisa
    dimengerti pengguna.
    """
    r = impute_row(row)
    return [float(r.get(f, 0.0)) for f in subset]


class Preprocessor:
    """Holds the fitted scaler and the exact feature order used."""

    def __init__(self, scaler=None, feature_order=None):
        self.scaler = scaler if scaler is not None else StandardScaler()
        self.feature_order = feature_order or list(cfg.FEATURES)

    def fit(self, X):
        self.scaler.fit(np.asarray(X, dtype=float))
        return self

    def transform(self, X):
        return self.scaler.transform(np.asarray(X, dtype=float))

    def assets(self):
        return {'scaler': self.scaler, 'feature_order': self.feature_order}