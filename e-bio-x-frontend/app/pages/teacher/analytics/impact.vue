<template>
  <div>
    <PageHeader
      title="Dampak Rekomendasi"
      subtitle="Apakah saran sistem dikerjakan siswa? Funnel baca → latihan → kuis, CTR rekomendasi, dan perbaikan latihan."
    />

    <!-- Filter bar -->
    <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 mb-6">
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <select v-model="filters.course_id" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm">
          <option value="">Semua Kelas</option>
          <option v-for="c in options.courses" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select v-model="filters.phase" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm">
          <option value="">Semua Fase</option>
          <option v-for="p in options.phases" :key="p" :value="p">Fase {{ p }}</option>
        </select>
        <select v-model="filters.topic" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm">
          <option value="">Semua Topik</option>
          <option v-for="t in options.topics" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-model="filters.material_id" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm">
          <option value="">Semua Materi</option>
          <option v-for="m in options.materials" :key="m.id" :value="m.id">{{ m.title }}</option>
        </select>
        <input v-model="filters.date_from" type="date" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm" />
        <input v-model="filters.date_to" type="date" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm" />
      </div>
      <div class="flex gap-2 mt-3">
        <button @click="load" class="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold">Terapkan</button>
        <button @click="resetFilters" class="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm font-semibold">Reset</button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else>
      <p class="text-xs text-gray-500 mb-4">
        Cakupan: {{ data.scope?.materials ?? 0 }} materi · {{ data.scope?.students ?? 0 }} siswa.
        <span v-if="data.generated_at"> Diperbarui {{ fmtTime(data.generated_at) }}.</span>
      </p>

      <!-- KPI cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <div class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:ads-click" class="w-5 h-5 text-green-600" />
            <span class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ data.recommendation?.ctr == null ? "–" : data.recommendation.ctr + "%" }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">CTR rekomendasi</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:visibility" class="w-5 h-5 text-blue-600" />
            <span class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ data.recommendation?.impressions ?? 0 }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Impresi (saran tayang)</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:touch-app" class="w-5 h-5 text-amber-600" />
            <span class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ data.recommendation?.clicked ?? 0 }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Klik setelah tayang</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:group" class="w-5 h-5 text-indigo-600" />
            <span class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ data.recommendation?.students_clicked ?? 0 }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Siswa yang klik</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:trending-up" class="w-5 h-5 text-emerald-600" />
            <span class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ data.practice_lift?.improve_rate == null ? "–" : data.practice_lift.improve_rate + "%" }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Latihan membaik</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
        <!-- Funnel -->
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-1">Funnel Belajar</h4>
          <p class="text-xs text-gray-500 mb-4">Siswa unik per tahap. Persentase dihitung dari siswa yang membuka materi.</p>
          <div v-for="(step, i) in funnelSteps" :key="step.key" class="mb-3">
            <div class="flex items-center justify-between text-sm mb-1">
              <span class="text-gray-700 dark:text-gray-200 flex items-center gap-1.5">
                <Icon :name="step.icon" class="w-4 h-4 text-green-600" />
                {{ step.label }}
              </span>
              <span class="font-semibold text-gray-800 dark:text-gray-100">
                {{ step.value }} <span class="text-xs text-gray-400">({{ step.rate == null ? "–" : step.rate + "%" }})</span>
              </span>
            </div>
            <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div class="h-full rounded-full bg-green-600 transition-all" :style="{ width: barWidth(step.value) + '%' }"></div>
            </div>
          </div>
        </div>

        <!-- Recommendation follow-through -->
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-1">Tindak Lanjut Setelah Klik</h4>
          <p class="text-xs text-gray-500 mb-4">
            Dari {{ data.recommendation?.students_clicked ?? 0 }} siswa yang mengklik saran, berapa yang benar-benar berlatih/berkuis setelahnya.
          </p>
          <div class="space-y-4">
            <div>
              <div class="flex items-center justify-between text-sm mb-1">
                <span class="text-gray-700 dark:text-gray-200">Berlatih setelah klik</span>
                <span class="font-semibold">{{ fmtPct(data.recommendation?.practice_after_click_rate) }}</span>
              </div>
              <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full rounded-full bg-indigo-500" :style="{ width: (data.recommendation?.practice_after_click_rate || 0) + '%' }"></div>
              </div>
              <p class="text-[11px] text-gray-400 mt-1">{{ data.recommendation?.followed_practice ?? 0 }} siswa</p>
            </div>
            <div>
              <div class="flex items-center justify-between text-sm mb-1">
                <span class="text-gray-700 dark:text-gray-200">Kuis setelah klik</span>
                <span class="font-semibold">{{ fmtPct(data.recommendation?.quiz_after_click_rate) }}</span>
              </div>
              <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full rounded-full bg-amber-500" :style="{ width: (data.recommendation?.quiz_after_click_rate || 0) + '%' }"></div>
              </div>
              <p class="text-[11px] text-gray-400 mt-1">{{ data.recommendation?.followed_quiz ?? 0 }} siswa</p>
            </div>
          </div>
          <p class="text-[11px] text-gray-400 mt-4">
            Impresi = pasangan (siswa × materi) yang sarannya benar-benar ditayangkan. CTR = klik setelah tayang / impresi (maks. 100%).
            <span v-if="data.recommendation?.clicks_without_impression">
              {{ data.recommendation.clicks_without_impression }} klik lama belum punya impresi tercatat sehingga tidak dihitung di CTR.
            </span>
          </p>
        </div>
      </div>

      <!-- Practice lift -->
      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 mb-6">
        <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-1">Perbaikan Latihan (soal diulang)</h4>
        <p class="text-xs text-gray-500 mb-4">
          {{ data.practice_lift?.retried_questions ?? 0 }} soal dijawab lebih dari sekali. Membaik = salah di percobaan pertama, benar di percobaan terakhir.
        </p>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p class="text-2xl font-bold text-emerald-600">{{ data.practice_lift?.improved ?? 0 }}</p>
            <p class="text-xs text-gray-500">Membaik</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-red-500">{{ data.practice_lift?.regressed ?? 0 }}</p>
            <p class="text-xs text-gray-500">Menurun</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-gray-700 dark:text-gray-200">{{ fmtPct(data.practice_lift?.first_attempt_accuracy) }}</p>
            <p class="text-xs text-gray-500">Akurasi percobaan pertama</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-gray-700 dark:text-gray-200">{{ fmtPct(data.practice_lift?.last_attempt_accuracy) }}</p>
            <p class="text-xs text-gray-500">Akurasi percobaan terakhir</p>
          </div>
        </div>
      </div>

      <!-- Per material table -->
      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
        <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Rincian per Materi</h4>
        <div v-if="data.by_material?.length" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-gray-500 border-b border-gray-200 dark:border-gray-700">
                <th class="py-2 pr-3">Materi</th>
                <th class="py-2 px-2 text-right">Dibuka</th>
                <th class="py-2 px-2 text-right">Selesai baca</th>
                <th class="py-2 px-2 text-right">Latihan</th>
                <th class="py-2 px-2 text-right">Kuis</th>
                <th class="py-2 px-2 text-right">Impresi</th>
                <th class="py-2 px-2 text-right">Klik</th>
                <th class="py-2 pl-2 text-right">CTR</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in data.by_material" :key="m.material_id" class="border-b border-gray-100 dark:border-gray-800">
                <td class="py-2 pr-3">
                  <p class="font-medium text-gray-800 dark:text-gray-100 truncate max-w-xs">{{ m.title }}</p>
                  <p class="text-xs text-gray-400">{{ m.topic || "–" }}</p>
                </td>
                <td class="py-2 px-2 text-right">{{ m.opened }}</td>
                <td class="py-2 px-2 text-right">{{ m.read }}</td>
                <td class="py-2 px-2 text-right">{{ m.practiced }}</td>
                <td class="py-2 px-2 text-right">{{ m.quizzed }}</td>
                <td class="py-2 px-2 text-right">{{ m.impressions }}</td>
                <td class="py-2 px-2 text-right">{{ m.clicked }}</td>
                <td class="py-2 pl-2 text-right font-semibold">{{ fmtPct(m.ctr) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="text-sm text-gray-500">Belum ada data pada cakupan ini.</p>
      </div>
    </template>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const loading = ref(true);
const options = ref({ courses: [], phases: [], topics: [], materials: [] });
const filters = ref({ course_id: "", phase: "", topic: "", material_id: "", date_from: "", date_to: "" });
const data = ref({
  scope: {}, funnel: {}, recommendation: {}, practice_lift: {}, by_material: [],
});

const authHeaders = () => ({ Authorization: `Bearer ${token}` });

const paramsOf = () => {
  const p = {};
  for (const [k, v] of Object.entries(filters.value)) if (v) p[k] = v;
  return p;
};

const fmtPct = (v) => (v == null ? "–" : v + "%");
const fmtTime = (iso) => {
  try {
    return new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
};

const funnelSteps = computed(() => {
  const f = data.value.funnel || {};
  return [
    { key: "opened", label: "Membuka materi", value: f.opened ?? 0, rate: null, icon: "material-symbols:menu-book" },
    { key: "read", label: "Selesai membaca", value: f.read ?? 0, rate: f.read_rate, icon: "material-symbols:task-alt" },
    { key: "practiced", label: "Latihan adaptif", value: f.practiced ?? 0, rate: f.practice_rate, icon: "material-symbols:fitness-center" },
    { key: "quizzed", label: "Mengerjakan kuis", value: f.quizzed ?? 0, rate: f.quiz_rate, icon: "material-symbols:quiz" },
  ];
});

const barWidth = (value) => {
  const max = Math.max(...funnelSteps.value.map((s) => s.value), 1);
  return Math.round((value / max) * 100);
};

const load = async () => {
  loading.value = true;
  try {
    const [opts, res] = await Promise.allSettled([
      $fetch(`${config.public.backend}/api/teacher/analytics/options`, { headers: authHeaders() }),
      $fetch(`${config.public.backend}/api/teacher/analytics/impact?${new URLSearchParams(paramsOf())}`, { headers: authHeaders() }),
    ]);
    if (opts.status === "fulfilled") options.value = opts.value;
    if (res.status === "fulfilled") data.value = res.value;
    else toast.add({ title: "Gagal memuat dampak rekomendasi", color: "red" });
  } finally {
    loading.value = false;
  }
};

const resetFilters = () => {
  filters.value = { course_id: "", phase: "", topic: "", material_id: "", date_from: "", date_to: "" };
  load();
};

load();

definePageMeta({
  layout: "teacher",
  middleware: "auth",
  role: "teacher",
});
</script>
