#!/usr/bin/env python3
"""Validate the generated before/after .docx files.

Checks that each is a readable OOXML package, lists the embedded images, counts
the drawings, and prints the per-page titles in order.
"""
import os
import re
import sys
import zipfile

DOCS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FILES = [
    "laporan-after-level-materi.docx",
    "laporan-before-level-materi.docx",
]


def main():
    rc = 0
    for name in FILES:
        path = os.path.join(DOCS, name)
        if not os.path.exists(path):
            print("MISSING:", path)
            rc = 1
            continue
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            media = sorted(n for n in z.namelist() if n.startswith("word/media/"))
            doc = z.read("word/document.xml").decode("utf-8")
            rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
            titles = re.findall(r'xml:space="preserve">(\d+\. [^<]+)<', doc)
        drawings = doc.count("<w:drawing>")
        rel_imgs = rels.count('Target="media/image')
        print(name)
        print("  zip_ok:", bad is None)
        print("  media_files:", len(media), " drawings:", drawings,
              " image_rels:", rel_imgs)
        print("  titles:", len(titles))
        for t in titles:
            print("    ", t)
        ok = (bad is None and len(media) == drawings == rel_imgs
              and len(media) > 0)
        if not ok:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
