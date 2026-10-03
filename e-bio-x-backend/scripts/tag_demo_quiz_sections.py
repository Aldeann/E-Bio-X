# -*- coding: utf-8 -*-
"""Fase 2 (persiapan demo): menandai soal kuis demo ke bagian materinya.

Kuis demo 89/90/91 (materi 115/116/117) punya 1880 jawaban siswa yang
terkumpul rapi, tapi `questions.section_id`-nya masih semua NULL. Akibatnya
seluruh jawaban itu tidakhitung di diagnosis per bagian: tidak ada bagian
yang punya bukti. yang tersedia cuma 2 jawaban interaktif per siswa per
bagian, sedangkan `MIN_SECTION_SAMPLE = 3`, jadi 0 dari 295 sel
(siswa x bagian) bisa mendapat skor.

Script ini menutup celah itu dengan menandai soal kuis tersebut ke bagian
yang benar, satu per satu, dengan alasannya.

Aturan yang dijaga script ini:
  - Tautan ditulis sebagai daftar (question_id, section_id, alasan) di bawah.
    TIDAK ada pencocokan teks otomatis: Fallen ke bagian mana adalah
    keputusan guru, bukan hasil tebakan. Alasan ditulis per soal supaya
    bisa diaudit.
  - Soal yang tidak benar-benar milik satu pun bagian TIDAK dipaksa. Daftar
    AMBIGUOUS di bawah sengaja dibiarkan NULL, dan alasannya dicetak saat
    dijalankan. Bagian yang tidak bisa dibuktikan lebih baik kosong daripada
    salah attribusi.
  - Pengaman: bagian harus dari materi yang sama dengan kuis soal tersebut,
    dan soal harus dari kuis demo yang terdaftar di DEMO_QUIZ_IDS.
  - `quizzes.section_id` SENGAJA tidak diisi. Satu kuis menyentuh dua bagian,
    jadi tag per soal (bukan per kuis) yang dipakai di sini.
  - Idempoten: menandai soal yang sudah tertaut ke bagian yang sama tidak
    melakukan perubahan. Soal yang tertaut ke bagian LAIN dilaporkan sebagai
    masalah, tidak ditimpa diam-diam.

Default: dry-run (tidak menulis). Gunakan --apply untuk menyimpan.

Contoh:
  python scripts/tag_demo_quiz_sections.py
  python scripts/tag_demo_quiz_sections.py --apply
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.question import Question  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402

# Kuis demo yang boleh disentuh script ini.
DEMO_QUIZ_IDS = (89, 90, 91)

# (question_id, section_id, alasan)
LINKS = [
    # --- Materi 115 "[Demo] Sel dan Organel" ---
    # Bagian 67 "Pengenalan Sel"     : menanyakan bagian/zat sel apa yang disebut apa.
    # Bagian 68 "Organel dan Fungsinya": menanyakan organel tertentu mengerjakan apa.
    (171, 67, 'menanyakan bagian sel yang mengontrol seluruh aktivitas sel (nukleus); '
              'soal pengenalan bagian sel, bukan fungsi organel'),
    (173, 67, 'menanyakan susunan dinding sel sebagai pembatas sel tumbuhan'),
    (176, 67, 'menanyakan bagian sel yang mengatur keluar masuknya zat (membran sel)'),
    (178, 67, 'menanyakan cairan sel tempat organel tersuspensi (sitoplasma); zat '
              'dasar sel, bukan organel'),

    (172, 68, 'menanyakan tempat respirasi sel (mitokondria): soal fungsi organel'),
    (174, 68, 'menanyakan organel pencerna makanan (lisosom): soal fungsi organel'),
    (175, 68, 'menanyakan organel sintesis protein (ribosom): soal fungsi organel'),
    (177, 68, 'menanyakan organel fotosintesis (kloroplas): soal fungsi organel'),
    (179, 68, 'menanyakan organel penyimpan air (vakuola): soal fungsi organel'),
    (180, 68, 'menanyakan fungsi badan Golgi: soal fungsi organel'),

    # --- Materi 116 "[Demo] Bakteri dan Peranannya" ---
    # Bagian 69 "Ciri dan Struktur Bakteri": apa yang dimiliki bakteri.
    # Bagian 70 "Peranan Bakteri"          : apa yang dilakukan/man'sfaat bakteri.
    (181, 69, 'menanyakan kondisi pembelahan binary fission; ciri bakteri, bukan '
              'peran/manfaatnya'),
    (182, 69, 'menanyakan bentuk bakteri (basil): struktur sel bakteri'),
    (185, 69, 'menanyakan alat gerak bakteri (flagel): struktur bakteri'),
    (187, 69, 'pewarnaan Gram membedakan berdasarkan dinding sel: klasifikasi yang '
              'bersandar pada struktur'),
    (189, 69, 'menanyakan materi genetik bakteri (DNA pada nukleoid): bagian dari '
              'strukturnya'),

    (183, 70, 'menanyakan zat antibakteri yang dibuat bakteri: peran bakteri '
              'terhadap bakteri lain'),
    (184, 70, 'menanyakan bakteri penghasil asam dalam yoghurt: penerapannya di '
              'produk'),
    (186, 70, 'menanyakan bakteri pada pembuatan keju dan mentega: penerapannya'),
    (188, 70, 'Rhizobium menambat nitrogen di tanah: peran bakteri dalam ekosistem'),
    (190, 70, 'bakteri penyebab tuberkulosis: peran patogen'),

    # --- Materi 117 "[Demo] Virus dan Replikasinya" ---
    # Bagian 71 "Struktur Virus"       : bagian-bagian virus.
    # Bagian 72 "Siklus Replikasi Virus": tahap-tahap siklus dalam sel inang.
    (192, 71, 'menanyakan bahan genetik virus (DNA atau RNA): bagian virus'),
    (193, 71, 'menanyakan selubung protein virus (kapsid): bagian virus'),
    (195, 71, 'menanyakan bagian virus yang menjadi materi genetik (asam nukleat): '
              'bagian virus'),

    (191, 72, 'siklus yang langsung memecah sel inang (litik): tahap siklus replikasi'),
    (197, 72, 'menanyakan tahap pertama infeksi (adsorpsi): tahap siklus replikasi'),
    (200, 72, 'siklus yang menyisipkan materi genetik ke DNA inang (lisogenik): '
              'siklus replikasi'),
]

# question_id -> alasan kenapa sengaja dibiarkan tanpa tag.
AMBIGUOUS = {
    194: 'menanyakan kenapa virus tidak dianggap organisme; menyangkut virus secara '
         'umum, bukan struktur virus dan bukan tahap siklus replikasi',
    196: 'menanyakan jenis virus yang menyerang bakteri (bakteriofag); menyangkut '
         'inang/pola penyerangan, bukan struktur virus dan bukan tahap siklus',
    198: 'menanyakan virus penyebab AIDS (HIV); menyangkut penyakit, di luar '
         'struktur virus dan siklus replikasi',
    199: 'menanyakan cara kerja vaksin; menyangkut pencegahan, di luar struktur virus '
         'dan siklus replikasi',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='simpan perubahan (tanpa flag ini hanya laporan)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        changed, kept, problems = 0, 0, []
        print('=' * 74)
        print('TAUTAN SOAL KUIS DEMO -> BAGIAN MATERI (persiapan diagnosis per bagian)')
        print('=' * 74)

        by_material = {}
        for q_id, sec_id, reason in LINKS:
            q = Question.query.get(q_id)
            sec = MaterialSection.query.get(sec_id)
            if not q:
                problems.append(f'soal {q_id} tidak ada')
                continue
            if not sec:
                problems.append(f'bagian {sec_id} tidak ada')
                continue

            quiz = q.quiz
            if not quiz or quiz.id not in DEMO_QUIZ_IDS:
                problems.append(f'soal {q_id} bukan dari kuis demo {DEMO_QUIZ_IDS}')
                continue
            if quiz.material_id != sec.material_id:
                problems.append(
                    f'soal {q_id} (kuis {quiz.id}, materi {quiz.material_id}) tidak boleh '
                    f'ditautkan ke bagian {sec_id} dari materi {sec.material_id}')
                continue

            label = (f'#{q_id} "{q.text[:46]}"\n'
                     f'      -> bagian {sec_id} "{sec.title}" (materi {sec.material_id})')
            if q.section_id == sec.id:
                kept += 1
                print(f'[LEWAT ] {label} (sudah tertaut)')
                continue
            if q.section_id is not None:
                problems.append(
                    f'soal {q_id} sudah tertaut ke bagian {q.section_id}, bukan {sec_id}; '
                    f'periksa manual (script tidak menimpa)')
                continue

            print(f'[TAUT  ] {label}\n      alasan: {reason}')
            by_material.setdefault((sec.material_id, sec.id), []).append(q_id)
            if args.apply:
                q.section_id = sec.id
            changed += 1

        print('\n' + '-' * 74)
        print('SOAL YANG SENGAJA DIBIARKAN TANPA TAG (tidak milik satu pun bagian):')
        for q_id, reason in sorted(AMBIGUOUS.items()):
            q = Question.query.get(q_id)
            if not q:
                problems.append(f'soal {q_id} (daftar ambigu) tidak ada')
                continue
            state = 'NULL' if q.section_id is None else f'TERTAG {q.section_id}'
            print(f'  #{q_id} [{state}] "{q.text[:52]}"')
            print(f'      alasan: {reason}')

        print('\n' + '-' * 74)
        print('RINGKASAN PER BAGIAN (soal kuis yang akan dihitung sebagai bukti):')
        for sec in MaterialSection.query.filter(
                MaterialSection.id.in_([s for _, s, _ in LINKS])
        ).order_by(MaterialSection.material_id, MaterialSection.position).all():
            qids = by_material.get((sec.material_id, sec.id), [])
            print(f'  bagian {sec.id} "{sec.title}" (materi {sec.material_id}): '
                  f'{len(qids)} soal {sorted(qids)}')

        if problems:
            print('\nPERHATIAN:')
            for p in problems:
                print(f'  - {p}')

        db.session.commit() if args.apply else db.session.rollback()

        print('\n' + '-' * 74)
        print(f'ditandai: {changed} | sudah benar: {kept} | perlu diperbaiki manual: '
              f'{len(problems)}')
        if not args.apply:
            print('mode dry-run, tidak ada yang disimpan (--apply untuk menyimpan)')
        print('-' * 74)
        return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())