# ============================================================
# KNOWLEDGE GRAPH PRASYARAT (otomatis) - Fase 4e.
#
# Fitur ini bikin sistem bisa menentukan "bagian mana yang harus
# dipelajari dulu" TANPA guru mengisi apa pun. Edge diturunkan dari
# bukti yang benar-benar ada di konten bagian:
#   1. rujukan judul persis (bukti literal),
#   2. kemiripan isi (TF-IDF cosine, arah dari posisi),
#   3. cadangan urutan posisi bila dua sumber di atas kosong.
#
# Prinsip yang dipatok test ini:
#   - judul generik (terlalu pendek / sama dengan nama materi / muncul
#     di hampir semua bagian) TIDAK dijadikan bukti rujukan,
#   - rujukan se-materi harus mengarah ke depan (tidak boleh mundur),
#   - SIKLUS selalu ditolak dan dilaporkan,
#   - bagian tanpa bukti tetap punya prasyarat = bagian sebelumnya,
#   - setiap edge membawa source + confidence + rationale (transparan),
#   - Fase 4 memakai graph ini untuk SEMUA prasyarat (bisa banyak &
#     lintas materi), tapi tetap advisory: tidak mengunci akses.
#
# Bagian 0 & 1 murni fungsi (tanpa database). Bagian 2 memakai
# app + database nyata dengan fixture miliknya sendiri.
# ============================================================
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import create_app  # noqa: E402
from src.config.database import db  # noqa: E402
from src.services import prerequisite_service as ps  # noqa: E402
from src.services.learning_analytics_service import (  # noqa: E402
    _apply_prerequisites,
)
from src.models.user import User  # noqa: E402
from src.models.course import Course  # noqa: E402
from src.models.enrollment import Enrollment  # noqa: E402
from src.models.material import Material  # noqa: E402
from src.models.material_section import MaterialSection  # noqa: E402
from src.models.material_content import MaterialContent  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402

STAMP = 'zzprereq'
results = []
created = {}


def check(name, cond, extra=""):
    ok = bool(cond)
    results.append((name, ok, extra))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}", extra or "")
    return ok


def token_for(user):
    return create_access_token(identity=str(user.id))


def is_acyclic(by_section):
    """True bila graph prasyarat tidak punya siklus (DFS)."""
    color = {}

    def dfs(node):
        color[node] = 1
        for edge in by_section.get(node, []):
            nxt = edge['prerequisite_section_id']
            if color.get(nxt) == 1:
                return False
            if color.get(nxt) is None and not dfs(nxt):
                return False
        color[node] = 2
        return True

    return all(dfs(n) for n in list(by_section) if color.get(n) is None)


def sources_to(section_id, graph):
    return {e['source'] for e in graph['by_section'].get(section_id, [])}


def sec(uid, title, position, text, material_id, material_title='Materi Uji'):
    return {'id': uid, 'title': title, 'position': position,
            'text': text, 'material_id': material_id,
            'material_title': material_title}


# ============================================================
# BAGIAN 0 - ALGORITMA build_graph (tanpa database)
# ============================================================
def part0_build_graph():
    print('\n[0] GRAPH - ATURAN DASAR (fungsi murni)')

    # 0a. rujukan judul persis se-materi yang mengarah ke depan.
    g = ps.build_graph([
        sec(1, 'Fotosintesis Tumbuhan', 0, 'klorofil cahaya air', 10),
        sec(2, 'Reaksi Terang dan Gelap', 1,
            'Bagian Fotosintesis Tumbuhan menjelaskan klorofil', 10),
    ])
    ref = [e for e in g['by_section'][2] if e['source'] == ps.REFERENCE_SOURCE]
    check('0a. rujukan judul persis menghasilkan edge reference',
          len(ref) == 1
          and ref[0]['prerequisite_section_id'] == 1
          and ref[0]['confidence'] == ps.REFERENCE_CONFIDENCE
          and bool(ref[0]['rationale']),
          str(ref))

    # 0b. rujukan mundur se-materi TIDAK dijadikan prasyarat.
    g = ps.build_graph([
        sec(2, 'Pendahuluan Biologi', 0,
            'lihat penjelasan Fotosintesis Tumbuhan', 10),
        sec(1, 'Fotosintesis Tumbuhan', 1, '', 10),
    ])
    all_ref = [e for s, e in g['edges'].items() for e in e
               if e['source'] == ps.REFERENCE_SOURCE]
    check('0b. rujukan mundur se-materi ditolak', not all_ref, str(all_ref))

    # 0c. judul pendek/generik TIDAK dijadikan bukti rujukan.
    g = ps.build_graph([
        sec(1, 'Sel', 0, '', 10),
        sec(2, 'Organel Sel Tumbuhan', 1, 'membahas Sel dan organelnya', 10),
    ])
    check('0c. judul pendek (generik) tidak jadi bukti rujukan',
          ps.REFERENCE_SOURCE not in sources_to(2, g),
          str(sources_to(2, g)))

    # 0d. judul yang muncul di hampir semua bagian juga dianggap generik.
    secs = [sec(i + 1, f'Topik Spesifik {i}', i,
                'Biologi Umum dibahas di sini', 10) for i in range(5)]
    secs[0]['title'] = 'Biologi Umum'  # muncul di 5 dari 5 teks
    g = ps.build_graph(secs)
    ref_total = sum(1 for e in g['edges'].values() for x in e
                    if x['source'] == ps.REFERENCE_SOURCE)
    check('0d. judul yang terlalu umum (muncul di >40% bagian) diabaikan',
          ref_total == 0, str(ref_total))

    # 0e. kemiripan isi -> edge similarity (se-materi, arah dari posisi).
    body = 'klorofil cahaya air karbon dioksida glukosa fotosintesis'
    g = ps.build_graph([
        sec(1, 'Pengantar Fotosintesis', 0, body, 10),
        sec(2, 'Proses Fotosintesis', 1, body, 10),
    ])
    check('0e. isi mirip menghasilkan edge similarity',
          ps.SIMILARITY_SOURCE in sources_to(2, g),
          str(sources_to(2, g)))

    # 0f. siklus lintas materi ditolak & dilaporkan.
    g = ps.build_graph([
        sec(1, 'Klorofil dan Cahaya', 0, 'membahas Pigmen Hijau Daun', 10, 'MA'),
        sec(2, 'Pigmen Hijau Daun', 0, 'membahas Klorofil dan Cahaya', 20, 'MB'),
    ])
    check('0f. siklus ditolak dan dilaporkan',
          len(g['dropped_cycles']) >= 1 and is_acyclic(g['by_section']),
          str(g['dropped_cycles']))

    # 0g. cadangan urutan posisi bila tidak ada bukti lain.
    g = ps.build_graph([
        sec(1, 'Bagian Satu', 0, '', 10),
        sec(2, 'Bagian Dua', 1, '', 10),
        sec(3, 'Bagian Tiga', 2, '', 10),
    ])
    check('0g. cadangan posisi: bagian tanpa bukti memakai bagian sebelumnya',
          ps.POSITION_SOURCE in sources_to(2, g)
          and ps.POSITION_SOURCE in sources_to(3, g)
          and g['by_section'][1] == []
          and g['used_position'] == 2,
          str(g['used_position']))

    # 0h. batas maksimum prasyarat per bagian dihormati.
    secs = [sec(i, f'Topik Unik Nomor {i}', i - 1, '', 10)
            for i in range(1, 5)]
    secs.append(sec(5, 'Rangkuman Semua', 4,
                    'membahas Topik Unik Nomor 1, Topik Unik Nomor 2, '
                    'Topik Unik Nomor 3, dan Topik Unik Nomor 4', 10))
    g = ps.build_graph(secs)
    check('0h. maksimum prasyarat per bagian dihormati',
          len(g['by_section'][5]) == ps.MAX_PREREQUISITES_PER_SECTION,
          str(len(g['by_section'][5])))


# ============================================================
# BAGIAN 1 - _apply_prerequisites (advisory, tanpa database)
# ============================================================
def part1_advisory():
    print('\n[1] ADVISORY - BANYAK PRASYARAT & LINTAS MATERI')

    def graph_with(prereqs):
        return {
            'by_section': {2: prereqs},
            'sections': {p['prerequisite_section_id']: {
                'title': f"Bagian {p['prerequisite_section_id']}",
                'material_id': p.get('_mat', 10),
                'material_title': 'MATERI A',
            } for p in prereqs},
        }

    def edge(pid, mat=10):
        return {'prerequisite_section_id': pid,
                'source': ps.REFERENCE_SOURCE, 'confidence': 0.9,
                'rationale': 'bukti', '_mat': mat}

    def row(material_id=20):
        return {'section_id': 2, 'title': 'Bagian B', 'material_id': material_id,
                'position': 0, 'status': 'READY', 'score': 50.0,
                'answered': 3, 'correct': 1, 'wrong': 2}

    # 1a. semua prasyarat tuntas -> met True, tanpa saran.
    rows = [row()]
    _apply_prerequisites(rows, graph_with([edge(1)]),
                         {1: {'status': 'READY', 'score': 80.0, 'title': 'Bagian 1'}})
    check('1a. prasyarat tuntas -> met True tanpa saran',
          rows[0]['prerequisite_met'] is True and rows[0]['advisory'] is None,
          str(rows[0]['advisory']))

    # 1b. prasyarat di bawah ambang -> met False + saran menyebut bagiannya.
    rows = [row()]
    _apply_prerequisites(rows, graph_with([edge(1)]),
                         {1: {'status': 'READY', 'score': 40.0, 'title': 'Bagian 1'}})
    check('1b. prasyarat belum tuntas -> met False + saran',
          rows[0]['prerequisite_met'] is False
          and 'Bagian 1' in (rows[0]['advisory'] or ''),
          str(rows[0]['advisory']))

    # 1c. belum berskor -> met None, TIDAK menegur.
    rows = [row()]
    _apply_prerequisites(rows, graph_with([edge(1)]),
                         {1: {'status': 'INSUFFICIENT_DATA', 'score': None,
                              'title': 'Bagian 1'}})
    check('1c. prasyarat belum berskor -> met None tanpa saran',
          rows[0]['prerequisite_met'] is None and rows[0]['advisory'] is None,
          str(rows[0]['advisory']))

    # 1d. baris prasyarat tidak diketahui (di luar akses) -> met None.
    rows = [row()]
    _apply_prerequisites(rows, graph_with([edge(1)]), {})
    check('1d. prasyarat tak diketahui -> met None (tidak menebak)',
          rows[0]['prerequisite_met'] is None, str(rows[0]['prerequisite_met']))

    # 1e. BANYAK prasyarat: satu belum tuntas -> met False, saran menunjuk itu.
    rows = [row()]
    _apply_prerequisites(rows, graph_with([edge(1), edge(3)]),
                         {1: {'status': 'READY', 'score': 90.0, 'title': 'Bagian 1'},
                          3: {'status': 'READY', 'score': 20.0, 'title': 'Bagian 3'}})
    check('1e. banyak prasyarat: satu gagal -> met False + saran menunjuk yang gagal',
          rows[0]['prerequisite_met'] is False
          and 'Bagian 3' in (rows[0]['advisory'] or '')
          and len(rows[0]['prerequisites']) == 2,
          str(rows[0]['advisory']))

    # 1f. prasyarat lintas materi: saran menyebut nama materi asal.
    rows = [row(material_id=20)]
    _apply_prerequisites(rows, graph_with([edge(1, mat=10)]),
                         {1: {'status': 'READY', 'score': 10.0, 'title': 'Bagian 1',
                              'material_id': 10}})
    check('1f. saran prasyarat lintas materi menyebut materi asal',
          'MATERI A' in (rows[0]['advisory'] or ''),
          str(rows[0]['advisory']))


# ============================================================
# BAGIAN 2 - INTEGRASI (app + database nyata)
# ============================================================
def make_fixture():
    teacher = User(email=f'{STAMP}@test.local', name='Prasyarat Guru',
                   role='teacher')
    other = User(email=f'{STAMP}.other@test.local', name='Prasyarat Guru Lain',
                 role='teacher')
    student = User(email=f'{STAMP}.student@test.local', name='Prasyarat Murid',
                   role='student')
    db.session.add_all([teacher, other, student])
    db.session.flush()

    course = Course(name=f'{STAMP} kelas', teacher_id=teacher.id)
    db.session.add(course)
    db.session.flush()
    db.session.add(Enrollment(student_id=student.id, course_id=course.id))
    db.session.flush()

    mat_a = Material(title='Materi Prasyarat A', course_id=course.id,
                     teacher_id=teacher.id, status='published', topic='PA')
    mat_b = Material(title='Materi Prasyarat B', course_id=course.id,
                     teacher_id=teacher.id, status='published', topic='PB')
    db.session.add_all([mat_a, mat_b])
    db.session.flush()

    a1 = MaterialSection(material_id=mat_a.id, title='Fotosintesis Tumbuhan',
                         position=0)
    a2 = MaterialSection(material_id=mat_a.id, title='Reaksi Terang dan Gelap',
                         position=1)
    b1 = MaterialSection(material_id=mat_b.id, title='Praktikum Daun',
                         position=0)
    db.session.add_all([a1, a2, b1])
    db.session.flush()

    db.session.add_all([
        MaterialContent(section_id=a1.id, type='text', position=0,
                        data={'content': 'klorofil cahaya air fotosintesis'}),
        MaterialContent(section_id=a2.id, type='text', position=0,
                        data={'content': 'seperti pada bagian Fotosintesis '
                                         'Tumbuhan, reaksi terang memakai cahaya'}),
        MaterialContent(section_id=b1.id, type='text', position=0,
                        data={'content': 'praktikum menguji Fotosintesis '
                                         'Tumbuhan dengan daun'}),
    ])
    db.session.commit()
    created.update(teacher=teacher, other=other, student=student,
                   course=course, mat_a=mat_a, mat_b=mat_b, a1=a1, a2=a2, b1=b1)


def drop_fixture():
    for key in ('a1', 'a2', 'b1'):
        s = created.get(key)
        if s is not None:
            MaterialContent.query.filter_by(section_id=s.id).delete()
    db.session.flush()
    for key in ('a1', 'a2', 'b1'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    for key in ('mat_a', 'mat_b'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    if created.get('course') is not None:
        # Course.enrollments memakai cascade delete-orphan; enrollment ikut
        # terhapus bersama course, jadi tidak dihapus terpisah (menghindari
        # peringatan hapus ganda).
        db.session.delete(created['course'])
    for key in ('teacher', 'other', 'student'):
        if created.get(key) is not None:
            db.session.delete(created[key])
    db.session.commit()


def part2_integration(app):
    print('\n[2] INTEGRASI - ENDPOINT GURU & WIRING FASE 4')
    make_fixture()
    client = app.test_client()
    h_t = {'Authorization': f'Bearer {token_for(created["teacher"])}'}
    h_o = {'Authorization': f'Bearer {token_for(created["other"])}'}
    h_s = {'Authorization': f'Bearer {token_for(created["student"])}'}
    mat_a = created['mat_a']

    try:
        r = client.get(f'/api/teacher/materials/{mat_a.id}/prerequisites',
                       headers=h_t)
        check('2a. endpoint guru 200', r.status_code == 200, r.text[:200])
        d = r.get_json() or {}
        check('2b. endpoint melaporkan metode + advisory',
              bool(d.get('method')) and d.get('advisory') is True,
              f"{d.get('method')}")
        by_title = {s['title']: s for s in d.get('sections', [])}
        a2 = by_title.get('Reaksi Terang dan Gelap', {})
        ref_edges = [e for e in a2.get('prerequisites', [])
                     if e.get('source') == ps.REFERENCE_SOURCE]
        check('2c. edge rujukan membawa judul bagian asal + alasan',
              len(ref_edges) == 1
              and ref_edges[0]['title'] == 'Fotosintesis Tumbuhan'
              and bool(ref_edges[0]['rationale']),
              str(ref_edges))

        r = client.get(f'/api/teacher/materials/{mat_a.id}/prerequisites',
                       headers=h_o)
        check('2d. guru lain ditolak 403', r.status_code == 403, str(r.status_code))

        r = client.get(f'/api/teacher/materials/{mat_a.id}/prerequisites',
                       headers=h_s)
        check('2e. siswa ditolak (endpoint guru)', r.status_code == 403,
              str(r.status_code))

        # Wiring Fase 4: endpoint siswa memuat daftar prasyarat.
        r = client.get(f'/api/student/sections/{mat_a.id}', headers=h_s)
        check('2f. endpoint siswa 200', r.status_code == 200, r.text[:200])
        sd = r.get_json() or {}
        check('2g. Fase 4 memuat daftar prasyarat per bagian',
              all('prerequisites' in s for s in sd.get('sections', [])),
              str(len(sd.get('sections', []))))
        check('2h. aturan dilaporkan memakai graph otomatis',
              'otomatis' in (sd.get('prerequisite_rule') or ''),
              str(sd.get('prerequisite_rule')))
    finally:
        drop_fixture()


def main():
    app = create_app()
    print('=' * 68)
    print('KNOWLEDGE GRAPH PRASYARAT OTOMATIS (Fase 4e)')
    print('=' * 68)

    part0_build_graph()
    part1_advisory()
    with app.app_context():
        part2_integration(app)

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print('\n' + '=' * 68)
    print(f'TOTAL: {total}  PASS: {passed}  FAIL: {total - passed}')
    if total != passed:
        print('\nGAGAL:')
        for name, ok, extra in results:
            if not ok:
                print(f'  - {name}  {extra}')
    return 0 if total == passed else 1


if __name__ == '__main__':
    sys.exit(main())
