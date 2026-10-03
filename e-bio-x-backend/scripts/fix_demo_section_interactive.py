# -*- coding: utf-8 -*-
"""Perbaikan data demo: soal interaktif diletakkan di bagian yang cocok.

Seeder demo lama mengisi bagian secara POSISIONAL: dua soal interaktif pertama
kuis masuk ke bagian 1, dua berikutnya ke bagian 2, tanpa melihat isi soalnya.
Akibatnya ada soal yang salah kamar, mis. "Selubung protein virus disebut?"
(kapsid, jelas tentang STRUKTUR) duduk di bagian "Siklus Replikasi Virus".

Karena jawaban interaktif ikut menentukan skor penguasaan bagian, soal yang
salah kamar itu membuat skor satu bagian dibentuk oleh pertanyaan bagian lain.
Script ini MEMINDAHKAN soal interaktif (beserta jawabannya) supaya tiap bagian
hanya memuat soal yang benar-benar sesuai judulnya.

Prinsip yang dijaga:
  - TIDAK ada angka baru dan TIDAK ada jawaban yang dihapus. Setiap pasangan
    (soal, jawaban) yang sudah ada hanya berpindah bagian: jumlah jawaban dan
    `is_correct`-nya tidak berubah. Yang berubah hanya `content_id`,
    `question_index`, dan `section_id` pada baris jawaban.
  - Pemindahan ditulis eksplisit per bagian di `TARGETS` (urutan soal), bukan
    hasil pencocokan teks otomatis.
  - Validasi ketat: setiap soal target harus ada di kumpulan soal materi itu,
    dan setiap soal materi itu harus dipakai tepat sekali. Kalau tidak, script
    berhenti tanpa mengubah apa pun.
  - Idempoten: kalau susunan soal tiap bagian sudah sesuai target, tidak ada
    yang diubah.
  - Hanya menyentuh konten bertipe `interactive` pada bagian yang terdaftar.

Default: dry-run (tidak menulis). Gunakan --apply untuk menyimpan.

Contoh:
  python scripts/fix_demo_section_interactive.py
  python scripts/fix_demo_section_interactive.py --apply
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.material_content import MaterialContent  # noqa: E402
from src.models.student_answer import StudentAnswer  # noqa: E402

# section_id -> daftar teks soal interaktif, dalam urutan yang diinginkan.
# Soal ditulis lengkap supaya bisa diaudit tanpa membuka DB.
TARGETS = {
    # --- Materi 115 "[Demo] Sel dan Organel" ---
    67: [  # Pengenalan Sel: bagian/zat sel apa yang disebut apa.
        'Bagian sel yang mengontrol seluruh aktivitas sel adalah?',
        'Dinding sel pada tumbuhan tersusun atas?',
    ],
    68: [  # Organel dan Fungsinya: organel tertentu mengerjakan apa.
        'Organel tempat respirasi sel disebut?',
        'Proses makanan dicerna di dalam sel terjadi pada?',
    ],
    # --- Materi 116 "[Demo] Bakteri dan Peranannya" (sudah sesuai, ditulis
    #     ulang agar script tetap menyatakan susunan yang benar) ---
    69: [  # Ciri dan Struktur Bakteri
        'Bakteri berkembang biak dengan pembelahan binary fission pada kondisi?',
        'Bentuk bakteri berbentuk batang disebut?',
    ],
    70: [  # Peranan Bakteri
        'Zat yang dibuat oleh bakteri untuk melawan bakteri lain adalah?',
        'Kelompok bakteri penghasil asam dalam yoghurt adalah?',
    ],
    # --- Materi 117 "[Demo] Virus dan Replikasinya" ---
    # "Virus tidak dianggap organisme karena?" menyangkut sifat STRUKTURAL
    # (tidak memiliki sel), jadi diletakkan di bagian struktur, bukan dipaksa
    # ke bagian siklus.
    71: [  # Struktur Virus
        'Bahan genetik virus dapat berupa?',
        'Selubung protein virus disebut?',
        'Virus tidak dianggap organisme karena?',
    ],
    72: [  # Siklus Replikasi Virus
        'Siklus virus yang langsung memecah sel inang disebut siklus?',
    ],
}


def _norm(text):
    return ' '.join((text or '').split()).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='simpan perubahan (tanpa flag ini hanya laporan)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print('=' * 76)
        print('PERBAIKAN SOAL INTERAKTIF DEMO -> BAGIAN YANG COCOK')
        print('=' * 76)

        problems = []
        materials = {}
        for sid in TARGETS:
            sec = MaterialSection.query.get(sid)
            if not sec:
                problems.append(f'bagian {sid} tidak ada')
                continue
            materials.setdefault(sec.material_id, []).append(sid)

        plans = []  # (material_id, [(section_id, [question_dict, ...]), ...], moves)
        total_moves = 0
        for material_id, section_ids in materials.items():
            # Kumpulkan seluruh soal interaktif materi ini, beserta lokasinya.
            pool = {}   # normalized text -> (content, index, question dict, section_id)
            contents = {}
            for sec in MaterialSection.query.filter_by(
                    material_id=material_id).order_by(MaterialSection.position).all():
                for c in sec.contents:
                    if c.type != 'interactive':
                        continue
                    contents[c.id] = c
                    for i, q in enumerate((c.data or {}).get('questions') or []):
                        key = _norm(q.get('question'))
                        if not key:
                            problems.append(f'konten {c.id} indeks {i} tanpa teks soal')
                            continue
                        if key in pool:
                            problems.append(f'soal ganda di materi {material_id}: "{key}"')
                            continue
                        pool[key] = (c, i, q, sec.id)

            wanted = []
            for sid in TARGETS:
                sec = MaterialSection.query.get(sid)
                if not sec or sec.material_id != material_id:
                    continue
                wanted.append(sid)

            used = set()
            for sid in wanted:
                for text in TARGETS[sid]:
                    key = _norm(text)
                    if key not in pool:
                        problems.append(
                            f'bagian {sid}: soal "{key}" tidak ditemukan di materi '
                            f'{material_id}')
                        continue
                    if key in used:
                        problems.append(f'soal dipakai dua kali: "{key}"')
                        continue
                    used.add(key)

            leftover = [k for k in pool if k not in used]
            if leftover:
                problems.append(
                    f'materi {material_id}: {len(leftover)} soal tidak punya bagian '
                    f'tujuan: {leftover}')

            # Bangun rencana baru.
            new_questions = {}   # content_id -> [question dict, ...]
            remap = {}           # (old_content_id, old_index) -> (content_id, index, section_id)
            for sid in wanted:
                # Susun soal bagian ini, lalu simpan ke konten interaktif bagian itu.
                inter = [c for c in MaterialSection.query.get(sid).contents
                         if c.type == 'interactive']
                if not inter:
                    problems.append(f'bagian {sid} tidak punya konten interaktif')
                    continue
                content = inter[0]
                if len(inter) > 1:
                    problems.append(f'bagian {sid} punya >1 konten interaktif; '
                                    f'script ini hanya menata yang pertama')
                qs = []
                for text in TARGETS[sid]:
                    key = _norm(text)
                    if key not in pool:
                        continue
                    old_c, old_i, q, _old_sec = pool[key]
                    qs.append(q)
                    remap[(old_c.id, old_i)] = (content.id, len(qs) - 1, sid)
                new_questions[content.id] = qs

            plans.append((material_id, new_questions, remap))

        if problems:
            print('\nVALIDASI GAGAL - tidak ada yang diubah:')
            for p in problems:
                print(f'  - {p}')
            db.session.rollback()
            return 1

        # Susun daftar perpindahan dari keadaan AWAL, sebelum satu baris pun
        # dipindah, lalu kunci pada `id` barisnya. Kalau tidak, baris yang baru
        # dipindah bisa ikut terjaring oleh perpindahan berikutnya dan tertumpuk
        # di satu (konten, indeks).
        moves = []
        for material_id, new_questions, remap in plans:
            print(f'\n--- Materi {material_id} ---')
            for cid, qs in sorted(new_questions.items()):
                content = MaterialContent.query.get(cid)
                print(f'  konten {cid} (bagian {content.section_id}):')
                for i, q in enumerate(qs):
                    print(f'      {i}. {q.get("question","")[:60]}')
            for (old_c, old_i), (new_c, new_i, new_sec) in sorted(remap.items()):
                if (old_c, old_i) == (new_c, new_i):
                    continue
                ids = [r.id for r in StudentAnswer.query.filter_by(
                    content_id=old_c, question_index=old_i).all()]
                moves.append((ids, new_c, new_i, new_sec))
                total_moves += len(ids)
                print(f'  pindah: konten {old_c} idx {old_i} -> konten {new_c} '
                      f'idx {new_i} (bagian {new_sec}); {len(ids)} jawaban ikut')

        print(f'\nTotal jawaban yang berpindah bagian: {total_moves}')

        if args.apply:
            # 1. Pindahkan jawaban (berdasarkan id yang sudah dikunci).
            for ids, new_c, new_i, new_sec in moves:
                if not ids:
                    continue
                for row in StudentAnswer.query.filter(
                        StudentAnswer.id.in_(ids)).all():
                    row.content_id = new_c
                    row.question_index = new_i
                    row.section_id = new_sec
            # 2. Ganti daftar soal tiap konten (objek baru supaya terdeteksi).
            for _mid, new_questions, _remap in plans:
                for cid, qs in new_questions.items():
                    content = MaterialContent.query.get(cid)
                    content.data = {**(content.data or {}), 'questions': qs}
            db.session.commit()
            print('Diterapkan.')
        else:
            print('Mode dry-run, tidak ada yang disimpan (--apply untuk menyimpan).')
        print('-' * 76)
        return 0


if __name__ == '__main__':
    sys.exit(main())
