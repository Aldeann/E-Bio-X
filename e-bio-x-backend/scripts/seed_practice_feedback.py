# -*- coding: utf-8 -*-
"""Isi pembahasan + miskonsepsi + feedback per opsi untuk soal latihan demo.

Soal bank bawaan seed lama dibuat tanpa pembahasan. Sebagai soal latihan, soal
tanpa pembahasan hampir tidak ada nilainya: siswa menjawab salah lalu hanya tahu
"salah", tanpa tahu alasan sebenarnya. Script ini mengisi tiga kolom yang
dipakai layar latihan (lihat student_practice_service.grade):

  - `explanation`  : pembahasan resmi untuk seluruh soal
  - `misconception`: kesalahan yang paling sering terjebak di soal ini
  - `feedback`     : alasan opsi benar / salah, per opsi

Isi teksnya ditulis manual di bawah (bukan hasil model) supaya jelas siapa
pengarangnya dan bisa dikoreksi guru. Skrip hanya MENGISI kolom yang masih
kosong, jadi hasil suntingan guru tidak tertimpa. Status persetujuan tidak
disentuh: menyetujui soal tetap keputusan guru lewat halaman Latihan Bagian.

Default: dry-run. Gunakan --apply untuk menyimpan.

Contoh:
  python scripts/seed_practice_feedback.py
  python scripts/seed_practice_feedback.py --apply
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.question_bank import QuestionBank  # noqa: E402

FEEDBACK = {
    7: {
        'explanation': (
            'Badan virus terdiri atas materi genetik (DNA atau RNA) dan selubung '
            'protein yang disebut kapsid. Mitokondria dan badan golgi adalah '
            'organel yang terdapat pada sel, sedangkan virus bukan sel.'),
        'misconception': (
            'Mengira virus memiliki organel sel seperti mitokondria atau badan '
            'golgi karena virus memiliki materi genetik.'),
        'options': {
            'kapsid': 'Benar, kapsid adalah selubung protein virus.',
            'mitokondria': 'Salah, mitokondria adalah organel sel, virus tidak memilikinya.',
            'badan golgi': 'Salah, badan golgi adalah organel sel, virus tidak memilikinya.',
        },
    },
    9: {
        'explanation': (
            'Kapsid adalah lapisan protein yang melindungi materi genetik virus '
            'dari kerusakan. Kapsomer merupakan subunit penyusun kapsid, bukan '
            'lapisan pelindung itu sendiri.'),
        'misconception': (
            'Tertukar antara kapsid (selubung pelindung) dan kapsomer '
            '(subunit pembentuk kapsid).'),
        'options': {
            'Kapsid': 'Benar, kapsid melindungi materi genetik virus.',
            'Kapsomer': 'Salah, kapsomer adalah subunit penyusun kapsid.',
            'Selubung': 'Salah, selubung adalah bagian virus yang memakai membran sel inang.',
            'Ekor': 'Salah, ekor virus berfungsi seperti jarum injeksi untuk menembus sel inang.',
            'Serabut ekor': 'Salah, serabut ekor berfungsi melekatkan virus pada sel inang.',
        },
    },
    10: {
        'explanation': (
            'Setiap virus hanya memiliki satu jenis materi genetik, yaitu DNA '
            'atau RNA. Tidak ada virus yang membawa DNA dan RNA sekaligus, '
            'karena hanya satu yang dipakai untuk membuat virus baru.'),
        'misconception': (
            'Mengira virus seperti sel yang membawa DNA dan RNA sekaligus.'),
        'options': {
            'DNA saja': 'Salah, sebagian virus memakai DNA, tetapi sebagian lain memakai RNA.',
            'RNA saja': 'Salah, sebagian virus memakai RNA, tetapi sebagian lain memakai DNA.',
            'DNA atau RNA': 'Benar, tiap virus hanya salah satu dari keduanya.',
            'DNA dan RNA secara bersamaan pada semua virus':
                'Salah, tidak ada virus yang membawa DNA dan RNA sekaligus.',
            'Protein dan RNA': 'Salah, protein adalah penyusun kapsid, bukan materi genetik.',
        },
    },
    11: {
        'explanation': (
            'Virus tidak memiliki ribosom maupun sistem metabolisme sendiri, '
            'sehingga tidak bisa menyusun protein atau menghasilkan energi '
            'mandiri. Virus memakai ribosom sel inang untuk membuat protein '
            'virus yang baru.'),
        'misconception': (
            'Mengira virus gagal bereproduksi karena tidak punya inti sel, '
            'padahal alasannya tidak punya ribosom dan metabolisme sendiri.'),
        'options': {
            'Tidak memiliki materi genetik':
                'Salah, virus justru memiliki materi genetik, itulah sumber salinannya.',
            'Tidak memiliki kapsid':
                'Salah, virus memiliki kapsid sebagai pelindung materi genetik.',
            'Tidak memiliki ribosom dan sistem metabolisme sendiri':
                'Benar, tanpa ribosom dan metabolisme virus tidak bisa bereproduksi sendiri.',
            'Tidak memiliki protein':
                'Salah, protein penyusun kapsid justru bagian dari virus.',
            'Tidak memiliki membran sel':
                'Salah, sebagian virus memang ber membran sel, dan itu bukan alasan '
                'ketidakmampuannya bereproduksi.',
        },
    },
    13: {
        'explanation': (
            'Garis Wallace memisahkan fauna tipe Asiatis di barat Indonesia '
            'dengan fauna tipe Australasia di timur. Fauna yang hidup di sekitar '
            'garis itu disebut fauna peralihan, misalnya anoa dan babirusa.'),
        'misconception': (
            'Mengira Indonesia hanya terbagi dua zona fauna (Asiatis dan '
            'Australasia) tanpa adanya zona peralihan di antaranya.'),
        'options': {
            'australis': 'Salah, fauna Australasia terdapat di timur garis Wallace, '
                         'bukan di kawasan peralihan.',
            'neartik': 'Salah, neartik adalah kawasan fauna Kutub Utara.',
            'peralihan': 'Benar, fauna di sekitar garis Wallace disebut fauna peralihan.',
            'asiatis': 'Salah, fauna Asiatis terdapat di barat garis Wallace.',
            'oriental': 'Salah, oriental menunjuk wilayah Asia Tenggara bagian selatan.',
        },
    },
    16: {
        'explanation': (
            'Nilai ekonomi adalah manfaat keanekaragaman hayati yang dimanfaatkan '
            'manusia sebagai sumber pangan, sandang, dan papan. Nilai estetika '
            'adalah keindahan, sedangkan nilai ilmiah adalah pengetahuan yang '
            'diperoleh dari kajian.'),
        'misconception': (
            'Tertukar antara nilai ekonomi (bermanfaat untuk kebutuhan hidup) '
            'dengan nilai estetika (keindahan).'),
        'options': {
            'estetika': 'Salah, estetika berkaitan dengan keindahan, bukan pemanfaatan bahan.',
            'ekologi': 'Salah, ekologi adalah ilmu yang mempelajari hubungan antarorganisme, '
                       'bukan nilai yang dipakai manusia.',
            'ilmiah': 'Salah, nilai ilmiah adalah pengetahuan dari hasil kajian.',
            'biologis': 'Salah, kata "biologis" menggambarkan jenis sumber daya, bukan nilainya.',
            'ekonomi': 'Benar, menjadi bahan pangan, sandang, dan papan adalah nilai ekonomi.',
        },
    },
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='simpan perubahan (tanpa flag ini hanya laporan)')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        filled, kept, missing = 0, 0, []
        print('=' * 70)
        print('PEMBAHASAN + MISKONSEPSI + FEEDBACK OPSI (soal latihan demo)')
        print('=' * 70)

        for bq_id, content in sorted(FEEDBACK.items()):
            bq = QuestionBank.query.get(bq_id)
            if not bq:
                missing.append(f'soal bank {bq_id} tidak ada')
                continue
            head = f'#{bq_id} "{bq.question_text[:56]}"'
            if bq.explanation and bq.misconception and all(o.feedback for o in bq.options):
                kept += 1
                print(f'[LEWAT ] {head} sudah lengkap')
                continue

            print(f'[ISI   ] {head}')
            if not bq.explanation:
                bq.explanation = content['explanation']
                filled += 1
                print('        + explanation')
            if not bq.misconception:
                bq.misconception = content['misconception']
                filled += 1
                print('        + misconception')
            for opt in sorted(bq.options, key=lambda x: x.order_index):
                if opt.feedback:
                    continue
                text = content['options'].get(opt.option_text)
                if not text:
                    missing.append(
                        f'soal {bq_id} opsi "{opt.option_text}" tidak ada di daftar teks')
                    continue
                opt.feedback = text
                filled += 1
            done = sum(1 for o in bq.options if o.feedback)
            print(f'        + feedback opsi {done}/{len(bq.options)}')

        if missing:
            print('\nPERHATIAN:')
            for m in missing:
                print(f'  - {m}')

        db.session.commit() if args.apply else db.session.rollback()

        print('\n' + '-' * 70)
        print(f'diisi: {filled} | sudah lengkap: {kept} | perlu diperbaiki manual: {len(missing)}')
        if not args.apply:
            print('mode dry-run, tidak ada yang disimpan (--apply untuk menyimpan)')
        print('-' * 70)
        return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())