#!/usr/bin/env python3
"""Bangun dokumen Word (before/after) untuk fitur "Level Materi".

Menghasilkan .docx berisi screenshot dari docs/screenshots yang berakhiran
``-<suffix>.png``, satu gambar per halaman, sudah diskalakan agar muat 1 halaman
A4. Tidak butuh dependensi eksternal (hanya stdlib).

Contoh pakai:
    python docs/tools/build_docx.py --suffix sebelum
    python docs/tools/build_docx.py --suffix sesudah

Default output:
    --suffix sebelum -> docs/laporan-before-level-materi.docx
    --suffix sesudah -> docs/laporan-after-level-materi.docx
"""
import argparse
import os
import struct
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DOCS = os.path.join(REPO, "docs")
SHOTDIR = os.path.join(DOCS, "screenshots")

# filename template ({s} diganti suffix), judul, route.
# Urutan di sini = urutan di dokumen.
SHOTS = [
    ("dashboard-guru-{s}.png",                  "Dashboard Guru",                    "/teacher"),
    ("daftar-materi-guru-{s}.png",              "Daftar Materi (Guru)",              "/teacher/materials"),
    ("form-materi-{s}.png",                     "Form Materi Baru (Guru)",           "/teacher/materials/create"),
    ("form-edit-materi-{s}.png",                "Form Edit Materi (Guru)",           "/teacher/materials/edit/107"),
    ("analitik-materi-107-{s}.png",             "Analitik Materi (Guru)",            "/teacher/materials/analytics/107"),
    ("latihan-per-bagian-guru-{s}.png",         "Latihan per Bagian (Guru)",         "/teacher/practice"),
    ("bank-soal-guru-{s}.png",                  "Bank Soal (Guru)",                  "/teacher/question-bank"),
    ("analitik-penguasaan-{s}.png",             "Analitik Penguasaan (Guru)",        "/teacher/analytics"),
    ("ml-insights-{s}.png",                     "ML Insights (Guru)",                "/teacher/analytics/ml"),
    ("analitik-siswa-72-{s}.png",               "Analitik Siswa (Guru)",             "/teacher/analytics/students/72"),
    ("daftar-materi-siswa-{s}.png",             "Daftar Materi (Siswa)",             "/student/materials"),
    ("detail-materi-siswa-{s}.png",             "Detail Materi (Siswa)",             "/student/materials/107"),
    ("dashboard-siswa-{s}.png",                 "Dashboard Siswa",                   "/student/dashboard"),
    ("riwayat-belajar-siswa-{s}.png",           "Riwayat Belajar (Siswa)",           "/student/progress"),
    ("progres-materi-siswa-107-{s}.png",        "Progress Materi (Siswa)",           "/student/progress/107"),
]

TW = 635  # EMU per twip
PAGE_W_TW, PAGE_H_TW = 11906, 16838  # A4
MARGIN_TW = 1440
CONTENT_W = (PAGE_W_TW - 2 * MARGIN_TW) * TW
CONTENT_H = (PAGE_H_TW - 2 * MARGIN_TW) * TW
MAX_H = int(CONTENT_H * 0.90)


def png_size(path):
    with open(path, "rb") as f:
        b = f.read(24)
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a png: " + path)
    w, h = struct.unpack(">II", b[16:24])
    return w, h


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run(text, bold=False, size=20, color=None):
    rpr = "<w:rPr>"
    if bold:
        rpr += "<w:b/>"
    rpr += '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
    if color:
        rpr += '<w:color w:val="%s"/>' % color
    rpr += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size)
    rpr += "</w:rPr>"
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(text))


def text_para(text, bold=False, size=20, color=None, after=120):
    return '<w:p><w:pPr><w:spacing w:after="%d"/></w:pPr>%s</w:p>' % (
        after, run(text, bold, size, color))


def image_para(rid, cx, cy, idx, name):
    return (
        '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="120" w:after="120"/></w:pPr>'
        '<w:r><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        '<wp:extent cx="%d" cy="%d"/>'
        '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        '<wp:docPr id="%d" name="Picture %d"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic>'
        '<pic:nvPicPr><pic:cNvPr id="%d" name="%s"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r></w:p>'
    ) % (cx, cy, idx, idx, idx, esc(name), rid, cx, cy)


PAGEBREAK = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')

CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Default Extension="png" ContentType="image/png"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
    '</Types>')

ROOT_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
    '</Relationships>')

STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:docDefaults><w:rPrDefault><w:rPr>'
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="20"/><w:szCs w:val="20"/>'
    '</w:rPr></w:rPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
    '</w:styles>')

APP = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
    'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
    '<Application>E-Bio-X Docs Builder</Application></Properties>')


def build(suffix, out_path, title, status_note):
    records = []
    for tmpl, judul, route in SHOTS:
        fname = tmpl.format(s=suffix)
        path = os.path.join(SHOTDIR, fname)
        if os.path.exists(path):
            records.append((fname, judul, route, path))
        else:
            print("SKIP (missing):", fname)
    if not records:
        raise SystemExit("Tidak ada screenshot berakhiran -%s.png di %s" % (suffix, SHOTDIR))

    body = [
        text_para(title, bold=True, size=32),
        text_para("Fitur: penilaian tingkat kesulitan materi otomatis dari SET DIAGNOSTIK "
                  "(netral, tidak terpengaruh mesin adaptif).", size=20),
        text_para(status_note, size=18, color="C00000"),
        text_para("Akun: guru1@ebiox.com (guru) - murid1@ebiox.com (siswa)  -  Tanggal: 15 Oktober 2026",
                  size=18, color="808080", after=240),
    ]

    rels = []
    idx = 1
    first = True
    for fname, judul, route, path in records:
        w, h = png_size(path)
        cx = CONTENT_W
        cy = int(cx * h / w)
        if cy > MAX_H:
            cy = MAX_H
            cx = int(cy * w / h)
        rid = "rIdImg%d" % idx
        if not first:
            body.append(PAGEBREAK)
        first = False
        body.append(text_para("%d. %s" % (idx, judul), bold=True, size=24, after=40))
        body.append(text_para("Route: %s   -   %dx%d px" % (route, w, h),
                              size=16, color="808080", after=80))
        body.append(image_para(rid, cx, cy, idx, fname))
        rels.append('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image%d.png"/>' % (rid, idx))
        idx += 1

    sectpr = ('<w:sectPr><w:pgSz w:w="%d" w:h="%d"/>'
              '<w:pgMar w:top="%d" w:right="%d" w:bottom="%d" w:left="%d" '
              'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
              % (PAGE_W_TW, PAGE_H_TW, MARGIN_TW, MARGIN_TW, MARGIN_TW, MARGIN_TW))
    body.append(sectpr)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document %s><w:body>%s</w:body></w:document>' % (NS, "".join(body)))

    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        + "".join(rels) + '</Relationships>')

    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>%s</dc:title><dc:creator>E-Bio-X</dc:creator><cp:lastModifiedBy>E-Bio-X</cp:lastModifiedBy>'
        '<dcterms:created xsi:type="dcterms:W3CDTF">2026-10-15T00:00:00Z</dcterms:created>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-10-15T00:00:00Z</dcterms:modified>'
        '</cp:coreProperties>' % esc(title))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", APP)
        for i, (_, _, _, path) in enumerate(records, start=1):
            z.write(path, "word/media/image%d.png" % i)
    return out_path, len(records)


DEFAULTS = {
    "sebelum": ("laporan-before-level-materi.docx",
                "Dokumentasi BEFORE - Level Materi",
                "Status: BELUM diimplementasikan - gambar adalah kondisi saat ini (before)."),
    "sesudah": ("laporan-after-level-materi.docx",
                "Dokumentasi AFTER - Level Materi",
                "Status: SUDAH diimplementasikan - gambar adalah kondisi setelah perubahan (after)."),
}


def main():
    ap = argparse.ArgumentParser(description="Bangun dokumen Word before/after Level Materi.")
    ap.add_argument("--suffix", default="sebelum", choices=["sebelum", "sesudah"])
    ap.add_argument("--out", default=None, help="Path .docx keluaran")
    args = ap.parse_args()

    default_name, title, note = DEFAULTS[args.suffix]
    out = args.out or os.path.join(DOCS, default_name)
    path, n = build(args.suffix, out, title, note)
    print("WROTE:", path)
    print("IMAGES:", n)
    print("SIZE_KB:", round(os.path.getsize(path) / 1024, 1))


if __name__ == "__main__":
    main()
