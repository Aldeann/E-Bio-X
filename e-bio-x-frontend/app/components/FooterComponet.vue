<template>
  <footer class="px-6 pb-6 pt-2">
    <div class="mx-auto max-w-6xl border-t border-line pt-5 text-center">
      <p class="text-xs text-muted sm:text-sm">
        &copy; {{ year }} E-Bio X &middot; Dikembangkan oleh
        <NuxtLink
          to="/tentang"
          class="font-medium text-body transition hover:text-brand-700 hover:underline dark:hover:text-brand-300">
          Muhammad Ghazali Alhakim
        </NuxtLink>
      </p>
      <p class="mt-1 text-xs text-muted">
        Program Studi Pendidikan Biologi &middot; FMIPA &middot; Universitas Negeri Padang
      </p>
      <p class="mt-2 flex flex-wrap items-center justify-center gap-x-2 gap-y-1 text-xs text-muted">
        <NuxtLink
          to="/tentang"
          class="transition hover:text-brand-700 hover:underline dark:hover:text-brand-300">
          Tentang Pengembang
        </NuxtLink>
        <span aria-hidden="true">&middot;</span>
        <a
          :href="`mailto:${email}`"
          class="transition hover:text-brand-700 hover:underline dark:hover:text-brand-300">
          Email
        </a>
      </p>
    </div>
  </footer>
</template>

<script setup>
const year = new Date().getFullYear();
const email = "ghazalialhakim@student.unp.ac.id";
</script>
