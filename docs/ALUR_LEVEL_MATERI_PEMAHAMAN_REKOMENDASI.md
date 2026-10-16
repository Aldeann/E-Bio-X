# Alur: Level Materi, Tingkat Pemahaman Siswa, dan Fitur Rekomendasi

> Dokumen penjelasan untuk presentasi ke dosen. Ditulis **faktual** mengacu pada
> kode dan spesifikasi di repositori E-Bio-X. Setiap klaim penting disertai
> sumber (file:baris). Path relatif terhadap root repo `D:\Aldeann`.
>
> Inti yang perlu dipahami dosen: sistem memisahkan **dua lane** yang tidak boleh
> bercampur — **lane PENGUKURAN** (mengukur, tidak menyesuaikan) dan **lane
> REMEDIASI** (menyesuaikan, untuk memperbaiki). Pencampuran keduanya itulah
> masalah yang diselesaikan oleh fitur "level materi".

---

## 0. Ringkasan satu menit

- **Level materi** = tingkat kesulitan materi (mudah / sedang / sulit) yang
  diukur dari **set soal diagnostik tetap** (non-adaptif), bukan dari latihan
  adaptif. Direpresentasikan `materials.difficulty` (deklarasi guru) vs
  `difficulty_observed` (hasil ukur).
- **Tingkat pemahaman siswa** punya **dua lapisan**:
  1. **Penguasaan per bagian** (rule-based, transparan): label **Kurang / Cukup /
     Baik / Baik Sekali**, dari rasio jawaban benar nyata per bagian.
  2. **Profil belajar ML**: Decision Tree (label **Perlu Penguatan / Cukup / Baik
     / Sangat Baik**) + K-Means (5 tipe kelompok belajar).
- **Fitur rekomendasi**: rekomendasi materi & **bagian**, **Langkah Berikutnya
  (Next Best Action)**, **sesi latihan adaptif** (jendela 10 soal, campuran
  60/30/10, rotasi), **fokus miskonsepsi**, **prasyarat antar-bagian (advisory)**,
  dan **dashboard dampak**. Ranker Learning-to-Rank sudah dibuat tetapi
  **sengaja tidak dipakai** karena belum terbukti lebih baik (jujur, lihat §5.3).

---

## 1. Peta besar — tiga lapisan & dua lane

```
                    ┌─────────────────────────────────────────────┐
                    │                SISWA BELAJAR                 │
                    └───────────────┬─────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────────────┐
        ▼                           ▼                                   ▼
┌──────────────────┐   ┌────────────────────────┐   ┌────────────────────────────┐
│ LANE PENGUKURAN  │   │   LANE REMEDIASI       │   │   LAPISAN PEMAHAMAN         │
│ (tetap, adil)    │   │   (menyesuaikan)       │   │   (diagnosis)               │
├──────────────────┤   ├────────────────────────┤   ├────────────────────────────┤
│ • Asesmen        │   │ • Sesi latihan adaptif │   │ • Penguasaan per bagian      │
│   Diagnostik     │   │   (60/30/10, jendela10)│   │   (Kurang..Baik Sekali)     │
│   (purpose=      │   │ • Fokus miskonsepsi    │   │ • Profil ML (DT + KMeans)    │
│   diagnostic)    │   │ • Rekomendasi bagian & │   │                              │
│                  │   │   materi, NBA          │   │                              │
└────────┬─────────┘   └───────────┬────────────┘   └─────────────┬──────────────┘
         │                         │                              │
         ▼                         │                              │
   ┌───────────────┐               │                              │
   │ LEVEL MATERI  │               │                              │
   │ (mudah/sedang │               │                              │
   │  /sulit)      │               │                              │
   └───────┬───────┘               │                              │
           └───────────┬───────────┴──────────────┬───────────────┘
                       ▼                          ▼
              ┌──────────────────────────────────────────┐
              │            FITUR REKOMENDASI              │
              │  materi • bagian • NBA • latihan adaptif  │
              └──────────────────────────────────────────┘
```

**Aturan emas:** jawaban diagnostik dan jawaban latihan disimpan di tabel yang
sama (`practice_answers`) tetapi ditandai kolom **`mode`** (`'diagnostic'` vs
`'practice'`) — jadi dua pool tidak pernah saling menyerap.
Sumber: `src/models/practice_answer.py:35-45`, `src/models/question_bank.py:46-49`.

---

## 2. ALUR LEVEL MATERI

### 2.1 Masalah yang diselesaikan

Dulu `materials.difficulty` hanya diisi dari data seed/guru. Kalau materi dinilai
dari jawaban **latihan adaptif**, materi jadi tampak lebih sulit daripada
kenyataan — karena latihan sengaja memberi soal yang menantang (campuran
60/30/10). Solusinya: ukur dari **set diagnostik non-adaptif**.
Sumber: `docs/spesifikasi-level-materi-diagnostik.md:13-26`.

### 2.2 Alur langkah (dari guru menyiapkan sampai label muncul)

```
(1) GURU menyiapkan soal
    ├─ soal latihan  → purpose = 'practice'   (masuk sesi adaptif)
    └─ soal diagnostik → purpose = 'diagnostic' (HANYA untuk mengukur)
        • wajib APPROVED, wajib punya section_id
        File: src/models/question_bank.py:24,49 ; question-bank sisi guru

(2) SISWA mengerjakan Asesmen Diagnostik per bagian
    • urutan soal TETAP (tidak menyesuaikan), non-adaptif
    • kunci jawaban tidak dikirim; maksimal 20 soal disajikan (MAX_SERVED)
    • jawaban dicatat dengan mode = 'diagnostic'
    File: controllers/practice_controller.py:500-593

(3) SERVER menghitung level materi (material_level_observed)
    a. ambil soal diagnostik APPROVED dari bagian-bagian materi
    b. ambil jawaban mode='diagnostic'; 1 siswa dihitung SEKALI per soal
       (memakai jawaban PERTAMA)
    c. tiap SOAL dinilai: p = benar/jawab; soal "READY" bila peserta >= 20
    d. gate: butuh >= 3 soal READY DAN >= 20 siswa berbeda
    e. bila lolos → hitung p pooled; peta ke label mudah/sedang/sulit
    f. bila belum lolos → INSUFFICIENT_DATA + alasan (jujur, tanpa mengarang)
    File: services/question_difficulty_service.py:236-342

(4) HASIL ditampilkan ke guru (deklarasi guru vs hasil ukur, berdampingan)
    • GET /api/materials/<id>/analytics → difficulty_declared, difficulty_observed
    • GET /api/teacher/analytics/materials/<id> → idem
    • UI: app/pages/teacher/materials/analytics/[id].vue (panel "Tingkat Materi")
```

### 2.3 Rumus & ambang (kode: `src/ml/ml_config.py`, `question_difficulty_service.py`)

| Hal | Nilai | Sumber |
|---|---|---|
| Ambang mudah | `p >= 0.70` | `question_difficulty_service.py:63-68` |
| Ambang sulit | `p < 0.40` | idem |
| Selain itu | sedang | idem |
| Sampel minimum per soal | 20 siswa | `ml_config.py:196` |
| Minimal soal terukur | 3 | `ml_config.py:209` |
| Minimal siswa berbeda | 20 | `ml_config.py:210` |
| Margin keyakinan | `1.96 * sqrt(p(1-p)/n)` | `question_difficulty_service.py:35-39`, `ml_config.py:197` |
| Penanda label | `basis = 'observed_diagnostic'` | `question_difficulty_service.py:329` |

Gate berurutan (semua harus lolos): `no_questions` → `items` → `students`.
Pesan jujur contoh: *"Baru 0 soal diagnostik yang terukur (perlu 3);
6 soal lain belum dijawab cukup banyak siswa."* (`:309-315`).

### 2.4 Yang penting untuk dosen

- **Diukur, bukan ditebak.** Jika data belum cukup, sistem **menolak memberi
  label** dan menyebutkan alasannya.
- **Label guru tidak pernah ditimpa.** Dua-duanya ditampilkan berdampingan:
  "deklarasi guru" vs "terukur dari set diagnostik".
  (`material_controller.py:386-389`; `analytics/[id].vue:206-231`)
- **Bias latihan adaptif dikeluarkan** dari pengukuran (hanya `mode='diagnostic'`).

### 2.5 Gerbang "wajib sebelum lanjut" (baru)

Agar pengukuran benar-benar berisi data, asesmen diagnostik dijadikan **wajib**:
siswa tidak bisa pindah bagian sebelum menuntaskan asesmen bagian itu. Muncul
sebagai **modal pemberitahuan tanpa opsi "lewati"**.
Sumber: `docs/spesifikasi-level-materi-diagnostik.md:340-386`;
`app/components/student/DiagnosticGateModal.vue`;
`app/pages/student/materials/[id].vue` (fungsi `guardNavigation`).
Data pendukung: `diagnostic_answered` + `diagnostic_required` per bagian pada
`GET /api/student/practice/<id>/sections`.

---

## 3. ALUR TINGKAT PEMAHAMAN SISWA

Ada **dua lapisan** yang sengaja dibedakan cakupannya.

### 3.1 Lapisan A — Penguasaan per bagian (rule-based, transparan)

**Sumber jawaban nyata per bagian** (`learning_analytics_service.py:345-433`):
1. **Kuis** — soal bertag `Question.section_id`; bila soal tak bertag, dipakai
   `Quiz.section_id` yang eksplisit. Soal & kuis tanpa tag **tidak dihitung**
   (lebih baik tidak dihitung daripada dipetakan ke bagian yang tak terbukti).
2. **Soal interaktif** — `StudentAnswer.section_id`.
3. **Latihan** — `PracticeAnswer.section_id`, satu soal dihitung dari jawaban
   **TERAKHIR**.

**Rumus & ambang** (`learning_analytics_service.py:362,436-461`):
```
bila answered >= 3:   skor = round(correct/answered * 100, 1)   → READY
bila answered <  3:   skor = None, status = INSUFFICIENT_DATA
                      note = "Butuh minimal 3 jawaban; baru N."
```
**Label skor** (`learning_analytics_service.py:48-62`):

| Skor | Label |
|---:|---|
| 90–100 | **Baik Sekali** |
| 75–89 | **Baik** |
| 60–74 | **Cukup** |
| 0–59 | **Kurang** |

Dipakai di: progres siswa, analitik guru per materi, dan **grid "Peta Penguasaan
Siswa × Bagian"** (guru). `section_mastery_for_student()` `:629` (siswa) dan
`section_mastery_class()` / `section_mastery_matrix()` `:670,759` (kelas/guru).

### 3.2 Lapisan B — Profil belajar ML (Decision Tree + K-Means)

**Decision Tree** (`src/ml/decision_tree.py`, `profile.py`):
- Label penguasaan (UI): **Perlu Penguatan / Cukup / Baik / Sangat Baik**
  (ambang 90/75/60/0 sama seperti lapisan A) — `ml_config.py:75-88`.
- **Penting & jujur:** label latih **bukan** hasil "deteksi ML", melainkan
  dihitung dari **aturan baseline transparan** (`baseline_label`), lalu Decision
  Tree belajar menirunya. Fitur pembentuk label **dikeluarkan** dari input agar
  tidak bocor (`decision_tree.py:1-53`; `ml_config.py:47-53,90-96`).
  Bobot baseline: `quiz_average 0.40 + material_completion_rate 0.30 +
  interactive_accuracy 0.30`.
- Ambang data: latih DT butuh ≥ 15 sampel, evaluasi andal butuh ≥ 20
  (`ml_config.py:99-103`).

**K-Means** (pengelompokan perilaku belajar):
- 5 tipe kelompok (kunci internal bahasa Inggris → tampilan Indonesia):
  High Achievement (Pencapaian Tinggi), Active Learner (Pembelajar Aktif),
  Moderate Learner (Pembelajar Sedang), Needs Support (Perlu Pendampingan),
  Low Activity (Aktivitas Rendah) — `cluster_interpreter.py:10-24`.
- Nama kelompok **diturunkan dari data centroid**, bukan dari nomor cluster
  (nomor cluster berubah antar-run) — `cluster_interpreter.py:1-7`.
- `k` dipilih dari `[2,3,4,5]` lewat silhouette; default 3 bila tak meyakinkan
  (`ml_config.py:104-106`).

**Scope diumumkan jujur:** bila model yang dipakai adalah model gabungan
(pooled) karena kelas belum punya model terlatih, hal itu dinyatakan eksplisit
di UI (bukan disembunyikan).

### 3.3 Dua lapisan berbeda — mengapa

| | Lapisan A (per bagian) | Lapisan B (ML) |
|---|---|---|
| Sifat | Deterministik, transparan | Statistik, teragregat |
| Cakupan | Satu bagian materi | Profil siswa menyeluruh |
| Label | Kurang..Baik Sekali | Perlu Penguatan..Sangat Baik |
| Untuk apa | Tindak lanjut belajar per bagian | Personalisasi rekomendasi |
| Ambang | ≥ 3 jawaban ter-tag | ≥ 15–20 sampel |

Keduanya **sengaja tidak selalu sama** untuk nilai di ambang — karena cakupan
berbeda. Perbedaan ini didokumentasikan dan dijaga pengujian.
Sumber: `docs/spesifikasi-kriteria-pemahaman-murid.md:7-12,172-179`.

---

## 4. ALUR FITUR REKOMENDASI

### 4.1 Daftar fitur

| # | Fitur | Input | Output | Dipakai di |
|---|-------|-------|--------|-----------|
| 1 | Rekomendasi **materi** | Fitur siswa + akses materi | Daftar materi + skor + alasan | dashboard siswa |
| 2 | Rekomendasi **bagian** | Penguasaan bagian + prasyarat + recency | `ranked` + `hints` | dashboard |
| 3 | **Langkah Berikutnya (NBA)** | penguasaan, progres baca, ketersediaan latihan/kuis | SATU aksi + alternatif | dashboard & halaman materi |
| 4 | **Sesi latihan adaptif** | soal APPROVED + riwayat | soal 60/30/10, jendela 10, rotasi | modal latihan |
| 5 | **Fokus miskonsepsi** | label miskonsepsi + jawaban terakhir | urutan soal diprioritaskan | sesi latihan |
| 6 | **Prasyarat antar-bagian** | teks konten (rujukan, kemiripan, posisi) | graph + status `prerequisite_met` | rekomendasi & peta guru |
| 7 | **Ranker LTR** | fitur pra-paparan | probabilitas penyelesaian | (belum dipakai, §5.3) |
| 8 | **Dashboard dampak** | event tayang/klik/selesai | CTR, funnel, practice lift | guru |

Sumber: `src/ml/recommendation.py`, `src/services/next_action_service.py`,
`src/services/student_practice_service.py`, `src/services/prerequisite_service.py`,
`src/ml/ranker.py`, `src/services/impact_analytics_service.py`.

### 4.2 Rekomendasi bagian — rumus skor

`recommendation.py:174-207`:
```
base  = mastery_gap * 0.60 + error_rate * 0.40
skor  = round( base * faktor_prasyarat * faktor_recency , 4 )

mastery_gap  = max(0, 1 - skor_penguasaan/100)      (0 bila belum ada skor)
error_rate   = salah / terjawab                      (dari jawaban nyata)
faktor_prasyarat = 0.5 bila prasyarat belum tuntas, selain itu 1.0
faktor_recency   = 0.80 bila baru dilatih (<20 jam),
                   1.05 bila sudah lama (>=7 hari), selain itu 1.0
```
- Bagian **READY** & skor < 90 → masuk daftar `ranked` (maks 4).
- Bagian belum READY → masuk `hints` (maks 2), tan **paksaan** (tanpa skor).
- Rekomendasi materi memakai bobot lain: `mastery_gap 0.35 + error 0.25 +
  belum_selesai 0.15 + relevansi topik 0.15 + kesesuaian tingkat 0.10`.

### 4.3 Langkah Berikutnya (Next Best Action)

Satu aksi dipilih, bobot dasar (bisa naik karena `need` & konteks)
(`next_action_service.py`, `ml_config.py:263-277`):

| Tipe aksi | Bobot | Kapan |
|---|---:|---|
| `practice_weak` | 1.00 | Bagian dikuasai lemah (<75) & ada soal latihan |
| `practice_after_read` | 0.90 | Sudah baca, belum pernah dilatih |
| `continue_reading` | 0.70 | Lanjut baca bagian / materi aktif |
| `take_quiz` | 0.55 | Kuis publik belum dikerjakan |
| `start_next_material` | 0.45 | Materi aktif selesai / belum mulai |
| `review_mastered` | 0.25 | Sudah tuntas tapi lama tak disentuh (≥14 hari) |
| `done` | 0.00 | Tidak ada aksi jujur (tidak memaksa) |

Setiap aksi membawa **CTA** konkret (`kind`: practice/read/quiz/material) supaya
siswa tahu harus klik apa.

### 4.4 Sesi latihan adaptif — jendela 10 + rotasi + fokus miskonsepsi

- Ukuran sesi **10 soal** (`SESSION_SIZE`, `ml_config.py:222-228`).
- Campuran tingkat **60% sesuai / 30% lebih mudah / 10% lebih sulit**
  (`SESSION_MIX_TARGET/BELOW/ABOVE`, `ml_config.py:217-220`) → mis. 6/3/1.
- **Rotasi**: soal yang belum pernah dijawab didahulukan, lalu yang paling lama
  tidak dijawab — supaya bank besar tetap terpakai lintas sesi.
  (`student_practice_service.py:548-563`)
- **Fokus miskonsepsi**: label miskonsepsi terlemah (salah > benar, min. 2 soal)
  diprioritaskan; label tidak pernah dikirim ke klien sebelum dijawab.
  (`:492-545`, `ml_config.py:254`)
- Keluar "tuntas" bila ≥ 3 soal & akurasi ≥ 75% (`ml_config.py:230-247`).

### 4.5 Prasyarat antar-bagian (advisory)

Graph prasyarat dibangun otomatis dari 3 bukti: **rujukan judul persis**
(confidence 0.9), **kemiripan isi** (TF-IDF), dan **urutan posisi** sebagai
cadangan (`prerequisite_service.py`). Sifatnya **advisory/tidak memblokir**:
hanya menurunkan prioritas (×0.5) bila prasyarat belum tuntas, tidak mengunci
akses (`recommendation.py:160-171`).

### 4.6 Dashboard dampak (untuk guru)

`impact_analytics_service.py:140-357`:
- **Funnel belajar**: `read_rate`, `practice_rate`, `quiz_rate`.
- **Rekomendasi**: `CTR = klik/tayang`, tindak lanjut setelah klik.
- **NBA**: `CTR` tayang→klik.
- **Practice lift**: `improve_rate`, akurasi percobaan pertama vs terakhir.
- **Per materi**: CTR per materi.
- Semua **observasional, bukan klaim kausal** (pengaman eksplisit di kode).

---

## 5. Titik jujur yang justru memperkuat presentasi

### 5.1 Tidak mengarang saat data kurang
Level materi & penguasaan bagian sama-sama mengembalikan `INSUFFICIENT_DATA`
dengan alasan, bukan angka karangan.

### 5.2 Dua lane tidak dicampur
Pengukuran (`mode='diagnostic'`, non-adaptif) terpisah dari remediasi (latihan
adaptif). Ini mencegah "materi tampak sulit" akibat alat ukurnya sendiri.

### 5.3 Ranker ML dibuat, diuji, **tetapi tidak dipakai** karena tidak menang
`ranker.py` melatih Learning-to-Rank dan mengevaluasinya lintas-siswa (5-fold,
NDCG@5). Hasil demo: ROC-AUC ≈ **0.92**, tetapi **NDCG@5 ≈ 0.43** —
**tidak lebih baik** dari acak (≈0.44) maupun baseline popularitas (≈0.43),
sehingga gate rilis **tertutup** dan rekomendasi tetap memakai aturan rule-based
yang transparan. (Angka dari `docs/laporan-demo-rekomendasi-virus.md:137-144`;
konstanta gate `ml_config.py:367-372`.)

> Poin ini kuat untuk dosen: sistem **tidak** memakai ML hanya agar terlihat
> canggih. Jika tidak terbukti lebih baik, ML tidak dirilis.

### 5.4 Anti-kebocoran label (label leakage)
Decision Tree tidak diberi fitur yang membentuk labelnya sendiri, sehingga
akurasi yang dilaporkan tidak "menipu" (`decision_tree.py:1-53`;
`ml_config.py:47-53`).

---

## 6. Alur end-to-end (satu tarikan napas)

```
GURU  ──menyiapkan──►  soal latihan (practice) + soal diagnostik (diagnostic)
                              │
SISWA ──membaca materi──►  tombol Asesmen Diagnostik  ──►  bagian digerbang
                              │                             (wajib sebelum lanjut)
                              ▼
                        jawaban mode='diagnostic'
                              │
              ┌───────────────┴────────────────┐
              ▼                                 ▼
      LEVEL MATERI (guru)              PENGUASAAN PER BAGIAN (siswa & guru)
      mudah/sedang/sulit               Kurang/Cukup/Baik/Baik Sekali
      (butuh ≥3 soal & ≥20 siswa)      (butuh ≥3 jawaban)
                              │                                 │
                              └───────────────┬─────────────────┘
                                              ▼
                                    PROFIL ML (DT + KMeans)
                                              │
                                              ▼
                            ┌─────────── FITUR REKOMENDASI ───────────┐
                            │ rekomendasi materi & bagian • NBA •      │
                            │ sesi latihan adaptif • fokus miskonsepsi │
                            │ • prasyarat (advisory) • dashboard dampak│
                            └──────────────────────────────────────────┘
                                              │
                                              ▼
                                    SISWA belajar lagi (loop)
```

---

## 7. Bukti / pengujian

Skrip uji otomatis (dijalankan berurutan pada DB nyata, membuat & menghapus
fixture-nya sendiri):

| Uji | Cakupan | Hasil terakhir |
|---|---|---|
| `test_material_level_diagnostic.py` | level materi & diagnostik | 77/77 |
| `test_practice_drafts.py` | latihan per bagian + draf guru | 83/83 |
| `test_ml_difficulty.py` | kesulitan soal otomatis | 67/67 |
| `test_section_recommendations.py` | rekomendasi bagian | 63/63 |
| `test_question_difficulty.py` | tingkat soal (p-value, LOO) | 59/59 |
| `test_section_mastery.py` | penguasaan per bagian + grid | 50/50 |
| `test_section_tagging.py` | penandaan bagian | 24/24 |
| `test_student_practice.py` | latihan siswa + sesi + gerbang | 103/103 |

Semua **0 gagal**.

---

## 8. Batasan jujur (siap ditanya dosen)

1. **Ranker LTR belum dirilis** (belum menang atas baseline) — rekomendasi
   masih rule-based & transparan.
2. **Dashboard dampak observasional**, bukan kausal (tidak ada kelompok kontrol).
3. **Gerbang asesmen diagnostik di sisi UI**; belum ada penegakan server-side.
   Buka-tembus lewat URL langsung (`?section=`) belum ditutup.
   (`docs/spesifikasi-level-materi-diagnostik.md:378-386`)
4. Di Materi 107 baru **sebagian** bagian punya soal diagnostik (bagian 48 & 50);
   bagian lain belum bisa digerbang sebelum ditambahi soal.
5. **Catatan teknis:** sumber "latihan" pada penguasaan bagian membaca seluruh
   baris `practice_answers` (`mode=None`), sehingga jawaban diagnostik ikut
   terhitung di sumber latihan. Level materi sendiri tetap memakai penanda
   `mode='diagnostic'` yang terpisah. (`student_practice_service.py:201-257`,
   `learning_analytics_service.py:417-433`.)

---

## 9. Referensi file kunci

| Topik | File |
|---|---|
| Spesifikasi level materi | `docs/spesifikasi-level-materi-diagnostik.md` |
| Spesifikasi pemahaman murid | `docs/spesifikasi-kriteria-pemahaman-murid.md` |
| Desain rekomendasi adaptif | `e-bio-x-backend/docs/DESIGN_REKOMENDASI_ADAPTIF.md` |
| Fitur bagian & mastery | `e-bio-x-backend/docs/FEATURE_BAGIAN_MASTERY.md` |
| Perhitungan level materi | `e-bio-x-backend/src/services/question_difficulty_service.py` |
| Perhitungan penguasaan | `e-bio-x-backend/src/services/learning_analytics_service.py` |
| Rekomendasi materi/bagian | `e-bio-x-backend/src/ml/recommendation.py` |
| NBA | `e-bio-x-backend/src/services/next_action_service.py` |
| Sesi latihan adaptif | `e-bio-x-backend/src/services/student_practice_service.py` |
| Ranker LTR | `e-bio-x-backend/src/ml/ranker.py`, `recommendation_evaluation.py` |
| Dashboard dampak | `e-bio-x-backend/src/services/impact_analytics_service.py` |
| Ambang & konstanta | `e-bio-x-backend/src/ml/ml_config.py` |
| UI guru (level materi) | `e-bio-x-frontend/app/pages/teacher/materials/analytics/[id].vue` |
| UI guru (dampak) | `e-bio-x-frontend/app/pages/teacher/analytics/impact.vue` |
| UI siswa (dashboard) | `e-bio-x-frontend/app/pages/student/dashboard.vue` |
| UI siswa (materi + gerbang) | `e-bio-x-frontend/app/pages/student/materials/[id].vue` |
