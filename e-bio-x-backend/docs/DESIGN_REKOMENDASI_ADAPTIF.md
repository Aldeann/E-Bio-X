# Desain: Rekomendasi Adaptif untuk Siswa

Status: **sebagian terimplementasi**.
- Tahap 1: **selesai** (lihat riwayat implementasi di bawah).
- Tahap 2: **selesai** (lihat riwayat implementasi di bawah).
- Tahap 3: **selesai** (lihat riwayat implementasi di bawah).
- Tahap 4 dan soal jangkar: **draf desain**, belum ada kode.
Cakupan: rekomendasi bagian (Fase 3e), sesi latihan adaptif (Fase 3f), dan
perluasan ke fokus miskonsepsi + soal jangkar untuk pengukuran.

Keputusan yang sudah diambil:
- **Lane pengukuran: B** - jawaban latihan tetap dipakai untuk pengukuran
  tingkat global untuk sekarang, dengan batasannya dicatat (bagian 9).
  Soal jangkar / post-test per bagian jadi arah perbaikan.
- **Cakupan dekat: Tahap 1, lalu Tahap 2, lalu Tahap 3** - Tahap 4 dan soal
  jangkar menunggu keputusan lanjutan.

Riwayat implementasi Tahap 1 (kode):
- `src/ml/recommendation.py` - `recommend_sections_for_student` menambahkan
  `practice_available` + `practice_total` ke tiap baris (skor & hint) lewat
  satu panggilan `student_practice_service.approved_count_map`.
- `app/pages/student/dashboard.vue` - tombol **Latihan adaptif** membuka
  `StudentSectionPracticeModal` langsung; tombol **Buka materi** tetap ada;
  tombol latihan dinonaktifkan dengan penjelasan bila belum ada soal APPROVED.
- `test_section_recommendations.py` - blok `[1b]`: soal APPROVED membuat
  latihan tersedia, soal DRAFT tidak dihitung, semua baris membawa info
  latihan (54/54 lulus).

Riwayat implementasi Tahap 2 (kode):
- `src/ml/ml_config.py` - konstanta `FOCUS_MIN_SAMPLE = 2`,
  `FOCUS_LABEL_MAXLEN = 160`.
- `src/services/student_practice_service.py` -
  `focus_for_student_section(student, approved)` menghitung label miskonsepsi
  terlemah dari jawaban TERAKHIR per soal (konsisten dengan `latest_attempts`),
  dengan syarat `total >= FOCUS_MIN_SAMPLE` dan `salah > benar`.
  `_order_questions(..., focus_label=None)` menggeser soal berlabel fokus ke
  depan DI DALAM tiap tingkat sesi; tanpa fokus perilaku identik dengan
  sebelumnya. `session_for_section` mengirim agregat angka
  (`focus_available`/`focus_wrong`/`focus_total` + `focus_text` generik) tanpa
  teks label.
- `app/components/student/SectionPracticeModal.vue` - layar **Latihan selesai**
  menampilkan daftar soal yang masih keliru (dihitung klien dari jawaban yang
  sudah diterima) + tombol **Latihan lagi** yang memuat ulang sesi (server
  menghitung fokus ulang sehingga urutan berikutnya lebih terarah); baris fokus
  netral di banner sesi. Bila masih ada soal yang belum pernah dikerjakan,
  tombolnya menjadi **Lanjut sesi berikutnya** dan ada catatan jujur berapa
  soal yang tersisa.
- `test_student_practice.py` - blok `[13]`: fokus terdeteksi / tidak terdeteksi
  (benar > salah, 1 soal), label tidak bocor di payload, urutan kuota campuran
  bergeser ke soal fokus, ekor tetap urut id, `_order_questions` murni; blok
  `[14]`: jendela sesi + rotasi (95/95 lulus).
- Kontrak yang disepakati saat implementasi: fokus memengaruhi KUOTA CAMPURAN
  (soal fokus mengisi posisi 60/30/10 lebih dulu); sisa soal di luar kuota
  tetap ikut di belakang dengan urutan id stabil (perilaku lama dipertahankan).

Riwayat implementasi Tahap 3 (kode):
- `src/ml/ml_config.py` - konstanta `REC_COOLDOWN_HOURS = 20`,
  `REC_STALE_DAYS = 7`, `REC_COOLDOWN_FACTOR = 0.80`, `REC_STALE_BOOST = 1.05`.
- `src/ml/recommendation.py` - `_practice_recency_map(student_id)` (satu query
  berkelompok `MAX(answered_at)` per bagian); `_recency_factor(s)` netral 1.0
  tanpa data latihan; `score_section` dikali `_recency_factor`; alasan teks
  "Baru kamu latih - ulangi besok agar lebih efektif" (cooldown) dan
  "Belum kamu sentuh N hari" (stale); item saran membawa `recently_practiced`
  (bool) + `days_since_practice` (int|None).
- `app/pages/student/dashboard.vue` - catatan kecil "Baru kamu latih - ulangi
  besok agar lebih efektif." di kartu bagian yang sedang dalam cooldown.
- `test_section_recommendations.py` - blok `[7]`: aturan murni (netral tanpa
  data, cooldown menurunkan, stale menaikkan), endpoint menandai bagian yang
  baru dilarin + alasan cooldown jujur + skor < baseline tanpa recency
  (54+9 = 63/63 lulus).


Dokumen ini melengkapi `FEATURE_BAGIAN_MASTERY.md`. Ia tidak menggantinya;
yang sudah berjalan di sana tetap jadi dasar.

---

## 1. Tujuan

Mengubah rekomendasi dari sekadar *"bagian ini lemah"* menjadi *"sesi yang
menyerang kelemahan spesifik, lalu menutup lingkaran dengan saran berikutnya"*,
tanpa mengorbankan kejujuran angka.

Adaptif penuh berarti menyesuaikan empat hal:

1. **Bagian mana** yang perlu dikerjakan.
2. **Tingkat soal** yang cocok.
3. **Konsep/miskonsepsi** yang sedang jadi masalah.
4. **Kapan** harus mengulang.

Yang sudah ada: (1) dan (2). Yang ditambah: (3), lalu (4).

## 2. Prinsip yang dipegang

1. **Tidak mengarang.** Tidak ada data -> katakan belum bisa dinilai; jangan
   memberi peringkat atau label palsu.
2. **Hanya soal `APPROVED`** yang pernah disajikan ke siswa.
3. **Tidak bocor sebelum dijawab.** Kunci jawaban *dan* label miskonsepsi tidak
   dikirim ke klien sebelum siswa menjawab soal yang bersangkutan.
4. **Hanya mengurutkan** soal yang sudah ada; tidak pernah membuat soal baru.
5. **Dua lane terpisah:** lane *pengukuran* (soal sama untuk semua) dan lane
   *remediasi* (latihan pribadi) tidak boleh saling meracuni.

## 3. Baseline nyata (yang sudah berjalan)

```
Dashboard siswa
  GET /api/student/recommendations
    -> section_recommendations      (recommendation.recommend_sections_for_student, Fase 3e)
       item: {material_id, section_id, section_title, status, answered, correct,
              wrong, mastery_score, reasons, ranked, prerequisite_met, prerequisites}
    klik -> /student/materials/<mid>?section=<sid>
      SectionPracticeModal.vue
        GET /api/student/practice/<mid>/sections/<sid>
          -> session_for_section()  (student_practice_service, Fase 3f)
             urut 60/30/10 per tingkat; target = _weakest_level()
        POST .../answer -> grade() + record() -> PracticeAnswer
```

Data yang sudah tersedia (tanpa tabel baru):

- `PracticeAnswer(student_id, material_id, section_id, bank_question_id,
  selected_option, is_correct, attempt_no, question_snapshot, answered_at)`
- `QuestionBank(misconception, topic, difficulty, section_id, status, source)`
- tingkat soal terukur: `question_difficulty_service.observed_bank_batch`
  (membaca `PracticeAnswer`; **ini sumber risiko di bagian 9**)
- konfigurasi `ml_config`: `SESSION_MIX_TARGET/BELOW/ABOVE`,
  `SESSION_LEVEL_ORDER`, `MIN_DIFFICULTY_SAMPLE`, `DIFFICULTY_P_EASY/HARD`,
  `HIGH_MASTERY_CUTOFF`, `MIN_SECTION_SAMPLE`, `REC_SECTION_*`

Yang belum dipakai sebagai sinyal: `QuestionBank.misconception` dan
`PracticeAnswer.answered_at`.

## 4. Alur target

```
Dashboard (Fase 3e + practice_available)
   [Latihan adaptif]  <- langsung buka modal, tanpa lompat halaman
   v
Sesi (session_for_section)
   urut 60/30/10 per tingkat
   DI DALAM tiap tingkat: soal yang cocok miskonsepsi terlemah didahulukan
   (label dipakai diam-diam; tidak dikirim ke klien)
   v
Jawab satu per satu -> umpan balik per soal (misconception muncul di sini)
   v
Ringkasan sesi  <- dihitung di klien dari jawaban yang sudah diterima
   "Kamu masih sering keliru di soal ini: ..."
   [Latihan lagi] -> sesi baru, urutan lebih fokus
```

---

## 5. Tahap 1 - Satu alur + tombol langsung

**Tujuan:** hapus lompatan dashboard -> halaman materi -> modal.

**Status: selesai.** Rincian kode ada di riwayat implementasi pada kepala
dokumen.

### 5.1 Backend

Perluas tiap item `section_recommendations` dengan dua field murah:

| field | isi | sumber |
|---|---|---|
| `practice_available` | `bool` | `approved_count_map([...section ids...])` |
| `practice_total` | jumlah soal APPROVED | idem |

Tidak ada perhitungan berat; satu query untuk semua bagian.

### 5.2 Frontend (`app/pages/student/dashboard.vue`)

- Impor `SectionPracticeModal` ke dashboard.
- Kartu bagian lemah punya dua aksi:
  - primer **Latihan adaptif** -> buka modal (`materialId`, `sectionId`, `sectionTitle`)
  - sekunder **Buka materi** -> `openSection(s)` seperti sekarang
- Bila `practice_available === false`: tombol latihan `disabled` +
  penjelasan "belum ada soal disetujui guru".

### 5.3 Risiko

Rendah. Menyambung dua layar yang sudah ada; tidak mengubah perhitungan.

---

## 6. Tahap 2 - Fokus per miskonsepsi (inti)

**Status: selesai.** Rincian kode ada di riwayat implementasi pada kepala
dokumen. Catatan kontrak: fokus menggeser soal di **dalam kuota campuran**
(60/30/10); sisa soal di luar kuota tetap urut id stabil (perilaku lama).

### 6.1 Sinyal fokus

Untuk pasangan (siswa, bagian), hitung dari **jawaban terakhir per soal**
(konsisten dengan `latest_attempts`, supaya mengulang tidak menambah bukti).

```python
def focus_for_student_section(student, section, approved, by_id):
    last = {}  # bank_question_id -> PracticeAnswer terakhir
    for r in PracticeAnswer.query.filter_by(
            student_id=student.id, section_id=section.id
        ).order_by(PracticeAnswer.answered_at.asc(), PracticeAnswer.id.asc()):
        last[r.bank_question_id] = r

    agg = {}  # label miskonsepsi -> hitungan
    for bq_id, r in last.items():
        bq = by_id.get(bq_id)
        label = (bq.misconception or '').strip() if bq else ''
        if not label:                       # label kosong: jangan mengarang
            continue
        a = agg.setdefault(label, {'wrong': 0, 'correct': 0, 'total': 0, 'last_at': None})
        a['total'] += 1
        a['correct' if r.is_correct else 'wrong'] += 1
        a['last_at'] = r.answered_at

    candidates = [(lbl, a) for lbl, a in agg.items()
                  if a['total'] >= cfg.FOCUS_MIN_SAMPLE
                  and a['wrong'] > a['correct']]
    candidates.sort(key=lambda kv: (-(kv[1]['wrong'] - kv[1]['correct']),
                                    kv[1]['last_at']))
    return candidates[0] if candidates else None
```

Aturan: satu kali salah bukan pola; tidak ada label -> tidak ada fokus; mirip
dengan `score_section` yang menolak mengarang saat data kurang.

### 6.2 Pengurutan (`_order_questions`)

Perubahan hanya **di dalam tiap kelompok tingkat**; komposisi 60/30/10 tidak
diubah dan tidak ada soal yang ditambah/dihapus.

```python
def _order_questions(approved, effective, target, focus_label=None):
    ...  # pengelompokan per tingkat seperti sekarang
    def rank(bq):
        match = 1 if focus_label and (bq.misconception or '').strip() == focus_label else 0
        return (-match, bq.id)   # cocok fokus dulu, lalu id stabil
    for lvl in queues:
        queues[lvl].sort(key=rank)
    ...  # pemilihan 60/30/10 apa adanya
```

Tanpa fokus (`focus_label is None`) -> perilaku identik dengan sekarang, jadi
tes lama tetap aman.

### 6.3 Jendela sesi + rotasi (Tahap 3f lanjutan)

Satu sesi tidak lagi memuat seluruh bank bagian. `SESSION_SIZE = 10`
(`ml_config.py`) membatasi berapa soal ditampilkan sekaligus, dan bila bank
lebih besar dari jendela itu, tiap tingkat dirotasi: **soal yang belum pernah
dijawab didahulukan, lalu yang paling lama dijawab**.

- Kuota 60/30/10 dihitung dari **ukuran jendela**, bukan dari seluruh bank
  (10 -> 6/3/1). Komposisi adaptif tidak berubah, hanya skalanya.
- Rotasi memakai riwayat `PracticeAnswer` dengan `mode='practice'` saja, jadi
  jawaban asesmen diagnostik tidak dianggap "sudah dilatih" dan dua pool itu
  tetap terpisah.
- Tanpa riwayat, atau bila bank muat dalam satu jendela, urutannya persis
  seperti sebelumnya (id stabil) -> regresi aman. Soal yang tingkatnya belum
  diketahui tetap menempel di belakang komposisi, tidak ditebak tingkatnya.
- UI memberi tahu siswa secara jujur: banner "Sesi ini menampilkan X dari Y
  soal" dan tombol **Lanjut sesi berikutnya** hanya muncul bila memang masih ada
  soal yang belum pernah dikerjakan (`session.has_more`, diperbarui live pada
  respons tiap jawaban lewat `practice_total`/`practice_seen`).

### 6.3 Privasi label (keputusan penting)

Label miskonsepsi sering **membocorkan konsep benar** (mis. "virus adalah sel
hidup" -> artinya "bukan sel"). Maka:

- **Menggerakkan urutan:** ya, di server.
- **Sebelum dijawab:** **tidak dikirim.** Payload sesi hanya memuat agregat
  netral (`focus_available`, `focus_wrong`, `focus_total`) tanpa teks label.
- **Umpan balik per soal:** teks miskonsepsi muncul seperti sekarang (setelah
  dijawab).
- **Ringkasan sesi:** menampilkan daftar **soal** yang masih salah (teks soal
  yang sudah dilihat siswa), bukan label mentah.

### 6.4 Ringkasan sesi tanpa endpoint baru

`SectionPracticeModal.vue` sudah menerima tiap respons jawaban (berisi
`question_text`, `is_correct`, `misconception`). Kumpulkan di state, lalu
tampilkan di layar "Latihan selesai":

> Kamu masih sering keliru di N soal ini: ...
> [Latihan lagi] - sesi berikutnya akan lebih fokus ke sana.

Tidak ada endpoint agregat baru -> tidak ada jalur bocor tambahan.

### 6.5 Konfigurasi baru (`ml_config.py`)

```python
FOCUS_MIN_SAMPLE = 2          # minimal soal terjawab pada satu label
FOCUS_LABEL_MAXLEN = 160      # potong teks label untuk umpan balik
```

### 6.6 UI

- Banner pra-sesi: kalimat halus tanpa menyebut label -
  "Sesi ini menekankan soal yang paling sering kamu lewatkan."
- Layar selesai: daftar soal yang salah + tombol "Latihan lagi".

---

## 7. Tahap 3 - Adaptif antar-sesi (pengulangan terjadwal) ✅ selesai

Memakai `PracticeAnswer.answered_at` (satu query `MAX(answered_at)` per
bagian via `_practice_recency_map`). Langkah yang dilakukan:

- `score_section` dikali `_recency_factor(s)`:
  - `practice_hours < REC_COOLDOWN_HOURS (20 jam)` dan masih lemah
    (pasti, karena bagian terkuasai tak pernah sampai ke `score_section`)
    -> dikali `REC_COOLDOWN_FACTOR = 0.80`: "ulangi besok", jangan didorong
    dua kali;
  - `practice_days >= REC_STALE_DAYS (7 hari)` -> dikali
    `REC_STALE_BOOST = 1.05`: bagian lemah lama tak disentuh naik prioritas;
  - tanpa data latihan untuk bagian itu -> netral 1.0 (tidak mengarang).
- Alasan jujur di kartu: **"Baru kamu latih - ulangi besok agar lebih
  efektif"** (cooldown), **"Belum kamu sentuh N hari"** (stale).
- Item saran baru: `recently_practiced` (bool) + `days_since_practice`
  (int | null); UI menampilkan catatan cooldown di kartu.
- Satu suku `recency_factor` transparan dengan faktor eksplisit di
  `ml_config.py` (bisa diaudit, bukan model); faktor dipakai sebagai
  **pengali**, bukan bobot tambahan di `REC_SECTION_WEIGHTS`, supaya bobot
  lama yang sudah dipakai lapangan tidak berubah maknanya.
- Mengubah peringkat Fase 3e -> tes `[7]` baru di
  `test_section_recommendations.py` (9 kasus, semuanya lulus).

Keputusan saat implementasi: cooldown TIDAK melarang membuka latihan (tombol
tetap bisa), hanya menurunkan prioritas + memberi tahu jujur bahwa lebih baik
menunggu; ringkasan "Latihan lagi" di dalam modal sesi tetap ada sebagai
kelanjutan sesi. "Masih lemah" adalah syarat implisit: hanya bagian di bawah
`HIGH_MASTERY_CUTOFF` yang sampai ke `score_section`.

## 8. Tahap 4 - Adaptif dalam sesi (ditunda)

Endpoint "soal berikutnya" yang menaik/menurunkan tingkat **setelah tiap
jawaban** (mirip CAT). Nilai tinggi, tetapi eksposur soal jadi tidak seimbang
dan risiko umpan-balik (bagian 9) makin tajam. Tunda sampai Tahap 1-3 stabil.

---

## 9. Risiko: umpan-balik ke pengukuran tingkat

`question_difficulty_service.observed_bank_batch` membaca `PracticeAnswer`.
Artinya jawaban latihan ikut menentukan tingkat soal, sementara pengurutan
adaptif mengubah soal mana yang dijawab siswa:

```
soal dianggap "sulit" karena dijawab siswa lemah
   -> sesi adaptif menyajikan soal itu ke siswa lemah
      -> p-value makin rendah -> makin dianggap "sulit"
```

Kecil untuk bagian yang <= 10 soal (seluruh bank tersaji dalam satu sesi;
`SESSION_SIZE = 10`), nyata untuk bagian yang lebih besar. Batas jendela tidak
memutus umpan balik di atas - ia hanya mengubah cakupan SATU sesi. Yang membuat
paparannya merata adalah rotasinya: soal yang belum pernah dijawab didahulukan,
sehingga seluruh bank tetap terjawab lintas sesi (bukan selalu 20 soal teratas).

Pilihan:

- **A. Pisahkan lane:** jawaban latihan hanya untuk diagnosis siswa sendiri;
  tingkat global dari kuis + interaktif (+ post-test). Paling bersih secara
  metodologis, tetapi mengubah perilaku Fase 3f/g dan tesnya.
- **B. Pertahankan sekarang, catat batasannya**, siapkan **soal jangkar**
  (bagian 10) untuk membenahi pengukuran.
- **C. Abaikan.** Tidak disarankan.

**Saran sekarang: B**, dengan soal jangkar sebagai arah perbaikan.

---

## 10. Soal jangkar (anchor items)

### 10.1 Definisi

Sekumpulan kecil soal yang **selalu dijawab semua siswa**, tidak peduli level
mereka. Karena tidak ada seleksi "siapa yang dapat soal ini", p-value-nya
bersih dan bisa dipakai untuk menetapkan tingkat soal.

### 10.2 Membagi tanggung jawab

| Jenis soal | Jawabannya dipakai untuk |
|---|---|
| **Soal jangkar** (dijawab semua) | menetapkan tingkat soal (pengukuran) |
| **Soal kolam adaptif** (dipilih per level) | hanya diagnosis + fokus siswa sendiri |

Dengan pemisahan ini, kolam adaptif bebas diacak tanpa merusak pengukuran.

### 10.3 Dua bentuk penerapan

**Ringan - tanda `is_anchor` di `question_bank`**

- Tambah kolom `is_anchor` (boolean, default `false`) lewat daftar migrasi
  manual di `src/config/database.py` (seperti `misconception` dulu).
- Per bagian, pilih 3-5 soal yang selalu disisipkan ke depan sesi **semua**
  siswa.
- `observed_bank_batch` hanya membaca jawaban `is_anchor = true` untuk label
  global.
- Kelemahan: hanya siswa yang membuka latihan yang menjawab; bias "siapa yang
  rajin" masih ada, walau jauh lebih kecil.

**Kuat - post-test per bagian (tujuan)**

- Memakai `Quiz.section_id` yang **sudah ada**.
- Post-test pendek per bagian berisi soal jangkar, sama untuk semua siswa,
  dikerjakan setelah bagian itu.
- Jawaban latihan **tidak lagi** dipakai untuk label global.
- Ini melunasi utang metodologis Fase 3f/g dan menyatukan lane pengukuran.

### 10.4 Cara memilih soal jangkar

- 3-5 per bagian, sebaran kasar 1 mudah / 1-3 sedang / 1 sulit.
- Pilih yang **membeda-bedakan**, bukan yang terlalu mudah/sulit untuk semua.
- Jangan sering diedit; bila isi soal berubah, kesulitannya berubah dan
  pengukuran lamanya tidak berlaku lagi.
- Bila mau diganti, ganti perlahan dan pertahankan sebagian soal lama sebagai
  penghubung. Ambang `MIN_DIFFICULTY_SAMPLE = 20` siswa berbeda tetap berlaku.

### 10.5 Konsekuensi jujur

- Soal non-jangkar kehilangan label terukur -> jatuh ke label guru; karena guru
  sekarang tidak mengisi tingkat (Fase 3g), banyak menjadi "Belum ditentukan".
- Soal tanpa label tetap ikut sesi (di belakang), tidak ada yang hilang.
- Peningkatan lanjutan (estimasi soal non-jangkar lewat pencocokan ke jangkar /
  IRT linking) ditunda.

Pertukarannya: **kepercayaan angka naik, cakupan label turun.** Ini disengaja:
lebih baik sedikit angka yang bisa dipercaya daripada banyak angka menyesatkan.

### 10.6 Urutan pengerjaan minimal

| Langkah | Isi | Berat |
|---|---|---|
| 1 | kolom `is_anchor` + pilih anchor per bagian | kecil |
| 2 | `observed_bank_batch` hanya baca jawaban anchor untuk label global | kecil |
| 3 | sisipkan anchor ke depan tiap sesi | kecil |
| 4 | post-test per bagian (pakai `Quiz.section_id`) | sedang |
| 5 | hentikan pemakaian jawaban latihan untuk label global | kecil (setelah 4) |

Langkah 1-3 sudah memutus sebagian besar lingkaran; langkah 4 yang membuatnya
benar-benar bersih.

---

## 11. Kontrak API: sebelum -> sesudah

| Endpoint | Sebelum | Sesudah (usulan) |
|---|---|---|
| `GET /api/student/recommendations` | item tanpa info latihan | **+ `practice_available`, `practice_total` (selesai, Tahap 1)**; **+ `recently_practiced`, `days_since_practice` (selesai, Tahap 3)** |
| `GET .../sections/<sid>` | `session{basis, target_level, mix, note}` | **+ `session.focus_available/focus_wrong/focus_total/focus_text` (selesai, Tahap 2; tanpa teks label)** |
| `POST .../answer` | tidak berubah | tidak berubah |
| ringkasan sesi | tidak ada | **dihitung klien dari respons jawaban (selesai, Tahap 2; tanpa endpoint)** |

Tidak ada endpoint atau tabel baru untuk Tahap 1-2. Perubahan
mundur-kompatibel: konsumen lama mengabaikan field tambahan.

---

## 12. Rencana uji

Status per item (item 1-7 dari Tahap 2 sudah lulus di blok `[13]`
`test_student_practice.py`; item 6 sudah lulus di `[1b]`
`test_section_recommendations.py`):

1. Fokus hanya muncul bila `total >= FOCUS_MIN_SAMPLE` dan `wrong > correct`. ✅
2. Satu kali salah -> bukan fokus. ✅
3. Label miskonsepsi kosong -> tidak ada fokus; urutan identik dengan sekarang. ✅
4. Fokus mengubah urutan **di dalam** tingkat; jumlah per tingkat 60/30/10 tetap. ✅
5. Payload sesi **tidak** memuat teks label miskonsepsi. ✅
6. `practice_available`/`practice_total` benar (termasuk 0 soal). ✅
7. Regresi: tanpa data fokus, output `session` identik dengan sebelum perubahan. ✅
8. Soal jangkar (bila dikerjakan): label global hanya dari jawaban anchor.
   (belum ada kode; menunggu Tahap A)
9. Tahap 3 murni: tanpa data latihan -> netral; baru dilarin (< cooldown) ->
   skor `* 0.80`; lama tak disentuh (>= 7 hari) -> `* 1.05`; pernah latih tapi
   wajar -> netral. ✅ (blok `[7]`)
10. Tahap 3 endpoint: bagian yang baru dilarin ditandai `recently_practiced`,
    alasan "ulangi besok" muncul, skor < baseline tanpa recency. ✅ (blok `[7]`)

---

## 13. Rilis bertahap

| Tahap | Isi | Risiko | Sentuh | Status |
|---|---|---|---|---|
| 1 | tombol langsung + `practice_available` | rendah | 1 controller, 1 vue | ✅ selesai |
| 2 | fokus miskonsepsi (urutan + ringkasan klien) | sedang | service sesi, modal | ✅ selesai |
| 3 | pengulangan terjadwal | sedang | scoring Fase 3e | ✅ selesai |
| 4 | adaptif per-item | tinggi | endpoint baru | draf (tunda) |
| A | soal jangkar / post-test per bagian | sedang | model, service, alur guru+siswa | draf (belum) |

---

## 14. Keputusan yang masih terbuka

Sudah diputuskan:

1. **Lane pengukuran (bagian 9):** **B** - pertahankan sekarang, catat
   batasannya; soal jangkar / post-test per bagian jadi arah perbaikan.
2. **Tahap yang dikerjakan:** **Tahap 1, lalu Tahap 2, lalu Tahap 3**
   (semuanya selesai).
3. **Ambang fokus `FOCUS_MIN_SAMPLE = 2`:** dipakai di implementasi Tahap 2;
   bisa dinaikkan ke 3 bila lapangan menunjukkan fokus terlalu sering.
4. **Ringkasan sesi:** daftar soal yang masih salah (diputuskan; tanpa
   menyebut nama konsep agar konsep benar tidak bocor menjelang sesi berikut).
5. **Tahap 3 (pengulangan terjadwal):** **selesai** - cooldown 20 jam
   (`REC_COOLDOWN_FACTOR = 0.80`) + boost bagian lama tak disentuh
   (`REC_STALE_DAYS = 7`, `REC_STALE_BOOST = 1.05`); netral tanpa data.
   Ambang 20 jam / 7 hari bisa dikalibrasi ulang dari lapangan.

Masih terbuka:

6. **Soal jangkar:** kerjakan sekarang (langkah 1-3) atau setelah ada bagian
   dengan > 20 soal / post-test?
