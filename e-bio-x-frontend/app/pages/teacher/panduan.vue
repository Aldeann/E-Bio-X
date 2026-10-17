<template>
  <div>
    <PageHeader
      title="Panduan Penggunaan"
      subtitle="Langkah singkat memakai setiap fitur guru di E-Bio X, dari masuk hingga keluar."
    >
      <span
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/40 text-green-700 dark:text-green-300 text-xs sm:text-sm font-medium">
        <Icon name="material-symbols:badge" class="w-4 h-4" /> Peran: Guru
      </span>
    </PageHeader>

    <!-- Kata pengantar -->
    <div
      class="rounded-xl border border-green-200 dark:border-green-800 bg-green-50/70 dark:bg-green-950/20 p-4 sm:p-5 mb-6">
      <p class="text-sm sm:text-base text-gray-700 dark:text-gray-200 leading-relaxed">
        Panduan ini menjelaskan semua menu pada sidebar guru beserta cara memakainya.
        Alurnya: <b>Masuk</b> → <b>Dasbor</b> → <b>Analitik</b> → <b>ML Insights</b> →
        <b>Materi</b> → <b>Kuis</b> → <b>Bank Soal</b> → <b>Latihan per Bagian</b> →
        <b>Forum</b> → <b>Pembahasan AI</b> → <b>Akun</b>. Klik gambar untuk memperbesar.
      </p>
    </div>

    <!-- Daftar isi -->
    <nav class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 mb-8">
      <h2 class="font-semibold mb-3 text-gray-800 dark:text-gray-100">Daftar Isi</h2>
      <ul class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1.5">
        <li v-for="(s, i) in sections" :key="s.id">
          <a :href="'#' + s.id"
            class="flex items-center gap-2 text-sm text-green-700 dark:text-green-400 hover:underline">
            <span
              class="inline-flex w-5 h-5 shrink-0 items-center justify-center rounded bg-green-100 dark:bg-green-900/50 text-[11px] font-bold text-green-700 dark:text-green-300">
              {{ i + 1 }}
            </span>
            {{ s.title }}
          </a>
        </li>
      </ul>
    </nav>

    <!-- Bagian -->
    <section v-for="(s, i) in sections" :id="s.id" :key="s.id" class="mb-10 scroll-mt-20">
      <div class="flex items-center gap-2.5 mb-2">
        <span
          class="inline-flex w-8 h-8 shrink-0 items-center justify-center rounded-lg bg-green-600 text-white text-sm font-bold">
          {{ i + 1 }}
        </span>
        <Icon :name="s.icon" class="w-6 h-6 text-green-600 dark:text-green-400 shrink-0" />
        <h2 class="text-lg sm:text-xl font-semibold text-gray-800 dark:text-gray-100">{{ s.title }}</h2>
      </div>

      <p class="text-sm text-gray-600 dark:text-gray-300 mb-3 leading-relaxed" v-html="s.desc"></p>

      <ol class="list-decimal list-outside ml-5 space-y-1.5 text-sm text-gray-700 dark:text-gray-200 leading-relaxed">
        <li v-for="(step, j) in s.steps" :key="j" v-html="step"></li>
      </ol>

      <p v-if="s.note"
        class="mt-3 flex items-start gap-2 text-xs sm:text-sm rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 p-2.5">
        <Icon name="material-symbols:info-outline" class="w-4 h-4 mt-0.5 shrink-0" />
        <span v-html="s.note"></span>
      </p>

      <figure v-if="s.image" class="mt-4">
        <a :href="s.image" target="_blank" rel="noopener" :title="'Perbesar: ' + s.title">
          <img :src="s.image" :alt="'Tangkapan layar: ' + s.title" loading="lazy"
            class="w-full h-64 sm:h-80 object-cover object-top rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition"
            @error="onImgError" />
        </a>
        <figcaption class="mt-1.5 text-[11px] text-gray-400 text-center">
          Gambar {{ i + 1 }} — {{ s.title }} · klik untuk memperbesar
        </figcaption>
      </figure>
    </section>

    <p class="text-center text-xs text-gray-400 pt-4 border-t border-gray-100 dark:border-gray-800">
      E-Bio X · Panduan Penggunaan Guru · v1.0
    </p>
  </div>
</template>

<script setup>
// Konten panduan disimpan sebagai data agar mudah diperbarui.
const sections = [
  {
    id: "masuk",
    title: "Masuk ke Aplikasi (Login)",
    icon: "material-symbols:login",
    desc: "Semua pengguna masuk melalui halaman <b>Login</b>. Gunakan akun guru yang diberikan oleh admin/sekolah.",
    steps: [
      "Buka alamat aplikasi E-Bio X. Halaman <b>Login</b> akan muncul otomatis.",
      "Isi kolom <b>Email</b> dan <b>Password</b> akun guru Anda.",
      "Klik ikon mata di kolom password bila ingin menampilkan/menyembunyikan password.",
      "Klik tombol <b>Login</b>. Jika berhasil, Anda diarahkan ke halaman <b>Dasbor Guru</b>.",
    ],
    note: "Tersedia juga tombol masuk dengan akun Google (opsional). Jika lupa password, hubungi admin sekolah untuk direset.",
    image: "/panduan/01-login.png",
  },
  {
    id: "dasbor",
    title: "Dasbor Guru",
    icon: "material-symbols:dashboard",
    desc: "Halaman utama setelah login. Menampilkan sapaan dan daftar kelas yang Anda ampu.",
    steps: [
      "Lihat daftar <b>Kelas Saya</b> — tiap kartu menampilkan nama kelas, jumlah siswa, dan kode kelas.",
      "Klik <b>+ Buat Kelas Baru</b>, isi nama kelas, lalu klik <b>Buat</b>.",
      "Bagikan <b>kode kelas</b> ke siswa (klik ikon salin) agar mereka dapat bergabung.",
      "Klik <b>Kelola</b> untuk membuka detail kelas, atau ikon tempat sampah untuk menghapus kelas.",
    ],
    image: "/panduan/02-dasbor.png",
  },
  {
    id: "analitik",
    title: "Analitik Pembelajaran",
    icon: "material-symbols:monitoring",
    desc: "Pantau progres siswa, penguasaan materi, kinerja kuis, dan topik.",
    steps: [
      "Atur filter: <b>Kelas</b>, <b>Fase</b>, <b>Topik</b>, <b>Materi</b>, cari siswa, rentang tanggal, status belajar, dan status penguasaan.",
      "Klik <b>Terapkan</b> untuk memuat data (klik <b>Reset</b> untuk mengembalikan filter).",
      "Baca kartu ringkasan dan grafik <b>Distribusi Penguasaan</b> serta <b>Distribusi Status Belajar</b>.",
      "Telaah <b>Analitik per Topik</b> dan <b>Kinerja per Tingkat Kesulitan</b>.",
      "Gunakan tabel siswa & peta penguasaan untuk menemukan siswa yang perlu pendampingan.",
    ],
    image: "/panduan/03-analitik.png",
  },
  {
    id: "ml-insights",
    title: "ML Insights (Machine Learning)",
    icon: "material-symbols:psychology",
    desc: "Analisis penguasaan, profil belajar, dan rekomendasi berbasis data.",
    steps: [
      "Buka menu <b>ML Insights</b>.",
      "Klik <b>Latih / Retrain Model</b> untuk memperbarui model dari data terbaru.",
      "Perhatikan pesan hasil training: status <b>Decision Tree</b> dan <b>K-Means</b> beserta metriknya.",
      "Cek keterangan <b>cakupan model</b> (per kelas atau gabungan) sebelum menafsirkan hasil.",
      "Gunakan bagian penguasaan, profil belajar, dan rekomendasi untuk merancang tindak lanjut.",
    ],
    note: "Model akan menolak dilatih bila data siswa belum cukup (status <b>INSUFFICIENT_DATA</b>), bukan karena kesalahan sistem.",
    image: "/panduan/04-ml-insights.png",
  },
  {
    id: "materi",
    title: "Materi Pembelajaran",
    icon: "material-symbols:menu-book",
    desc: "Kelola materi interaktif untuk siswa.",
    steps: [
      "Klik <b>Buat Materi</b>, lalu isi judul, mata pelajaran, fase, kelas, dan topik.",
      "Gunakan <b>Filter kelas</b> untuk menyaring daftar materi.",
      "Klik judul atau tombol <b>Edit</b> untuk membuka <b>Penyusun Materi</b> dan mengatur bagian, konten, gambar, serta tujuan pembelajaran.",
      "Lengkapi kartu <b>pengantar</b>, <b>petunjuk belajar</b>, dan <b>kebutuhan belajar</b> pada materi agar siswa tahu cara memakainya.",
      "Manfaatkan tombol <b>Preview</b> (tampilan siswa), <b>Analitik</b> (progres), <b>Publish/Unpublish</b>, dan <b>Hapus</b>.",
    ],
    image: "/panduan/05-materi.png",
  },
  {
    id: "kuis",
    title: "Kuis",
    icon: "material-symbols:quiz",
    desc: "Buat, publikasikan, dan pantau kuis interaktif materi.",
    steps: [
      "Klik <b>Buat Kuis</b> (siapkan soalnya lebih dulu di <b>Bank Soal</b> bila perlu).",
      "Isi judul, deskripsi, materi terkait, durasi, dan nilai kelulusan (KKM), lalu tambahkan soal.",
      "Pada daftar kuis, lihat status (Draft/Published), jumlah soal, poin, durasi, dan statistik Peserta/Percobaan/Rata-rata.",
      "Klik <b>Kelola</b> untuk mengatur & mempublikasikan kuis, <b>Analitik</b> untuk hasil per soal, atau ikon sampah untuk menghapus.",
    ],
    image: "/panduan/06-kuis.png",
  },
  {
    id: "bank-soal",
    title: "Bank Soal",
    icon: "material-symbols:database",
    desc: "Kumpulan soal yang dapat dipakai ulang di kuis mana pun.",
    steps: [
      "Klik <b>Tambah Soal</b> untuk menulis soal baru (pilihan ganda / benar-salah), lengkap dengan tingkat kesulitan dan jenisnya.",
      "Gunakan filter: pencarian, tipe, kesulitan, status, dan jenis (Latihan adaptif / Diagnostik).",
      "Atur <b>soal per slide</b> dan pindah halaman dengan tombol panah kiri/kanan.",
      "Pada tiap soal tersedia aksi <b>Edit</b>, <b>Hapus</b>, dan <b>Generate Pembahasan AI</b>.",
    ],
    image: "/panduan/07-bank-soal.png",
  },
  {
    id: "latihan",
    title: "Latihan per Bagian",
    icon: "material-symbols:fitness_center",
    desc: "Soal latihan untuk setiap bagian materi.",
    steps: [
      "Buka tab <b>Bagian</b> untuk melihat tiap materi & bagian beserta jumlah soal disetujui, diagnostik, menunggu review, dan ditolak.",
      "Klik <b>Minta AI membuat draf</b> pada bagian yang ingin dibuatkan soal (bila AI aktif).",
      "Buka tab <b>Review</b> untuk memeriksa draf soal yang dihasilkan AI.",
      "Klik <b>Setujui</b> agar draf dapat dipakai siswa, atau <b>Tolak</b> bila tidak sesuai.",
      "Pastikan setiap materi memiliki minimal <b>3 soal diagnostik</b> agar tingkat materi dapat diukur.",
    ],
    image: "/panduan/08-latihan.png",
  },
  {
    id: "forum",
    title: "Forum Diskusi",
    icon: "mdi:forum-outline",
    desc: "Wadah diskusi antara siswa dan guru.",
    steps: [
      "Klik <b>Forum Baru</b> untuk membuat topik diskusi (tipe: Diskusi, Presentasi, Tanya Jawab, atau Studi Kasus).",
      "Cari/ filter forum berdasarkan tipe dan urutan; centang <b>Hanya forum saya</b> bila perlu.",
      "Klik salah satu kartu forum untuk membuka dan membalas diskusi.",
      "Gunakan tombol <b>Moderasi</b> untuk meninjau konten dan <b>Analitik</b> untuk statistik forum.",
      "Gunakan ikon tempat sampah pada kartu untuk menghapus forum.",
    ],
    image: "/panduan/09-forum.png",
  },
  {
    id: "pembahasan-ai",
    title: "Pembahasan AI",
    icon: "material-symbols:lightbulb",
    desc: "Kelola pembahasan kuis. Siswa hanya dapat melihat pembahasan yang berstatus disetujui.",
    steps: [
      "Masukkan <b>ID Soal</b> pada kolom di kanan atas, lalu klik <b>Generate</b> untuk membuat pembahasan otomatis.",
      "Saring daftar berdasarkan <b>status</b> dan kata kunci, lalu klik <b>Terapkan</b>.",
      "Lihat ringkasan: Total, Disetujui, Menunggu, dan Gagal.",
      "Klik <b>Lihat</b> untuk membaca, <b>Setujui</b> bila sudah sesuai, atau <b>Tolak</b> bila perlu diperbaiki.",
    ],
    image: "/panduan/10-pembahasan-ai.png",
  },
  {
    id: "akun",
    title: "Akun & Keluar",
    icon: "mdi:cog",
    desc: "Atur profil dan keluar dari aplikasi.",
    steps: [
      "Buka menu <b>Akun</b> pada sidebar.",
      "Klik ikon pensil untuk mengubah <b>nama</b> Anda.",
      "Klik tombol <b>ubah password</b> untuk mengganti password.",
      "Untuk keluar, klik <b>Logout</b> di sidebar lalu konfirmasi. Tema terang/gelap dapat diubah lewat tombol <b>Ganti tema</b>.",
    ],
    image: "/panduan/11-akun.png",
  },
];

const onImgError = (e) => {
  const fig = e?.target?.closest("figure");
  if (fig) fig.style.display = "none";
};

definePageMeta({
  layout: "teacher",
  middleware: "auth",
  role: "teacher",
});
</script>
