# ============================================================
# KNOWLEDGE GRAPH PRASYARAT ANTAR BAGIAN (otomatis)
#
# Tujuan: sistem bisa menjawab "bagian mana yang harus dipelajari
# lebih dulu" tanpa guru mengisi apa pun. Edge (prasyarat) diturunkan
# dari bukti yang benar-benar ada di konten materi, bukan dikarang.
#
# Tiga sumber bukti, semuanya transparan dan bisa dihitung ulang:
#
#   1. `reference`  - sebuah bagian menyebut JUDUL bagian lain secara
#                     persis. Bukti paling kuat (kutipan literal).
#   2. `similarity` - isi dua bagian dalam materi yang sama sangat mirip
#                     (TF-IDF cosine). Arah dari posisi (lebih dulu =
#                     prasyarat). Ini sinyal terukur, bukan tebakan.
#   3. `position`   - cadangan: bagian tepat sebelumnya dalam urutan
#                     materi. Dipakai hanya bila dua sumber di atas tidak
#                     menghasilkan edge. Ini perilaku lama yang sudah ada,
#                     dipertahankan supaya graph kosong tidak menghapus
#                     aturan urutan yang selama ini dipakai.
#
# Prinsip yang dipatok:
#   - TIDAK ADA auto-approve konten ke siswa di sini. Graph ini hanya
#     mengurutkan/menyarankan (Fase 4 advisory + prioritas rekomendasi),
#     tidak mengunci akses. Setiap edge membawa source + confidence +
#     rationale sehingga tidak pernah dibaca sebagai kebenaran mutlak.
#   - Judul generik (mis. judul bagian yang sama dengan nama materi, atau
#     frasa yang muncul di hampir semua bagian) DIABAIKAN sebagai bukti
#     rujukan, karena akan menghasilkan edge palsu.
#   - SIKLUS DITOLAK: A -> B -> A tidak boleh terjadi. Edge dengan bukti
#     terkuat dipertahankan; yang menutup siklus dibuang dan dilaporkan.
#
# Graph dihitung saat dibutuhkan (tidak disimpan). Tidak ada tabel yang
# bisa basi ketika guru mengubah konten.
# ============================================================
from collections import defaultdict

from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.material_content import MaterialContent

REFERENCE_SOURCE = 'reference'
SIMILARITY_SOURCE = 'similarity'
POSITION_SOURCE = 'position'

# Bukti rujukan judul dianggap pasti bila cocok persis.
REFERENCE_CONFIDENCE = 0.9
# Ambang kemiripan isi agar sebuah pasangan dianggap berhubungan.
SIMILARITY_MIN = 0.30
# Maksimal prasyarat dari kemiripan per bagian (top-N), supaya graph tidak
# berubah jadi jaring kusut.
SIMILARITY_MAX_PREREQS = 2
# Batas total prasyarat per bagian.
MAX_PREREQUISITES_PER_SECTION = 3
# Judul dianggap generik bila muncul di lebih dari rasio ini dari seluruh
# bagian - artinya ia nama topik, bukan rujukan ke sebuah bagian. Rasio
# hanya dipercaya bila kemunculannya benar-benar banyak (>= 3 bagian),
# supaya korpus kecil (2-3 bagian) tidak salah menuduh judul yang sah.
GENERIC_TITLE_RATIO = 0.4
GENERIC_TITLE_MIN_HITS = 3
# Judul lebih pendek dari ini terlalu umum untuk dijadikan bukti rujukan.
MIN_TITLE_LEN = 8


def _content_text(data):
    """Gabungkan seluruh nilai string pada `data` menjadi satu teks."""
    parts = []

    def walk(value):
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(data)
    return ' '.join(parts)


def sections_with_text(material_ids=None):
    """Bagian + teks kontennya, untuk dipakai sebagai input graph.

    Mengembalikan list of dict: id, title, material_id, material_title,
    position, text.
    """
    query = MaterialSection.query
    if material_ids is not None:
        ids = [int(m) for m in material_ids]
        if not ids:
            return []
        query = query.filter(MaterialSection.material_id.in_(ids))
    sections = query.order_by(
        MaterialSection.material_id, MaterialSection.position).all()
    if not sections:
        return []

    titles = {m.id: m.title for m in Material.query.all()}
    sec_ids = [s.id for s in sections]
    chunks = defaultdict(list)
    for c in MaterialContent.query.filter(
            MaterialContent.section_id.in_(sec_ids)).all():
        chunks[c.section_id].append(_content_text(c.data))

    return [{
        'id': s.id,
        'title': s.title,
        'material_id': s.material_id,
        'material_title': titles.get(s.material_id),
        'position': s.position,
        'text': ' '.join(chunks.get(s.id, [])),
    } for s in sections]


def _is_generic_title(title, material_title, all_texts):
    """Judul yang terlalu umum untuk dijadikan bukti rujukan."""
    t = (title or '').strip().lower()
    if len(t) < MIN_TITLE_LEN:
        return True
    if material_title and t == (material_title or '').strip().lower():
        return True
    if not all_texts:
        return False
    hits = sum(1 for txt in all_texts if t in (txt or '').lower())
    return hits >= GENERIC_TITLE_MIN_HITS and (hits / len(all_texts)) > GENERIC_TITLE_RATIO


def _reference_edges(sections):
    """(confidence, a, b, source, rationale) bila b menyebut judul a."""
    import re
    all_texts = [s['text'] for s in sections]
    out = []
    for a in sections:
        if _is_generic_title(a['title'], a['material_title'], all_texts):
            continue
        pattern = re.compile(
            r'(?<!\w)' + re.escape(a['title'].strip().lower()) + r'(?!\w)')
        for b in sections:
            if a['id'] == b['id'] or not b['text']:
                continue
            # Dalam materi yang sama, rujukan harus mengarah ke depan. Bagian
            # pembuka yang menyebut judul bagian lanjutan bukan bukti bahwa
            # bagian lanjutan itu prasyaratnya - arahnya terbalik.
            if a['material_id'] == b['material_id'] and a['position'] >= b['position']:
                continue
            if pattern.search(b['text'].lower()):
                out.append((
                    REFERENCE_CONFIDENCE, a['id'], b['id'], REFERENCE_SOURCE,
                    f'Bagian ini menyebut "{a["title"]}" secara langsung'))
    return out


def _similarity_edges(sections):
    """(confidence, a, b, source, rationale) untuk isi yang mirip.

    Hanya se-materi dan arah dari posisi (lebih dulu -> kemudian), karena
    untuk pasangan beda materi tidak ada dasar menentukan mana yang dulu.
    """
    if len(sections) < 2:
        return []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except Exception:
        return []

    corpus = [s['text'] or '' for s in sections]
    if sum(1 for c in corpus if c.strip()) < 2:
        return []
    try:
        matrix = TfidfVectorizer().fit_transform(corpus)
    except ValueError:
        return []
    sim = cosine_similarity(matrix)

    per_target = defaultdict(list)
    n = len(sections)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a, b = sections[i], sections[j]
            if a['material_id'] != b['material_id']:
                continue
            if not (a['position'] < b['position']):
                continue
            score = float(sim[i][j])
            if score >= SIMILARITY_MIN:
                per_target[b['id']].append((score, a))

    out = []
    for target_id, candidates in per_target.items():
        candidates.sort(key=lambda c: -c[0])
        for score, a in candidates[:SIMILARITY_MAX_PREREQS]:
            out.append((
                score, a['id'], target_id, SIMILARITY_SOURCE,
                f'Isi mirip dengan "{a["title"]}" ({score:.2f}) dan '
                f'posisinya lebih dulu'))
    return out


def _reaches(adjacency, source, target):
    """Apakah `target` bisa dicapai dari `source` (deteksi siklus)."""
    stack = [source]
    seen = set()
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adjacency.get(node, ()))
    return False


def build_graph(sections):
    """Graph prasyarat dari daftar bagian (`sections_with_text`).

    Mengembalikan dict:
      edges          : {section_id: [edge, ...]}
      by_section     : sama, dijamin ada (list kosong bila tak ada)
      sections       : {section_id: info bagian}
      dropped_cycles : edge yang dibuang karena menutup siklus
      source_counts  : jumlah edge per sumber bukti
      used_position  : jumlah bagian yang jatuh ke cadangan posisi
    """
    candidates = _reference_edges(sections) + _similarity_edges(sections)
    # Bukti rujukan didahulukan, lalu confidence tertinggi.
    candidates.sort(key=lambda c: (c[3] != REFERENCE_SOURCE, -c[0]))

    adjacency = defaultdict(list)
    edges = defaultdict(list)
    dropped = []
    has_prerequisite = set()

    for confidence, a, b, source, rationale in candidates:
        if len(edges[b]) >= MAX_PREREQUISITES_PER_SECTION:
            continue
        if any(e['prerequisite_section_id'] == a for e in edges[b]):
            continue
        if _reaches(adjacency, b, a):
            dropped.append({'from': a, 'to': b, 'source': source,
                            'reason': 'menutup siklus'})
            continue
        adjacency[a].append(b)
        edges[b].append({
            'prerequisite_section_id': a,
            'source': source,
            'confidence': round(confidence, 3),
            'rationale': rationale,
        })
        has_prerequisite.add(b)

    # Cadangan posisi: hanya untuk bagian yang belum punya prasyarat.
    used_position = 0
    by_material = defaultdict(list)
    for s in sections:
        by_material[s['material_id']].append(s)
    for s in sections:
        if s['id'] in has_prerequisite:
            continue
        siblings = sorted(by_material[s['material_id']], key=lambda x: x['position'])
        order = [x['id'] for x in siblings]
        idx = order.index(s['id'])
        if idx == 0:
            continue
        prev = siblings[idx - 1]
        if _reaches(adjacency, s['id'], prev['id']):
            dropped.append({'from': prev['id'], 'to': s['id'],
                            'source': POSITION_SOURCE,
                            'reason': 'menutup siklus'})
            continue
        adjacency[prev['id']].append(s['id'])
        edges[s['id']].append({
            'prerequisite_section_id': prev['id'],
            'source': POSITION_SOURCE,
            'confidence': None,
            'rationale': 'Bagian tepat sebelumnya dalam urutan materi',
        })
        used_position += 1

    source_counts = defaultdict(int)
    for edge_list in edges.values():
        for e in edge_list:
            source_counts[e['source']] += 1

    return {
        'edges': dict(edges),
        'by_section': {s['id']: edges.get(s['id'], []) for s in sections},
        'sections': {s['id']: s for s in sections},
        'dropped_cycles': dropped,
        'source_counts': dict(source_counts),
        'used_position': used_position,
    }


def graph_for_materials(material_ids):
    """Bangun graph untuk sekumpulan materi (boleh lintas materi)."""
    return build_graph(sections_with_text(material_ids))


def prerequisites_of_section(section_id, graph):
    """Daftar prasyarat sebuah bagian (list kosong bila tidak ada)."""
    return graph.get('by_section', {}).get(int(section_id), [])
