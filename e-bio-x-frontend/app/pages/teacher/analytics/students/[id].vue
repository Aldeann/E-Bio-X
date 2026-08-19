<template>
  <div class="container mx-auto px-4 py-6">
    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="detail">
      <div class="mb-6">
        <NuxtLink to="/teacher/analytics" class="text-sm text-green-600 hover:underline flex items-center gap-1 mb-1">
          <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
          Kembali ke Analitik
        </NuxtLink>
        <h2 class="text-2xl font-semibold">{{ detail.student.name }}</h2>
        <p class="text-sm text-gray-500">{{ detail.student.email }}</p>
        <div class="flex flex-wrap gap-1.5 mt-2" v-if="detail.student.enrolled_courses.length">
          <span v-for="c in detail.student.enrolled_courses" :key="c.id" class="text-xs px-2 py-1 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400">
            {{ c.name }}
          </span>
        </div>
      </div>

      <!-- Summary -->
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-6">
        <div v-for="card in summaryCards" :key="card.label" class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4 text-center">
          <p class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ card.value }}</p>
          <p class="text-xs text-gray-500 mt-1">{{ card.label }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <!-- Materials -->
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
          <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 font-semibold text-gray-800 dark:text-gray-100">
            Progres per Materi
          </div>
          <div v-if="detail.materials.length" class="divide-y divide-gray-100 dark:divide-gray-800">
            <div v-for="m in detail.materials" :key="m.material_id" class="px-4 py-3">
              <NuxtLink :to="`/student/progress/${m.material_id}`" class="font-medium text-sm hover:text-green-600">
                {{ m.title }}
              </NuxtLink>
              <p class="text-xs text-gray-500 mb-1.5">{{ m.topic || "-" }} · {{ m.completed_sections }}/{{ m.total_sections }} bagian</p>
              <div class="flex items-center gap-2">
                <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div class="h-full bg-green-600 rounded-full" :style="{ width: m.progress_percentage + '%' }"></div>
                </div>
                <span class="text-xs font-semibold">{{ m.progress_percentage }}%</span>
              </div>
              <div class="flex justify-between text-xs text-gray-500 mt-1.5">
                <span>{{ minutesOf(m.learning_seconds) }} belajar</span>
                <span class="font-semibold" :class="masteryColor(m.mastery.label)">{{ m.mastery.label }} ({{ m.mastery.score }})</span>
              </div>
            </div>
          </div>
          <p v-else class="px-4 py-8 text-center text-sm text-gray-500">Belum ada progres materi.</p>
        </div>

        <!-- Quizzes -->
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
          <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 font-semibold text-gray-800 dark:text-gray-100">
            Riwayat Kuis
          </div>
          <div v-if="detail.quizzes.length" class="divide-y divide-gray-100 dark:divide-gray-800">
            <div v-for="q in detail.quizzes" :key="q.quiz_id + '-' + q.attempt_number" class="px-4 py-3 flex items-center justify-between gap-3">
              <div class="min-w-0">
                <p class="text-sm font-medium truncate">{{ q.quiz_title || 'Kuis #' + q.quiz_id }}</p>
                <p class="text-xs text-gray-500">Percobaan {{ q.attempt_number }} · {{ q.correct_count }} benar, {{ q.wrong_count }} salah</p>
              </div>
              <div class="text-right shrink-0">
                <p class="text-sm font-bold" :class="(q.percentage || 0) >= 75 ? 'text-green-600' : 'text-red-500'">{{ q.percentage }}%</p>
                <p class="text-xs text-gray-400">{{ formatDate(q.submitted_at) }}</p>
              </div>
            </div>
          </div>
          <p v-else class="px-4 py-8 text-center text-sm text-gray-500">Belum ada kuis dikerjakan.</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
const route = useRoute();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const detail = ref(null);
const loading = ref(true);

const minutesOf = (s) => {
  s = s || 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}j ${m}m` : `${m}m`;
};
const formatDate = (iso) => {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
};
const masteryColor = (label) => {
  const map = { "Baik Sekali": "text-green-600", Baik: "text-emerald-600", Cukup: "text-amber-500", Kurang: "text-red-500" };
  return map[label] || "text-gray-500";
};
const summaryCards = computed(() => {
  const s = detail.value?.summary || {};
  return [
    { label: "Materi Selesai", value: s.materials_completed ?? 0 },
    { label: "Progres Rata-rata", value: s.average_progress ? s.average_progress + "%" : "0%" },
    { label: "Waktu Belajar", value: minutesOf(s.learning_seconds) },
    { label: "Kuis Dikerjakan", value: s.quiz_attempts ?? 0 },
    { label: "Rata-rata Kuis", value: s.quiz_avg ? s.quiz_avg + "%" : "0%" },
    { label: "Akurasi Interaktif", value: s.interactive_accuracy ? s.interactive_accuracy + "%" : "0%" },
  ];
});

const load = async () => {
  loading.value = true;
  try {
    detail.value = await $fetch(`${config.public.backend}/api/teacher/analytics/students/${route.params.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Data siswa tidak dapat diakses.";
    toast.add({ title: msg, color: "red" });
  } finally {
    loading.value = false;
  }
};

load();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>