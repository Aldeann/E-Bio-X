<template>
  <div class="space-y-6">
    <!-- Identitas pengembang -->
    <section class="rounded-2xl border border-line bg-surface p-6 shadow-sm sm:p-8">
      <div class="flex flex-col gap-6 sm:flex-row sm:items-center">
        <!-- Ganti blok inisial ini dengan <img> foto profesional saat tersedia. -->
        <div
          class="flex h-24 w-24 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-700 to-brand-900 text-3xl font-bold text-white ring-4 ring-brand-100 dark:ring-brand-900/50"
          aria-hidden="true">
          {{ developer.initials }}
        </div>

        <div class="min-w-0">
          <p class="text-xs font-semibold uppercase tracking-wider text-brand-700 dark:text-brand-300">
            Tentang Pengembang
          </p>
          <h1 class="mt-1 text-2xl font-bold text-strong sm:text-3xl">{{ developer.name }}</h1>
          <p class="mt-1 text-sm font-medium text-body">{{ developer.role }}</p>
          <p class="mt-3 text-sm leading-relaxed text-muted">
            Mahasiswa {{ institution.program }}<br />
            {{ institution.faculty }}<br />
            {{ institution.university }}
          </p>

          <div class="mt-4 flex flex-wrap gap-2">
            <a
              :href="`mailto:${developer.email}`"
              class="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-medium text-body transition hover:border-brand-300 hover:text-brand-700 dark:hover:border-brand-700 dark:hover:text-brand-300">
              <Icon name="material-symbols:mail" class="h-4 w-4" aria-hidden="true" />
              Email
            </a>
            <!-- Tambahkan tautan GitHub / LinkedIn di sini saat sudah tersedia. -->
          </div>
        </div>
      </div>
    </section>

    <!-- Tentang pengembangan -->
    <section class="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-strong">
        <Icon name="material-symbols:science" class="h-5 w-5 text-brand-700 dark:text-brand-400" aria-hidden="true" />
        Tentang Pengembangan
      </h2>

      <div class="mt-3 space-y-3 text-sm leading-relaxed text-body">
        <p>
          E-Bio X adalah website pembelajaran biologi terintegrasi <em>machine learning</em>
          yang dikembangkan sebagai bagian dari <strong>skripsi</strong> di Program Studi
          Pendidikan Biologi, Fakultas Matematika dan Ilmu Pengetahuan Alam,
          Universitas Negeri Padang.
        </p>
        <p>
          Pengembangan berangkat dari kebutuhan akan suplemen belajar digital yang tidak
          hanya menyajikan materi, tetapi juga memberikan umpan balik yang dipersonalisasi.
          E-Bio X menghadirkan materi interaktif, kuis, serta analisis berbasis
          <em>machine learning</em> untuk membantu peserta didik memahami materi dan
          membantu guru memantau proses belajar.
        </p>
        <p>
          Penelitian ini menggunakan metode penelitian dan pengembangan dengan validasi
          ahli serta uji coba pada peserta didik <strong>Fase E SMA (kelas X)</strong>.
        </p>
      </div>

      <h3 class="mt-6 text-sm font-semibold text-strong">Fitur Utama</h3>
      <ul class="mt-2 grid gap-2 sm:grid-cols-2">
        <li v-for="feature in features" :key="feature" class="flex items-start gap-2 text-sm text-body">
          <Icon
            name="material-symbols:check-circle"
            class="mt-0.5 h-4 w-4 shrink-0 text-brand-700 dark:text-brand-400"
            aria-hidden="true" />
          <span>{{ feature }}</span>
        </li>
      </ul>
    </section>

    <!-- Institusi & penelitian -->
    <div class="grid gap-6 lg:grid-cols-2">
      <section class="rounded-2xl border border-line bg-surface p-6 sm:p-8">
        <h2 class="flex items-center gap-2 text-lg font-semibold text-strong">
          <Icon name="material-symbols:account-balance" class="h-5 w-5 text-brand-700 dark:text-brand-400" aria-hidden="true" />
          Institusi
        </h2>
        <div class="mt-3 space-y-1 text-sm leading-relaxed text-body">
          <p class="text-base font-semibold text-strong">{{ institution.university }}</p>
          <p>{{ institution.faculty }}</p>
          <p>{{ institution.program }}</p>
          <p class="text-muted">{{ institution.location }}</p>
        </div>
        <!-- Tambahkan logo institusi di sini setelah memperoleh izin. -->
      </section>

      <section class="rounded-2xl border border-line bg-surface p-6 sm:p-8">
        <h2 class="flex items-center gap-2 text-lg font-semibold text-strong">
          <Icon name="material-symbols:menu-book" class="h-5 w-5 text-brand-700 dark:text-brand-400" aria-hidden="true" />
          Penelitian
        </h2>
        <dl class="mt-3 divide-y divide-line text-sm">
          <div class="py-2.5">
            <dt class="text-muted">Judul</dt>
            <dd class="mt-0.5 font-medium leading-snug text-body">{{ research.title }}</dd>
          </div>
          <div class="flex items-center justify-between gap-3 py-2.5">
            <dt class="text-muted">Jenis</dt>
            <dd class="text-body">{{ research.type }}</dd>
          </div>
          <div class="flex items-center justify-between gap-3 py-2.5">
            <dt class="text-muted">Tahun pengembangan</dt>
            <dd class="text-body">{{ research.year }}</dd>
          </div>
          <div class="flex items-center justify-between gap-3 py-2.5">
            <dt class="text-muted">Ruang lingkup</dt>
            <dd class="text-right text-body">{{ research.scope }}</dd>
          </div>
        </dl>
      </section>
    </div>

    <!-- Tim pembimbing -->
    <section class="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-strong">
        <Icon name="material-symbols:groups" class="h-5 w-5 text-guru-700 dark:text-guru-300" aria-hidden="true" />
        Tim Pembimbing
      </h2>

      <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <article
          v-for="person in supervisors"
          :key="person.name"
          class="flex items-center gap-3 rounded-xl border border-line bg-surface-muted p-4">
          <!-- Ganti blok inisial ini dengan <img> foto dosen setelah memperoleh izin. -->
          <div
            class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-guru-50 text-sm font-bold text-guru-700 ring-1 ring-guru-200 dark:bg-guru-900/40 dark:text-guru-200 dark:ring-guru-800"
            aria-hidden="true">
            {{ person.initials }}
          </div>
          <div class="min-w-0">
            <h3 class="text-sm font-semibold leading-snug text-strong">{{ person.name }}</h3>
            <p class="mt-0.5 text-xs text-muted">{{ person.role }}</p>
          </div>
        </article>
      </div>
    </section>

    <!-- Informasi sistem -->
    <section class="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-strong">
        <Icon name="material-symbols:info" class="h-5 w-5 text-brand-700 dark:text-brand-400" aria-hidden="true" />
        Informasi Sistem
      </h2>

      <dl class="mt-3 divide-y divide-line text-sm">
        <div
          v-for="item in systemInfo"
          :key="item.label"
          class="grid gap-1 py-2.5 sm:grid-cols-3 sm:gap-3">
          <dt class="text-muted">{{ item.label }}</dt>
          <dd class="text-body sm:col-span-2">{{ item.value }}</dd>
        </div>
      </dl>
    </section>

    <!-- Kontak -->
    <section class="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-strong">
        <Icon name="material-symbols:contact-mail" class="h-5 w-5 text-brand-700 dark:text-brand-400" aria-hidden="true" />
        Kontak &amp; Tautan
      </h2>

      <p class="mt-3 text-sm leading-relaxed text-body">
        Demo aplikasi tersedia atas permintaan. Silakan hubungi pengembang melalui email
        untuk memperoleh akses atau informasi lebih lanjut.
      </p>

      <div class="mt-4 flex flex-wrap gap-2">
        <a
          :href="`mailto:${developer.email}`"
          class="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-medium text-body transition hover:border-brand-300 hover:text-brand-700 dark:hover:border-brand-700 dark:hover:text-brand-300">
          <Icon name="material-symbols:mail" class="h-4 w-4" aria-hidden="true" />
          {{ developer.email }}
        </a>
        <a
          :href="demoLink"
          class="inline-flex items-center gap-1.5 rounded-lg bg-brand-700 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-brand-800">
          <Icon name="material-symbols:open-in-new" class="h-4 w-4" aria-hidden="true" />
          Minta akses demo
        </a>
      </div>
    </section>

    <!-- Kredit -->
    <section class="rounded-2xl border border-line bg-surface p-6 sm:p-8">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-strong">
        <Icon name="material-symbols:verified" class="h-5 w-5 text-brand-700 dark:text-brand-400" aria-hidden="true" />
        Kredit
      </h2>

      <dl class="mt-3 space-y-2 text-sm">
        <div>
          <dt class="text-muted">Pengembang</dt>
          <dd class="text-body">Muhammad Ghazali Alhakim</dd>
        </div>
        <div>
          <dt class="text-muted">Pembimbing</dt>
          <dd class="text-body">Relsas Yogica, S.Pd., M.Pd.</dd>
        </div>
        <div>
          <dt class="text-muted">Penanggap</dt>
          <dd class="text-body">Dr. Heffi Alberida, S.Pd., M.Si.; Fitri Olvia Rahmi, S.Pd., M.Pd.</dd>
        </div>
        <div>
          <dt class="text-muted">Kredit pihak ketiga</dt>
          <dd class="text-body">
            Ikon dari Iconify (Material Symbols, Fluent, Lucide) serta library open source
            yang digunakan pada aplikasi ini.
          </dd>
        </div>
      </dl>

      <p class="mt-4 text-xs text-muted">
        © 2026 E-Bio X · Muhammad Ghazali Alhakim · Universitas Negeri Padang
      </p>
    </section>
  </div>
</template>

<script setup>
definePageMeta({
  layout: "public",
});

useHead({
  title: "Tentang Pengembang",
  meta: [
    {
      name: "description",
      content:
        "Profil pengembang dan informasi penelitian E-Bio X, website pembelajaran biologi terintegrasi machine learning di Universitas Negeri Padang.",
    },
    { name: "author", content: "Muhammad Ghazali Alhakim" },
  ],
});

const developer = {
  name: "Muhammad Ghazali Alhakim",
  initials: "MG",
  role: "Pengembang Website · Peneliti",
  email: "ghazalialhakim@student.unp.ac.id",
};

const institution = {
  university: "Universitas Negeri Padang",
  faculty: "Fakultas Matematika dan Ilmu Pengetahuan Alam",
  program: "Program Studi Pendidikan Biologi",
  location: "Padang, Sumatera Barat",
};

const research = {
  title:
    "Pengembangan Website Pembelajaran Biologi Terintegrasi Machine Learning sebagai Suplemen Belajar untuk Peserta Didik Fase E SMA",
  type: "Skripsi",
  year: "2026",
  scope: "Pembelajaran biologi Fase E SMA (kelas X)",
};

const features = [
  "Materi interaktif dengan blok konten dan pertanyaan.",
  "Kuis dan bank soal dengan penilaian otomatis.",
  "Analitik berbasis machine learning untuk memantau penguasaan materi.",
  "Penjelasan jawaban berbasis AI yang divalidasi guru.",
  "Forum diskusi kelas antara siswa dan guru.",
  "Manajemen kelas, materi, dan pengguna.",
];

const supervisors = [
  { name: "Relsas Yogica, S.Pd., M.Pd.", role: "Dosen Pembimbing", initials: "RY" },
  { name: "Dr. Heffi Alberida, S.Pd., M.Si.", role: "Dosen Penanggap 1", initials: "HA" },
  { name: "Fitri Olvia Rahmi, S.Pd., M.Pd.", role: "Dosen Penanggap 2", initials: "FR" },
];

const systemInfo = [
  { label: "Nama aplikasi", value: "E-Bio X" },
  { label: "Jenis", value: "Platform pembelajaran biologi berbasis AI (LMS)" },
  { label: "Versi", value: "1.0.0" },
  { label: "Status", value: "Uji Coba Terbatas" },
  { label: "Frontend", value: "Nuxt 3, Vue 3, Nuxt UI, Tailwind CSS, TypeScript" },
  { label: "Backend", value: "Flask, SQLAlchemy, MySQL, JWT" },
  { label: "Machine learning", value: "scikit-learn" },
  { label: "AI", value: "LLM melalui API kompatibel OpenAI" },
  {
    label: "Lisensi",
    value: "© 2026 Muhammad Ghazali Alhakim. Seluruh hak dilindungi.",
  },
  { label: "Terakhir diperbarui", value: "Oktober 2026" },
];

const demoLink =
  "mailto:ghazalialhakim@student.unp.ac.id?subject=" +
  encodeURIComponent("Permintaan akses demo E-Bio X");
</script>
