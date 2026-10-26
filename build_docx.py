import json
import re
import os
from urllib.parse import urlparse, parse_qs

try:
    from docx import Document
    from docx.shared import Inches, Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except Exception:
    raise SystemExit("python-docx not installed")

def yt_id(url):
    if not url: return None
    url = str(url)
    m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', url)
    if m: return m.group(1)
    p = urlparse(url)
    if p.netloc in ('youtube.com','www.youtube.com'):
        q = parse_qs(p.query)
        if 'v' in q: return q['v'][0]
    return None

def thumb(idv):
    return f'https://img.youtube.com/vi/{idv}/hqdefault.jpg' if idv else None

def add_img(doc, url, maxw=6.0):
    if not url: return
    try:
        import io, urllib.request
        data = urllib.request.urlopen(url, timeout=30).read()
        doc.add_picture(io.BytesIO(data), width=Inches(maxw))
    except Exception:
        p = doc.add_paragraph('Gambar: ' + url)
        p.runs[0].font.size = Pt(9)

data = json.load(open(r'D:\Aldeann\virus_material_full.json','r',encoding='utf-8'))
m = data.get('material', data)
doc = Document()

# cover
h = doc.add_heading(m.get('title','MATERI'), 0)
h.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph('Konsep Materi + Soal Berlabel Per Subtopik')
doc.add_paragraph(f'Total Subtopik: {len(m.get("sections",[]))}')
doc.add_page_break()

for si, sec in enumerate(m.get('sections',[])):
    s = doc.add_heading(sec.get('title','Subtopik'), 1)
    doc.add_paragraph(f'ID: {sec.get("id")} | Posisi: {sec.get("position")}')
    contents = sorted(sec.get('contents',[]), key=lambda x: x.get('position',0))
    # konsep
    doc.add_heading('A. KONSEP MATERI', 2)
    for c in contents:
        t = c.get('type')
        d = c.get('data',{}) or {}
        if t == 'heading':
            lvl = d.get('level',3)
            doc.add_heading(d.get('content',''), lvl)
        elif t == 'text':
            doc.add_paragraph(d.get('content',''))
        elif t == 'box':
            p = doc.add_paragraph(d.get('content',''))
            p.style = 'Intense Quote'
        elif t == 'image':
            doc.add_paragraph(d.get('caption') or '')
            add_img(doc, d.get('url'))
        elif t == 'video':
            vid = yt_id(d.get('url'))
            th = thumb(vid)
            p = doc.add_paragraph('VIDEO')
            p.runs[0].bold = True
            doc.add_paragraph(f'Judul: {d.get("title") or ""}')
            if th: add_img(doc, th, maxw=5.5)
            p2 = doc.add_paragraph('Link akses: ' + (d.get('url') or ''))
            p2.runs[0].font.size = Pt(9)
        elif t == 'pdf':
            doc.add_paragraph('PDF: ' + (d.get('title') or d.get('url') or ''))
            doc.add_paragraph(d.get('url') or '')
    # soal
    soal = []
    for c in contents:
        if c.get('type') in ('question','quiz'):
            soal.append((c.get('position',0), c.get('data',{}) or {}))
    soal.sort(key=lambda x:x[0])
    if soal:
        doc.add_heading('B. SOAL BERLABEL DI SUBTOPIK INI', 2)
        for idx,sq in enumerate(soal,1):
            sd = sq[1]
            qtext = sd.get('question') or sd.get('text') or ''
            doc.add_heading(f'Soal #{idx}', 3)
            doc.add_paragraph(qtext)
            qt = sd.get('question_type') or sd.get('type') or sd.get('kind') or ''
            if qt:
                doc.add_paragraph(f'Tipe: {qt}')
            opts = sd.get('options') or sd.get('choices') or []
            for op in opts:
                lab = op.get('label') or op.get('letter') or op.get('key') or ''
                txt = op.get('text') or op.get('value') or op.get('content') or ''
                doc.add_paragraph(f'  {lab}. {txt}')
            if 'answer' in sd or 'correct_answer' in sd or 'correct' in sd:
                ca = sd.get('correct_answer') or sd.get('answer') or sd.get('correct') or ''
                doc.add_paragraph(f'Kunci Jawaban: {ca}')
            if sd.get('explanation') or sd.get('explain'):
                doc.add_paragraph(f'Penjelasan: {sd.get("explanation") or sd.get("explain")}')
    doc.add_page_break()

out = r'D:\Aldeann\[DEMO] VIRUS - Konsep & Soal Per Subtopik.docx'
doc.save(out)
print('OK', out)
