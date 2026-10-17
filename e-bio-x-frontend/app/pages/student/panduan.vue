<template>
  <div>
    <div class="mb-5">
      <div class="flex flex-wrap items-center gap-2.5">
        <h1 class="text-2xl font-bold text-green-700 dark:text-green-400">Panduan Penggunaan</h1>
        <span
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/40 text-green-700 dark:text-green-300 text-xs sm:text-sm font-medium">
          <Icon name="material-symbols:school" class="w-4 h-4" /> Peran: Siswa
        </span>
      </div>
      <p class="text-sm text-gray-500 mt-1">
        Langkah singkat memakai setiap fitur siswa di E-Bio X, dari masuk hingga keluar.
      </p>
    </div>

    <!-- Kata pengantar -->
    <div
      class="rounded-xl border border-green-200 dark:border-green-800 bg-green-50/70 dark:bg-green-950/20 p-4 sm:p-5 mb-6">
      <p class="text-sm sm:text-base text-gray-700 dark:text-gray-200 leading-relaxed">
        Panduan ini menjelaskan semua menu pada navigasi siswa beserta cara memakainya.
        Alurnya: <b>Masuk</b> → <b>Kelas Saya</b> → <b>Dashboard</b> → <b>Materi</b> →
        <b>Belajar Materi</b> → <b>Latihan Adaptif</b> → <b>Asesmen Diagnostik</b> →
        <b>Kuis</b> → <b>Riwayat Belajar</b> → <b>Forum</b> → <b>Akun</b>. Klik gambar untuk memperbesar.
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
      E-Bio X · Panduan Penggunaan Siswa · v1.0
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
    desc: "Semua pengguna masuk melalui halaman <b>Login</b>. Gunakan akun siswa yang diberikan oleh guru/sekolah.",
    steps: [
      "Buka alamat aplikasi E-Bio X. Halaman <b>Login</b> akan muncul otomatis.",
      "Isi kolom <b>Email</b> dan <b>Password</b> akun siswa Anda.",
      "Klik ikon mata di kolom password bila ingin menampilkan/menyembunyikan password.",
      "Klik tombol <b>Login</b>. Jika berhasil, Anda diarahkan ke halaman <b>Kelas Saya</b>.",
    ],
    note: "Tersedia juga tombol masuk dengan akun Google (opsional). Jika lupa password, hubungi guru atau admin sekolah untuk direset.",
    image: "/panduan-siswa/01-login.png",
  },
  {
    id: "kelas",
    title: "Kelas Saya & Gabung Kelas",
    icon: "material-symbols:groups",
    desc: "Halaman pertama setelah masuk. Di sini Anda bergabung ke kelas dan melihat kelas yang sudah diikuti.",
    steps: [
      "Pada bagian <b>Gabung Kelas</b>, masukkan <b>kode kelas</b> yang dibagikan gurumu, lalu klik <b>Gabung</b>.",
      "Pada bagian <b>Kelasku</b>, tiap kartu menampilkan nama kelas dan nama guru pengampu.",
      "Klik <b>Masuk Kelas</b> untuk membuka isi kelas.",
      "Klik ikon keluar (tanda kotak-panah) di pojok kartu bila ingin keluar dari kelas.",
    ],
    note: "Belum punya kode kelas? Minta kode kepada gurumu. Bila belum terdaftar di kelas mana pun, daftar materi & kuis bisa jadi kosong.",
    image: "/panduan-siswa/02-kelas.png",
  },
  {
    id: "ruang-kelas",
    title: "Masuk Kelas (Ruang Kelas)",
    icon: "material-symbols:meeting-room",
    desc: "Isi sebuah kelas, dipecah menjadi beberapa tab: Materi, Siswa, Kuis, dan Forum.",
    steps: [
      "Klik tab <b>Materi</b> untuk melihat bahan ajar kelas.",
      "Klik tab <b>Siswa</b> untuk melihat teman sekelas.",
      "Klik tab <b>Kuis</b> untuk melihat kuis kelas.",
      "Klik tab <b>Forum</b> untuk berdiskusi dengan kelas.",
    ],
    image: "/panduan-siswa/03-ruang-kelas.png",
  },
  {
    id: "dasbor",
    title: "Dashboard Belajar",
    icon: "material-symbols:dashboard",
    desc: "Ringkasan belajar: arahan berikutnya, rekomendasi, dan progres.",
    steps: [
      "Baca kotak <b>Langkah Berikutnya</b> — satu arahan utama yang bisa langsung diklik.",
      "Lihat <b>kartu ringkasan</b> (jumlah materi, kuis, dan capaian belajarmu).",
      "Telaah <b>Rekomendasi Belajar Anda</b>: label penguasaan, faktor utama, dan alasan tiap saran.",
      "Pada <b>Bagian yang Perlu Diperkuat</b>, klik <b>Latihan adaptif</b> untuk langsung berlatih atau <b>Buka materi</b>.",
      "Lanjutkan lewat <b>Lanjutkan Belajar</b> dan pantau <b>Progres Materi</b> (tombol <b>Buka</b>/<b>Ulangi</b>).",
    ],
    note: "Rekomendasi dihitung dari jawabanmu sendiri (kuis, soal interaktif, dan latihan). Bila datanya belum cukup, skor sengaja tidak ditampilkan.",
    image: "/panduan-siswa/04-dasbor.png",
  },
  {
    id: "materi",
    title: "Materi Pembelajaran",
    icon: "material-symbols:menu-book",
    desc: "Telusuri semua materi yang dipublikasikan gurumu.",
    steps: [
      "Buka menu <b>Materi</b> pada navigasi.",
      "Gunakan kolom <b>pencarian</b> untuk mencari judul, topik, atau mata pelajaran.",
      "Saring dengan filter <b>Kelas</b>, <b>Fase</b>, <b>Kesulitan</b>, dan <b>Status</b>, lalu atur urutan.",
      "Klik kartu materi untuk mulai belajar (atau <b>Reset</b> untuk menghapus filter).",
    ],
    image: "/panduan-siswa/05-materi.png",
  },
  {
    id: "belajar",
    title: "Belajar Materi (Bagian & Konten)",
    icon: "material-symbols:auto-stories",
    desc: "Halaman isi materi: pengantar, tujuan, konten tiap bagian, dan soal interaktif.",
    steps: [
      "Baca kartu pembuka: <b>Kata Pengantar</b>, <b>Pengantar</b>, <b>Tujuan Pembelajaran</b>, <b>Petunjuk Pembelajaran</b>, dan <b>Kebutuhan Belajar</b> (klik untuk membuka/menutup).",
      "Lihat <b>Kuis Terkait</b> bila materi ini punya kuis.",
      "Pilih bagian lewat <b>Daftar Bagian</b>, lalu baca konten dan kerjakan <b>soal interaktif</b> di dalamnya.",
      "Gunakan tombol <b>Diskusi di Forum</b> bila ada yang ingin ditanyakan.",
    ],
    note: "Progres tiap bagian tersimpan otomatis, jadi kamu bisa berhenti dan melanjutkan kapan saja.",
    image: "/panduan-siswa/06-belajar.png",
  },
  {
    id: "latihan",
    title: "Latihan Adaptif per Bagian",
    icon: "material-symbols:fitness-center",
    desc: "Latihan yang menyesuaikan tingkat kesulitan dengan jawabanmu.",
    steps: [
      "Dari halaman materi atau dashboard, klik tombol <b>Latihan adaptif</b> (menampilkan jumlah soal).",
      "Kerjakan satu soal per layar; tingkat soal mengikuti jawabanmu.",
      "Pilih satu opsi, lalu klik <b>Periksa Jawaban</b>.",
      "Perhatikan ikon <b>centang</b> (benar) / <b>silang</b> (salah) beserta pembahasan tiap opsi.",
      "Klik <b>Soal Berikutnya</b> hingga selesai, lalu lihat ringkasan sesi.",
    ],
    note: "Jawaban latihan ikut dihitung pada peta pemahaman bagian ini, jadi kerjakan dengan sungguh-sungguh.",
    image: "/panduan-siswa/07-latihan.png",
  },
  {
    id: "asesmen",
    title: "Asesmen Diagnostik",
    icon: "material-symbols:fact-check",
    desc: "Asesmen awal untuk mengukur tingkat pemahamanmu pada suatu bagian.",
    steps: [
      "Pada halaman materi (atau dashboard), klik tombol <b>Asesmen Diagnostik</b>.",
      "Kerjakan semua soal asesmen yang muncul.",
      "Setelah selesai, lihat ringkasan: berapa soal dijawab dan berapa yang benar.",
    ],
    note: "Asesmen diagnostik dipakai untuk menyesuaikan materi & latihan berikutnya, bukan untuk nilai.",
    image: "/panduan-siswa/08-asesmen.png",
  },
  {
    id: "kuis",
    title: "Kuis",
    icon: "material-symbols:quiz",
    desc: "Kerjakan kuis dari gurumu dan ukur pemahamanmu.",
    steps: [
      "Buka menu <b>Kuis</b>.",
      "Saring daftar dengan tombol <b>Semua</b>, <b>Belum</b>, <b>Berjalan</b>, atau <b>Selesai</b>.",
      "Klik kartu kuis untuk mengerjakan; perhatikan jumlah soal, poin, dan durasinya.",
      "Setelah selesai, lihat hasil (skor/kelulusan) dan pembahasan bila gurumu sudah menyetujuinya.",
    ],
    note: "Kuis yang punya batas waktu akan otomatis dikumpulkan saat waktu habis — perhatikan sisa waktu.",
    image: "/panduan-siswa/09-kuis.png",
  },
  {
    id: "riwayat",
    title: "Riwayat Belajar & Progres",
    icon: "material-symbols:history",
    desc: "Rekap semua materi yang kamu ikuti beserta progres dan penguasaannya.",
    steps: [
      "Buka dari dashboard: <b>Progres Materi</b> → <b>Lihat riwayat</b> (atau menu <b>Riwayat</b>).",
      "Lihat kartu ringkasan: <b>Total Materi</b>, <b>Selesai</b>, <b>Sedang Berjalan</b>, <b>Progres Rata-rata</b>, dan <b>Total Waktu Belajar</b>.",
      "Telaah tabel materi: progres, status, dan label penguasaan.",
      "Klik judul materi untuk membuka detail progres per bagian.",
    ],
    image: "/panduan-siswa/10-riwayat.png",
  },
  {
    id: "forum",
    title: "Forum Diskusi",
    icon: "mdi:forum-outline",
    desc: "Wadah diskusi antara siswa dan guru.",
    steps: [
      "Buka menu <b>Forum</b>.",
      "Klik <b>Forum Baru</b> untuk membuat topik diskusi baru.",
      "Cari/ filter forum, lalu klik salah satu kartu untuk membukanya.",
      "Tulis balasan pada kolom diskusi dan kirim.",
    ],
    note: "Jaga kesopanan saat berdiskusi. Hindari membagikan data pribadi.",
    image: "/panduan-siswa/11-forum.png",
  },
  {
    id: "akun",
    title: "Akun & Keluar",
    icon: "mdi:cog",
    desc: "Atur profil dan keluar dari aplikasi.",
    steps: [
      "Klik <b>nama/avatar</b> di kanan atas, lalu pilih <b>Akun</b> (di ponsel: buka menu ☰ → <b>Akun</b>).",
      "Klik ikon pensil untuk mengubah <b>nama</b> Anda.",
      "Klik tombol <b>ubah password</b> untuk mengganti password.",
      "Ubah tema terang/gelap lewat tombol <b>Ganti tema</b>. Untuk keluar, pilih <b>Logout</b> lalu konfirmasi.",
    ],
    image: "/panduan-siswa/12-akun.png",
  },
];

const onImgError = (e) => {
  const fig = e?.target?.closest("figure");
  if (fig) fig.style.display = "none";
};

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>
