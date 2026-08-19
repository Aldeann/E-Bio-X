<template>
  <div class="container mx-auto px-4 py-6">
    <div class="mb-6">
      <h2 class="text-2xl font-semibold">Dashboard Belajar</h2>
      <p class="text-sm text-gray-500">
        Pantau progres belajarmu, lanjutkan materi, dan lihat hasil kuismu.
      </p>
    </div>

    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="data">
      <!-- Summary cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
        <div
          v-for="card in summaryCards"
          :key="card.label"
          class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4"
        >
          <div class="flex items-center justify-between">
            <Icon :name="card.icon" class="w-5 h-5 text-green-600 dark:text-green-500" />
            <span class="text-2xl font-bold text-gray-800 dark:text-gray-100">
              {{ card.value }}
            </span>
          </div>
          <p class="text-xs text-gray-500 mt-2">{{ card.label }}</p>
        </div>
      </div>

      <!-- Continue learning -->
      <div v-if="data.continue_learning && data.continue_learning.length" class="mb-8">
        <h4 class="text-lg font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
          <Icon name="material-symbols:play-circle" class="w-5 h-5" />
          Lanjutkan Belajar
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <NuxtLink
            v-for="m in data.continue_learning"
            :key="m.material_id"
            :to="`/student/materials/${m.material_id}`"
            class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4 hover:shadow-lg transition"
          >
            <p class="font-semibold text-gray-800 dark:text-gray-100 truncate">{{ m.title }}</p>
            <p class="text-xs text-gray-500 mt-1 mb-2">
              Topik: {{ m.topic || "-" }} <span v-if="m.phase">· Fase {{ m.phase }}</span>
            </p>
            <div class="flex items-center gap-3">
              <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-green-600 rounded-full"
                  :style="{ width: m.progress_percentage + '%' }"
                ></div>
              </div>
              <span class="text-xs font-semibold text-green-700 dark:text-green-400">
                {{ Math.round(m.progress_percentage) }}%
              </span>
            </div>
            <p v-if="m.last_section_title" class="text-xs text-gray-400 mt-2 truncate">
              Terakhir: {{ m.last_section_title }}
            </p>
          </NuxtLink>
        </div>
      </div>

      <!-- Materials progress -->
      <div class="mb-8">
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-lg font-semibold text-green-700 dark:text-green-400 flex items-center gap-2">
            <Icon name="material-symbols:menu-book" class="w-5 h-5" />
            Progres Materi
          </h4>
          <NuxtLink to="/student/progress" class="text-sm text-green-600 hover:underline">
            Lihat riwayat →
          </NuxtLink>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div
            v-for="m in data.materials"
            :key="m.material_id"
            class="flex flex-wrap md:flex-nowrap items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900 border-b last:border-b-0 border-gray-100 dark:border-gray-800"
          >
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-sm text-gray-800 dark:text-gray-100 truncate">{{ m.title }}</p>
              <p class="text-xs text-gray-500">{{ m.topic || "Tanpa topik" }} · {{ m.total_sections }} bagian</p>
            </div>
            <div class="w-full md:w-40">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div class="h-full bg-green-600 rounded-full" :style="{ width: m.progress_percentage + '%' }"></div>
                </div>
                <span class="text-xs font-semibold w-9 text-right">{{ Math.round(m.progress_percentage) }}%</span>
              </div>
            </div>
            <span
              class="text-xs px-2 py-1 rounded-full font-medium shrink-0"
              :class="statusClass(m.status)"
            >
              {{ statusLabel(m.status) }}
            </span>
            <NuxtLink
              :to="`/student/materials/${m.material_id}`"
              class="text-sm px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white shrink-0"
            >
              {{ m.status === 'selesai' ? 'Ulangi' : 'Buka' }}
            </NuxtLink>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from "vue";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const data = ref(null);
const loading = ref(true);

const formatSeconds = (s) => {
  s = s || 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h} jam ${m} mnt` : `${m} mnt`;
};

const summaryCards = computed(() => {
  const s = data.value?.summary || {};
  return [
    { label: "Materi Selesai", value: s.materials_completed ?? 0, icon: "material-symbols:task-alt" },
    { label: "Progres Rata-rata", value: s.average_progress ? s.average_progress + "%" : "0%", icon: "material-symbols:percent" },
    { label: "Kuis Dikerjakan", value: s.quizzes_taken ?? 0, icon: "material-symbols:quiz" },
    { label: "Rata-rata Kuis", value: s.quiz_avg ? s.quiz_avg + "%" : "0%", icon: "material-symbols:monitoring" },
    { label: "Waktu Belajar", value: formatSeconds(s.learning_seconds), icon: "material-symbols:schedule" },
    { label: "Soal Interaktif", value: s.interactive_answered ?? 0, icon: "material-symbols:question-answer" },
    { label: "Akurasi Interaktif", value: s.interactive_accuracy ? s.interactive_accuracy + "%" : "0%", icon: "material-symbols:verified" },
    { label: "Materi Diikuti", value: s.materials_started ?? 0, icon: "material-symbols:menu-book" },
  ];
});

const statusLabel = (s) => {
  const map = {
    belum_dimulai: "Belum Dimulai",
    dimulai: "Dimulai",
    sedang_belajar: "Sedang Belajar",
    selesai: "Selesai",
  };
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

const load = async () => {
  loading.value = true;
  try {
    data.value = await $fetch(`${config.public.backend}/api/student/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat dashboard", color: "red" });
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