# -*- coding: utf-8 -*-
"""Perbaikan sekali jalan: memisahkan jawaban interaktif yang tertumpuk.

`scripts/fix_demo_section_interactive.py` versi pertama memindahkan baris
sambil membaca ulang DB di tengah proses, sehingga baris yang baru dipindah
ikut terpindah lagi. Akibatnya dua kelompok jawaban tertumpuk di satu
(konten, indeks):

  - konten 211 idx 0  (bagian 68) berisi jawaban soal mitokondria (172)
    BERCAMPUR jawaban soal dinding sel (173)  -> 97 baris, harusnya 62
  - konten 219 idx 0  (bagian 72) berisi jawaban soal litik (191)
    BERCAMPUR jawaban soal bahan genetik (192) -> 126 baris, harusnya 63

Daftar soal tiap konten sudah benar; hanya baris jawabannya yang salah kamar.

Cara memisahkan (bukan menebak):
  - Seeder `seed_ml_activity.py` menyisipkan jawaban satu siswa berurutan
    mengikuti urutan bagian lalu urutan soal. Jadi untuk satu siswa, baris
    yang lebih dulu (id lebih kecil) adalah soal yang lebih dulu di daftar.
    Pada dua konten di atas, soal yang lebih dulu adalah soal SUMBER, dan
    yang lebih akhir adalah soal TUJUAN. Karena bagian yang dipelajari selalu
    prefiks (bagian 2 hanya dipelajari bila bagian 1 sudah), setiap siswa yang
    muncul punya tepat dua baris di situ.
  - Diperkuat lagi oleh invarian seeder: nilai `is_correct` SELALU sama
    dengan `(selected_answer == correct_answer)` untuk soal yang benar-benar
    dijawab. Script ini memverifikasi invarian itu untuk SETIAP baris, baik
    yang tetap maupun yang dipindah. Kalau ada satu saja yang tidak cocok,
    script berhenti tanpa mengubah apa pun.

Idempoten: kalau tidak ada siswa dengan dua baris di konten sumber, tidak ada
yang diubah. Default dry-run; pakai --apply untuk menyimpan.
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.material_content import MaterialContent  # noqa: E402
from src.models.student_answer import StudentAnswer  # noqa: E402

# (konten_sumber, idx_sumber, konten_tujuan, idx_tujuan, bagian_tujuan,
#  jumlah_yang_harus_pindah)
SPLITS = [
    (211, 0, 209, 1, 67, 35),   # 173 (dinding sel) balik ke bagian 67
    (219, 0, 217, 0, 71, 63),   # 192 (bahan genetik) balik ke bagian 71
]


def _correct_index(content, index):
    qs = (content.data or {}).get('questions') or []
    if index >= len(qs):
        return None
    return qs[index].get('correct_answer')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='simpan perubahan (tanpa flag ini hanya laporan)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print('=' * 74)
        print('PISAHKAN JAWABAN INTERAKTIF YANG TERTUMPUK')
        print('=' * 74)

        problems = []
        all_moves = []   # (answer, dest_content, dest_index, dest_section)
        for src_c, src_i, dst_c, dst_i, dst_sec, expect in SPLITS:
            src = MaterialContent.query.get(src_c)
            dst = MaterialContent.query.get(dst_c)
            if not src or not dst:
                problems.append(f'konten {src_c} atau {dst_c} tidak ada')
                continue
            src_ok = _correct_index(src, src_i)
            dst_ok = _correct_index(dst, dst_i)
            if src_ok is None or dst_ok is None:
                problems.append(f'konten {src_c}/{dst_c} tidak punya soal di indeks itu')
                continue

            rows = StudentAnswer.query.filter_by(
                content_id=src_c, question_index=src_i).order_by(
                StudentAnswer.student_id, StudentAnswer.id).all()
            by_student = defaultdict(list)
            for r in rows:
                by_student[r.student_id].append(r)

            moved = 0
            singles = 0
            for student_id, group in by_student.items():
                if len(group) == 1:
                    # Siswa ini hanya menjawab soal sumber, bukan soal tujuan.
                    singles += 1
                    only = group[0]
                    if not (only.is_correct == (only.selected_answer == src_ok)):
                        problems.append(
                            f'konten {src_c} idx {src_i}: baris {only.id} tidak '
                            f'konsisten dengan soal sumber (correct_idx={src_ok})')
                    continue
                if len(group) != 2:
                    problems.append(
                        f'konten {src_c} idx {src_i}: siswa {student_id} punya '
                        f'{len(group)} baris (harusnya 1 atau 2)')
                    continue
                # Baris terakhir = soal tujuan (lihat docstring).
                early, late = sorted(group, key=lambda a: a.id)
                if not (early.is_correct == (early.selected_answer == src_ok)):
                    problems.append(
                        f'konten {src_c} idx {src_i}: baris {early.id} tidak konsisten '
                        f'dengan soal sumber (correct_idx={src_ok})')
                if not (late.is_correct == (late.selected_answer == dst_ok)):
                    problems.append(
                        f'konten {dst_c} idx {dst_i}: baris {late.id} tidak konsisten '
                        f'dengan soal tujuan (correct_idx={dst_ok})')
                all_moves.append((late, dst_c, dst_i, dst_sec))
                moved += 1

            print(f'\nkonten {src_c} idx {src_i} -> konten {dst_c} idx {dst_i} '
                  f'(bagian {dst_sec})')
            print(f'   baris di sumber: {len(rows)} | siswa: {len(by_student)} '
                  f'(1 baris: {singles}, 2 baris: {len(by_student) - singles})')
            if moved == 0:
                print('   sudah rapi (tidak ada jawaban tertumpuk)')
            elif moved != expect:
                print(f'   akan dipindah: {moved} (diharapkan {expect})')
                problems.append(
                    f'konten {src_c} idx {src_i}: dipindah {moved}, diharapkan {expect}')
            else:
                print(f'   akan dipindah: {moved} (diharapkan {expect})')

        if problems:
            print('\nVALIDASI GAGAL - tidak ada yang diubah:')
            for p in problems:
                print(f'  - {p}')
            db.session.rollback()
            return 1

        print(f'\nTOTAL baris jawaban yang dipindah: {len(all_moves)}')
        if args.apply:
            for row, dst_c, dst_i, dst_sec in all_moves:
                row.content_id = dst_c
                row.question_index = dst_i
                row.section_id = dst_sec
            db.session.commit()
            print('Diterapkan.')
        else:
            print('Mode dry-run, tidak ada yang disimpan (--apply untuk menyimpan).')
        print('-' * 74)
        return 0


if __name__ == '__main__':
    sys.exit(main())
