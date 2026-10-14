<template>
  <!-- Judul halaman guru yang seragam: satu tempat untuk ukuran, warna,
       dan jarak, supaya tidak lagi beda-beda antar halaman. Tombol aksi
       ditaruh di slot default (kanan atas di layar lebar, bawah di HP). -->
  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
    <div class="min-w-0">
      <div v-if="icon || $slots.title" class="flex items-center gap-2">
        <Icon v-if="icon" :name="icon" class="w-6 h-6 text-green-600 dark:text-green-500 shrink-0" />
        <h1 class="text-xl sm:text-2xl font-bold text-green-700 dark:text-green-400 truncate">
          <slot name="title">{{ title }}</slot>
        </h1>
      </div>
      <h1 v-else class="text-xl sm:text-2xl font-bold text-green-700 dark:text-green-400 truncate">
        {{ title }}
      </h1>
      <p v-if="subtitle" class="text-xs sm:text-sm text-gray-500 mt-1">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.default" class="flex flex-wrap gap-2 shrink-0">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  icon: { type: String, default: "" },
});
</script>
