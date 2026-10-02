# -*- coding: utf-8 -*-
"""Fase 1: backfill `questions.section_id` (tag bagian materi) secara aman.

Strategi (berurutan, tidak mengarang):
  1. Ikuti section kuis:  question.quiz.section_id
  2. Judul bank soal yang persis sama dengan salah satu judul bagian materi
     (bank_question.topic == material_section.title, ternormalisasi)
  3. Jika materi kuis hanya punya SATU bagian, pakai bagian itu (tidak ambigu)

Default: dry-run (tidak menulis). Gunakan --apply untuk menyimpan.
Hanya mengisi soal yang `section_id`-nya masih NULL, kecuali --overwrite.

Contoh:
  python scripts/backfill_question_sections.py
  python scripts/backfill_question_sections.py --apply
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.models.question import Question  # noqa: E402


def _norm(text):
    return ' '.join((text or '').strip().lower().split())


def _section_by_topic(quiz, topic):
    if not quiz.material_id or not topic:
        return None
    want = _norm(topic)
    if not want:
        return None
    for section in quiz.material.sections:
        if _norm(section.title) == want:
            return section.id
    return None


def propose_section(question):
    """Return (section_id, reason) for a question, or (None, reason)."""
    quiz = question.quiz
    if not quiz:
        return None, 'tanpa kuis'

    # 1. Ikuti section kuis.
    if quiz.section_id:
        return quiz.section_id, 'section kuis'

    # 2. Topik bank soal yang persis sama dengan judul bagian.
    bank_topic = (question.bank_question.topic
                  if question.bank_question else None)
    matched = _section_by_topic(quiz, bank_topic)
    if matched:
        return matched, f'topik bank "{bank_topic}"'

    # 3. Materi hanya punya satu bagian -> tidak ambigu.
    if quiz.material and len(quiz.material.sections) == 1:
        return quiz.material.sections[0].id, 'materi hanya 1 bagian'

    return None, 'tidak ada padanan pasti (perlu tag manual guru)'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true',
                        help='simpan perubahan (default: dry-run)')
    parser.add_argument('--overwrite', action='store_true',
                        help='timpa soal yang sudah punya section_id')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        questions = Question.query.order_by(Question.id).all()
        planned = []
        skipped_tagged = 0
        reasons = {}

        for q in questions:
            if q.section_id and not args.overwrite:
                skipped_tagged += 1
                continue
            section_id, reason = propose_section(q)
            reasons[reason] = reasons.get(reason, 0) + 1
            if section_id:
                planned.append((q, section_id, reason))

        print(f'Total soal            : {len(questions)}')
        print(f'Sudah bertag (skip)   : {skipped_tagged}')
        print(f'Akan diisi            : {len(planned)}')
        print('Rincian alasan:')
        for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f'  - {reason}: {count}')

        if not planned:
            print('\nTidak ada yang bisa diisi otomatis. '
                  'Sisanya perlu ditandai guru lewat builder kuis.')
            return

        for q, section_id, reason in planned:
            section = next(s for s in q.quiz.material.sections if s.id == section_id)
            print(f'  q{q.id} -> section {section_id} "{section.title}" ({reason})')

        if args.apply:
            for q, section_id, _ in planned:
                q.section_id = section_id
            db.session.commit()
            print(f'\nDiterapkan: {len(planned)} soal diperbarui.')
        else:
            print('\nDRY-RUN. Jalankan ulang dengan --apply untuk menyimpan.')


if __name__ == '__main__':
    main()
