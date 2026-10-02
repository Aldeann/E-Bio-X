# -*- coding: utf-8 -*-
"""Fase 3d: menandai soal bank lama sebagai latihan di bagian yang tepat.

Soal bank bawaan demo (seed lama) tidak punya `section_id`: saat itu fitur ini
belum ada. Script ini menautkannya SECARA EKSPLISIT ke bagian yang benar-benar
membahas isi soal tersebut, supaya siswa punya latihan di lebih dari satu bagian
dan lebih dari satu materi.

Aturan yang dijaga script ini:
  - Tautan ditulis sebagai daftar (bank_question_id, section_id) di bawah.
    Tidak ada pencocokan judul/topik otomatis: penentuan bagian adalah
    keputusan guru, bukan hasil tebakan teks.
  - `topic` mengikuti judul bagian setelah ditautkan (perilaku yang sama
    dengan form soal bank), jadi keduanya tidak bisa melenceng.
  - Skrip TIDAK menyetujui apa pun. Status soal tetap seperti semula:
    guru yang memutuskan.
  - Idempoten: menautkan soal yang sudah tertaut ke bagian yang sama
    tidak melakukan perubahan.

Default: dry-run (tidak menulis). Gunakan --apply untuk menyimpan.

Contoh:
  python scripts/tag_demo_practice_sections.py
  python scripts/tag_demo_practice_sections.py --apply
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.question_bank import QuestionBank  # noqa: E402

# (bank_question_id, section_id, alasan)
LINKS = [
    (7, 50, 'soal ini menanyakan struktur tubuh virus; bagian 50 membahas '
            'bagian-bagian virus'),
    (9, 50, 'kapsid melindungi materi genetik; bagian 50 membahas '
            'struktur virus'),
    (10, 50, 'materi genetik virus adalah bagian dari strukturnya; bagian 50'),
    (11, 63, 'pertanyaan tentang virus tidak bisa bereproduksi sendiri; bagian 63 '
             'membahas cara virus berkembang biak'),
    (13, 59, 'hewan khas Indonesia per wilayah; bagian 59 membahas kekayaan '
             'keanekaragaman hayati Indonesia'),
    (16, 61, 'manfaat keanekaragaman hayati sebagai bahan pangan/sandang/papan; '
             'bagian 61 membahas pemanfaatan dan pelestarian'),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='simpan perubahan (tanpa flag ini hanya laporan)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        changed, skipped, problems = 0, 0, []
        print('=' * 70)
        print('TAUTAN SOAL BANK -> BAGIAN MATERI (Fase 3d)')
        print('=' * 70)

        for bq_id, sec_id, reason in LINKS:
            bq = QuestionBank.query.get(bq_id)
            sec = MaterialSection.query.get(sec_id)
            if not bq:
                problems.append(f'soal bank {bq_id} tidak ada')
                continue
            if not sec:
                problems.append(f'bagian {sec_id} tidak ada')
                continue

            label = f'#{bq_id} "{bq.question_text[:52]}" -> bagian {sec_id} "{sec.title}"'
            if bq.section_id == sec.id:
                skipped += 1
                print(f'[LEWAT ] {label} (sudah tertaut)')
                continue

            print(f'[TAUT  ] {label}\n         alasan: {reason}')
            if args.apply:
                bq.section_id = sec.id
                bq.topic = sec.title
                changed += 1
            else:
                changed += 1

        if problems:
            print('\nPERHATIAN:')
            for p in problems:
                print(f'  - {p}')

        db.session.commit() if args.apply else db.session.rollback()

        print('\n' + '-' * 70)
        print(f'diubah/tundial: {changed} | sudah benar: {skipped} | '
              f'perlu diperbaiki manual: {len(problems)}')
        if not args.apply:
            print('mode dry-run, tidak ada yang disimpan (--apply untuk menyimpan)')
        print('-' * 70)
        return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())