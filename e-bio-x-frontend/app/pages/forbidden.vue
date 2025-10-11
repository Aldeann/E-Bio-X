<template>
  <main class="flex-1 px-4 py-6 max-w-6xl mx-auto w-full">
    <div class="p-8 text-center">
      <h1 class="text-3xl font-bold text-red-600">Akses Ditolak</h1>
      <p class="text-gray-600 mt-2">Maaf, Anda tidak memiliki izin untuk mengakses halaman ini.</p>
      <button @click="$router.back()" class="mt-4 px-4 py-2 bg-green-600 text-white rounded">
        Kembali
      </button>
    </div>
  </main>
</template>

<script setup>
definePageMeta({
  layout: "blank",
});
</script>