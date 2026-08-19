<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-semibold">Riwayat Belajar</h2>
        <p class="text-sm text-gray-500">Semua materi yang kamu ikuti beserta progres & penguasaannya.</p>
      </div>
      <NuxtLink
        to="/student/dashboard"
        class="text-sm text-green-600 hover:underline flex items-center gap-1"
      >
        <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
        Kembali ke Dashboard
      </NuxtLink>
    </div>

    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="summary">
      <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ summary.total }}</p>
          <p class="text-xs text-gray-500">Total Materi</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p class="text-2xl font-bold text-green-600">{{ summary.completed }}</p>
          <p class="text-xs text-gray-500">Selesai</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p class="text-2xl font-bold text-amber-500">{{ summary.in_progress }}</p>
          <p class="text-xs text-gray-500">Sedang Berjalan</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p class="text-2xl font-bold text-blue-600">{{ summary.average_progress }}%</p>
          <p class="text-xs text-gray-500">Progres Rata-rata</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 text-center">
          <p class="text-2xl font-bold text-purple-600">{{ minutesText }}</p>
          <p class="text-xs text-gray-500">Total Waktu Belajar</p>
        </div>
      </div>

      <div class="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div class="hidden md:grid grid-cols-[1fr_150px_120px_110px] gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-800 text-xs font-semibold text-gray-500 uppercase">
          <span>Materi</span>
          <span>Progres</span>
          <span>Status</span>
          <span class="text-right">Penguasaan</span>
        </div>
        <div
          v-for="m in materials"
          :key="m.material_id"
          class="grid grid-cols-1 md:grid-cols-[1fr_150px_120px_110px] gap-3 items-center px-4 py-3 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800"
        >
          <div class="min-w-0">
            <NuxtLink :to="`/student/progress/${m.material_id}`" class="font-semibold text-gray-800 dark:text-gray-100 hover:text-green-600 truncate block">
              {{ m.title }}
            </NuxtLink>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ m.topic || "Tanpa topik" }} · {{ m.completed_sections }}/{{ m.total_sections }} bagian
              <span class="mx-1">·</span>{{ minutesOf(m.learning_seconds) }} belajar
            </p>
          </div>
          <div class="flex items-center gap-2">
            <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div class="h-full bg-green-600 rounded-full" :style="{ width: m.progress_percentage + '%' }"></div>
            </div>
            <span class="text-xs font-semibold w-9 text-right">{{ Math.round(m.progress_percentage) }}%</span>
          </div>
          <span class="text-xs px-2 py-1 rounded-full font-medium text-center w-max" :class="statusClass(m.status)">
            {{ statusLabel(m.status) }}
          </span>
          <div class="text-right">
            <span class="text-sm font-bold" :class="masteryColor(m.mastery.label)">{{ m.mastery.label }}</span>
            <p class="text-xs text-gray-400">{{ m.mastery.score }}</p>
          </div>
        </div>
        <div v-if="materials.length === 0" class="text-center py-16 text-gray-500">
          Belum ada riwayat belajar.
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const materials = ref([]);
const summary = ref(null);
const loading = ref(true);

const formatSeconds = (s) => {
  s = s || 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}j ${m}m` : `${m}m`;
};
const minutesOf = (s) => formatSeconds(s);
const minutesText = computed(() => formatSeconds(summary.value?.total_learning_seconds));

const statusLabel = (s) => {
  const map = { belum_dimulai: "Belum Dimulai", dimulai: "Dimulai", sedang_belajar: "Sedang Belajar", selesai: "Selesai" };
  return map[s] || s;
};
const statusClass = (s) => {
  const map = {
    belum_dimulai: "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300",
    dimulai: "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400",
    sedang_belajar: "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400",
    selesai: "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400",
  };
  return map[s] || map.belum_dimulai;
};
const masteryColor = (label) => {
  const map = { "Baik Sekali": "text-green-600", Baik: "text-emerald-600", Cukup: "text-amber-500", Kurang: "text-red-500" };
  return map[label] || "text-gray-500";
};

const load = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/student/progress`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    summary.value = res.summary;
    materials.value = res.materials;
  } catch (e) {
    toast.add({ title: "Gagal memuat riwayat", color: "red" });
  } finally {
    loading.value = false;
  }
};

load();

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>