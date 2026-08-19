<template>
  <div class="container mx-auto px-4 py-6">
    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="detail">
      <div class="mb-6">
        <NuxtLink to="/student/progress" class="text-sm text-green-600 hover:underline flex items-center gap-1 mb-1">
          <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
          Kembali ke Riwayat
        </NuxtLink>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-2xl font-semibold">{{ detail.title }}</h2>
            <p class="text-sm text-gray-500">
              {{ detail.topic || "Tanpa topik" }}
              <span v-if="detail.phase"> · Fase {{ detail.phase }}</span>
              <span v-if="detail.teacher_name"> · {{ detail.teacher_name }}</span>
            </p>
          </div>
          <NuxtLink
            :to="`/student/materials/${detail.material_id}`"
            class="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold"
          >
            {{ detail.status === 'selesai' ? 'Ulangi Belajar' : 'Lanjutkan Belajar' }}
          </NuxtLink>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <!-- Left: progress detail -->
        <div class="lg:col-span-2 space-y-5">
          <!-- Summary -->
          <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
            <div class="flex items-center justify-between mb-4">
              <h4 class="font-semibold text-gray-800 dark:text-gray-100">Ringkasan</h4>
              <span class="text-xs px-2 py-1 rounded-full font-medium" :class="statusClass(detail.status)">
                {{ statusLabel(detail.status) }}
              </span>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div class="text-center">
                <p class="text-2xl font-bold text-green-600">{{ Math.round(detail.progress_percentage) }}%</p>
                <p class="text-xs text-gray-500">Progres</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ detail.completed_sections }}/{{ detail.total_sections }}</p>
                <p class="text-xs text-gray-500">Bagian Selesai</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ minutesOf(detail.learning_seconds) }}</p>
                <p class="text-xs text-gray-500">Waktu Belajar</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold" :class="masteryColor(detail.mastery.label)">{{ detail.mastery.label }}</p>
                <p class="text-xs text-gray-500">Penguasaan ({{ detail.mastery.score }})</p>
              </div>
            </div>
            <div class="mt-4">
              <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span>Kemajuan materi</span>
                <span>{{ Math.round(detail.progress_percentage) }}%</span>
              </div>
              <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-green-600 rounded-full" :style="{ width: detail.progress_percentage + '%' }"></div>
              </div>
            </div>
          </div>

          <!-- Sections -->
          <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
            <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-4">Bagian Materi</h4>
            <div v-for="s in detail.sections" :key="s.section_id" class="py-2.5 border-b last:border-b-0 border-gray-100 dark:border-gray-800">
              <div class="flex items-center gap-3">
                <Icon
                  :name="s.completed ? 'material-symbols:check-circle' : 'material-symbols:radio-button-unchecked'"
                  class="w-5 h-5 shrink-0"
                  :class="s.completed ? 'text-green-600' : 'text-gray-300 dark:text-gray-600'"
                />
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-sm text-gray-800 dark:text-gray-100 truncate">{{ s.title }}</p>
                  <p class="text-xs text-gray-500">
                    {{ s.content_count }} konten · {{ s.content_viewed }}/{{ s.content_count }} dibuka
                  </p>
                </div>
                <span class="text-xs text-gray-500">{{ s.interactive_total }} soal interaktif</span>
              </div>
            </div>
          </div>

          <!-- Interactive & video -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
              <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 flex items-center gap-2">
                <Icon name="material-symbols:question-answer" class="w-5 h-5 text-green-600" />
                Soal Interaktif
              </h4>
              <div class="grid grid-cols-3 text-center gap-2">
                <div>
                  <p class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ detail.interactive.interactive_total }}</p>
                  <p class="text-xs text-gray-500">Dijawab</p>
                </div>
                <div>
                  <p class="text-xl font-bold text-green-600">{{ detail.interactive.interactive_correct }}</p>
                  <p class="text-xs text-gray-500">Benar</p>
                </div>
                <div>
                  <p class="text-xl font-bold text-blue-600">{{ detail.interactive.interactive_accuracy }}%</p>
                  <p class="text-xs text-gray-500">Akurasi</p>
                </div>
              </div>
              <div v-if="Object.keys(detail.interactive.difficulty_accuracy || {}).length" class="mt-3 space-y-1.5">
                <div v-for="(v, k) in detail.interactive.difficulty_accuracy" :key="k" class="flex items-center gap-2 text-xs">
                  <span class="w-14 capitalize text-gray-500">{{ k }}</span>
                  <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div class="h-full bg-green-600 rounded-full" :style="{ width: v.accuracy + '%' }"></div>
                  </div>
                  <span class="font-semibold w-10 text-right">{{ v.accuracy }}%</span>
                </div>
              </div>
            </div>
            <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
              <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 flex items-center gap-2">
                <Icon name="material-symbols:play-circle" class="w-5 h-5 text-green-600" />
                Video
              </h4>
              <div class="grid grid-cols-3 text-center gap-2">
                <div>
                  <p class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ detail.video.videos }}</p>
                  <p class="text-xs text-gray-500">Video</p>
                </div>
                <div>
                  <p class="text-xl font-bold text-green-600">{{ detail.video.completed_videos }}</p>
                  <p class="text-xs text-gray-500">Selesai</p>
                </div>
                <div>
                  <p class="text-xl font-bold text-blue-600">{{ detail.video.average_completion }}%</p>
                  <p class="text-xs text-gray-500">Rata-rata</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Activities -->
          <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
            <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Aktivitas Terakhir</h4>
            <div v-if="detail.activities.length" class="space-y-2.5">
              <div v-for="a in detail.activities" :key="a.id" class="flex items-start gap-2.5 text-sm">
                <Icon :name="activityIcon(a.event_type)" class="w-4 h-4 mt-0.5 text-green-600 shrink-0" />
                <div class="flex-1 min-w-0">
                  <p class="text-gray-800 dark:text-gray-100">{{ activityLabel(a.event_type) }}</p>
                  <p class="text-xs text-gray-400">{{ formatDate(a.created_at) }}</p>
                </div>
              </div>
            </div>
            <p v-else class="text-sm text-gray-500">Belum ada aktivitas.</p>
          </div>
        </div>

        <!-- Right: mastery -->
        <div class="space-y-5">
          <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
            <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 flex items-center gap-2">
              <Icon name="material-symbols:stars" class="w-5 h-5 text-amber-400" />
              Penguasaan Materi
            </h4>
            <div class="space-y-3">
              <div v-for="row in detail.mastery_rows" :key="row.source + '-' + (row.section_id || row.quiz_id)" class="flex items-center gap-3">
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-gray-800 dark:text-gray-100 truncate">{{ row.title }}</p>
                  <p class="text-xs text-gray-400">{{ row.source === 'section' ? 'Bagian' : 'Kuis' }}</p>
                </div>
                <div class="w-24">
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div class="h-full rounded-full" :class="barColor(row.mastery.label)" :style="{ width: (row.score || 0) + '%' }"></div>
                    </div>
                    <span class="text-xs font-bold w-9 text-right" :class="masteryColor(row.mastery.label)">{{ row.score || 0 }}</span>
                  </div>
                </div>
              </div>
              <div v-if="detail.mastery_rows.length === 0" class="text-sm text-gray-500">Data penguasaan belum tersedia.</div>
            </div>
          </div>

          <!-- Quiz performance -->
          <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
            <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Performa Kuis</h4>
            <div v-if="detail.quiz_performance.length" class="space-y-3">
              <div v-for="q in detail.quiz_performance" :key="q.quiz_id" class="border border-gray-100 dark:border-gray-800 rounded-lg p-3">
                <div class="flex items-center justify-between gap-2">
                  <p class="font-medium text-sm truncate">{{ q.title }}</p>
                  <NuxtLink
                    v-if="q.attempts"
                    :to="`/student/quizzes/${q.quiz_id}/result`"
                    class="text-xs text-green-600 hover:underline"
                  >
                    Lihat
                  </NuxtLink>
                </div>
                <div class="flex items-center gap-2 mt-1.5 text-xs">
                  <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div class="h-full bg-green-600 rounded-full" :style="{ width: (q.best || 0) + '%' }"></div>
                  </div>
                  <span class="font-semibold">{{ q.best || 0 }}%</span>
                </div>
                <p class="text-xs text-gray-400 mt-1">{{ q.attempts }} percobaan · rata-rata {{ q.average }}% · terbaik {{ q.best }}%</p>
              </div>
            </div>
            <p v-else class="text-sm text-gray-500">Belum ada kuis.</p>
          </div>
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
  const d = new Date(iso);
  return d.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
};
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
const barColor = (label) => {
  const map = { "Baik Sekali": "bg-green-600", Baik: "bg-emerald-500", Cukup: "bg-amber-500", Kurang: "bg-red-500" };
  return map[label] || "bg-gray-400";
};
const activityIcon = (t) => {
  const map = {
    material_opened: "material-symbols:log-in", material_closed: "material-symbols:logout",
    section_opened: "material-symbols:folder-open", section_completed: "material-symbols:check-circle",
    content_viewed: "material-symbols:visibility", video_played: "material-symbols:play-circle",
    video_paused: "material-symbols:pause-circle", video_completed: "material-symbols:task-alt",
    pdf_opened: "material-symbols:picture-as-pdf", question_answered: "material-symbols:quiz",
    quiz_started: "material-symbols:play-arrow", quiz_submitted: "material-symbols:send",
    material_completed: "material-symbols:celebration",
  };
  return map[t] || "material-symbols:touch-app";
};
const activityLabel = (t) => {
  const map = {
    material_opened: "Membuka materi", material_closed: "Menutup materi",
    section_opened: "Membuka bagian", section_completed: "Menyelesaikan bagian",
    content_viewed: "Melihat konten", video_played: "Memutar video",
    video_paused: "Menjeda video", video_completed: "Video selesai ditonton",
    pdf_opened: "Membuka PDF", interactive_started: "Mulai soal interaktif",
    question_answered: "Menjawab soal interaktif", quiz_started: "Mulai kuis",
    quiz_submitted: "Mengumpulkan kuis", material_completed: "Menyelesaikan materi",
    note_created: "Membuat catatan", bookmark_created: "Menandai bookmark",
  };
  return map[t] || t;
};

const load = async () => {
  loading.value = true;
  try {
    detail.value = await $fetch(`${config.public.backend}/api/student/progress/${route.params.id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Detail tidak dapat diakses.";
    toast.add({ title: msg, color: "red" });
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