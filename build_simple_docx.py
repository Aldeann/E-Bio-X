from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import json, re, io, urllib.request
from urllib.parse import urlparse, parse_qs

def yt_id(url):
    if not url: return None
    m = re.search(r'(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})', str(url))
    if m: return m.group(1)
    try:
        p = urlparse(str(url))
        if p.netloc in ('youtube.com','www.youtube.com'):
            q = parse_qs(p.query)
            if 'v' in q: return q['v'][0]
    except: pass
    return None

def thumb(idv): return f'https://img.youtube.com/vi/{idv}/hqdefault.jpg' if idv else None

def add_img(doc,url,maxw=5.5):
    if not url: return
    try:
        with urllib.request.urlopen(url,timeout=30) as r:
            data=r.read()
        doc.add_picture(io.BytesIO(data), width=Inches(maxw))
    except Exception as e:
        p=doc.add_paragraph('Gambar: '+url)
        p.runs[0].font.size=Pt(9)

data=json.load(open(r'D:\Aldeann\virus.json','r',encoding='utf-8'))
m=data.get('material',data)
doc=Document()
doc.add_heading(m['title'],0).alignment=WD_ALIGN_PARAGRAPH.CENTER
doc.add_paragraph('Konsep Materi & Soal Berlabel Per Subtopik')
doc.save(r'D:\Aldeann\test.docx')
print('ok')
