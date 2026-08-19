<script setup>
defineProps({
  title: { type: String, default: "" },
  total: { type: Number, default: 0 },
  completed: { type: Number, default: 0 },
  percentage: { type: Number, default: 100 },
});

const emit = defineEmits(["restart"]);
</script>

<template>
  <div class="rounded-2xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-8 text-center max-w-xl mx-auto shadow-sm">
    <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center">
      <Icon name="material-symbols:celebration" class="w-12 h-12 text-green-600 dark:text-green-400" />
    </div>
    <h1 class="text-2xl font-bold text-green-700 dark:text-green-400">Materi Selesai!</h1>
    <p class="text-gray-700 dark:text-gray-200 font-semibold mt-2">{{ title }}</p>
    <p class="text-gray-500 mt-1">Anda telah menyelesaikan materi ini.</p>

    <div class="mt-6 max-w-xs mx-auto">
      <MaterialProgress :percentage="percentage" />
      <p class="text-sm text-gray-600 dark:text-gray-300 mt-3">
        Section selesai: <span class="font-bold">{{ completed }} / {{ total }}</span>
      </p>
    </div>

    <div class="flex flex-wrap justify-center gap-3 mt-8">
      <NuxtLink
        to="/student/materials"
        class="px-5 py-2.5 rounded-lg text-sm font-semibold bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-100 hover:bg-gray-300 dark:hover:bg-gray-600 flex items-center gap-1"
      >
        <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
        Daftar Materi
      </NuxtLink>
      <button
        @click="emit('restart')"
        class="px-5 py-2.5 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white flex items-center gap-1"
      >
        <Icon name="material-symbols:replay" class="w-4 h-4" />
        Pelajari Kembali
      </button>
    </div>

    <div class="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800 text-[11px] text-gray-400">
      Fitur rekomendasi materi akan segera hadir.
    </div>
  </div>
</template>