import json
import re
from urllib.parse import urlparse, parse_qs

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def yt_id(url):
    if not url: return None
    url = str(url)
    m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', url)
    if m: return m.group(1)
    try:
        p = urlparse(url)
        if p.netloc in ('youtube.com','www.youtube.com'):
            q = parse_qs(p.query)
            if 'v' in q: return q['v'][0]
    except Exception:
        pass
    return None

def thumb(idv):
    return f'https://img.youtube.com/vi/{idv}/hqdefault.jpg' if idv else None

def add_img(doc, url, maxw=6.0):
    if not url: return
    try:
        import io, urllib.request
        with urllib.request.urlopen(url, timeout=40) as r:
            data = r.read()
        doc.add_picture(io.BytesIO(data), width=Inches(maxw))
    except Exception:
        p = doc.add_paragraph('Gambar: ' + url)
        p.runs[0].font.size = Pt(9)

data = json.load(open(r'D:\Aldeann\virus.json','r',encoding='utf-8'))
m = data.get('material', data)
doc = Document()

h = doc.add_heading(m.get('title','MATERI'), 0)
h.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph('Konsep Materi & Soal Berlabel Per Subtopik')
doc.add_paragraph(f'Total Subtopik: {len(m.get("sections",[]))}')
doc.add_page_break()

for si, sec in enumerate(m.get('sections',[])):
    doc.add_heading(sec.get('title','Subtopik'), 1)
    contents = sorted(sec.get('contents',[]), key=lambda x: x.get('position',0))
    doc.add_heading('A. KONSEP MATERI', 2)
    for c in contents:
        t = c.get('type')
        d = c.get('data',{}) or {}
        if t == 'heading':
            doc.add_heading(d.get('content',''), d.get('level',3))
        elif t == 'text':
            txt = d.get('content','')
            if txt: doc.add_paragraph(txt)
        elif t == 'box':
            b = doc.add_paragraph(d.get('content',''))
            b.style = 'Intense Quote'
        elif t == 'image':
            if d.get('caption'): doc.add_paragraph(d['caption'])
            add_img(doc, d.get('url'))
        elif t == 'video':
            vid = yt_id(d.get('url'))
            p = doc.add_paragraph('VIDEO')
            p.runs[0].bold = True
            if d.get('title'): doc.add_paragraph(f'Judul: {d["title"]}')
            if vid: add_img(doc, thumb(vid), maxw=5.5)
            doc.add_paragraph('Link akses: ' + (d.get('url') or ''))
        elif t == 'pdf':
            doc.add_paragraph('PDF: ' + (d.get('title') or ''))
            doc.add_paragraph(d.get('url') or '')
    # soal
    soal = []
    for c in contents:
        if c.get('type') in ('question','quiz'):
            soal.append((c.get('position',0), c.get('data',{}) or {}))
    soal.sort(key=lambda x:x[0])
    if soal:
        doc.add_heading('B. SOAL BERLABEL DI SUBTOPIK INI', 2)
        for idx, sq in enumerate(soal,1):
            sd = sq[1]
            q = sd.get('question') or sd.get('text') or ''
            doc.add_heading(f'Soal #{idx}', 3)
            if q: doc.add_paragraph(q)
            qt = sd.get('question_type') or sd.get('type') or ''
            if qt: doc.add_paragraph(f'Tipe: {qt}')
            opts = sd.get('options') or sd.get('choices') or []
            for op in opts:
                lab = op.get('label') or op.get('letter') or op.get('key') or ''
                txt = op.get('text') or op.get('value') or op.get('content') or ''
                doc.add_paragraph(f'  {lab}. {txt}')
            ca = sd.get('correct_answer') or sd.get('answer') or sd.get('correct') or ''
            if ca: doc.add_paragraph(f'Kunci Jawaban: {ca}')
            exp = sd.get('explanation') or sd.get('explain')
            if exp: doc.add_paragraph(f'Penjelasan: {exp}')
    doc.add_page_break()

out = r'D:\Aldeann\[DEMO] VIRUS - Konsep & Soal Per Subtopik.docx'
doc.save(out)
print(out)
