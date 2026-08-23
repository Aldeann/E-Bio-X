<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-semibold">Analitik Pembelajaran</h2>
        <p class="text-sm text-gray-500">
          Pantau progres siswa, penguasaan materi, kinerja kuis, dan topik.
        </p>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 mb-6">
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
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
        <input v-model="filters.search" type="text" placeholder="Cari siswa..." class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm" />
        <input v-model="filters.date_from" type="date" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm" />
        <input v-model="filters.date_to" type="date" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm" />
        <select v-model="filters.status_learning" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm">
          <option value="">Semua Status</option>
          <option v-for="s in options.status_learnings" :key="s" :value="s">{{ statusLabel(s) }}</option>
        </select>
        <select v-model="filters.mastery_status" class="form-input border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg text-sm">
          <option value="">Semua Penguasaan</option>
          <option v-for="s in options.mastery_statuses" :key="s" :value="s">{{ s }}</option>
        </select>
      </div>
      <div class="flex gap-2 mt-3">
        <button @click="applyFilters" class="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold">
          Terapkan
        </button>
        <button @click="resetFilters" class="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm font-semibold">
          Reset
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else>
      <!-- Overview cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
        <div v-for="c in overviewCards" :key="c.label" class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon :name="c.icon" class="w-5 h-5 text-green-600 dark:text-green-500" />
            <span class="text-xl font-bold text-gray-800 dark:text-gray-100">{{ c.value }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">{{ c.label }}</p>
        </div>
      </div>

      <!-- Distributions -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Distribusi Penguasaan</h4>
          <div v-for="(v, k) in overview.mastery_distribution" :key="k" class="flex items-center gap-3 mb-2">
            <span class="w-24 text-sm text-gray-600 dark:text-gray-300">{{ k }}</span>
            <div class="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div class="h-full rounded-full" :class="barColor(k)" :style="{ width: distPct(overview.mastery_distribution, k) + '%' }"></div>
            </div>
            <span class="text-sm font-semibold w-8 text-right">{{ v }}</span>
          </div>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Distribusi Status Belajar</h4>
          <div v-for="(v, k) in overview.status_distribution" :key="k" class="flex items-center gap-3 mb-2">
            <span class="w-24 text-sm text-gray-600 dark:text-gray-300">{{ statusLabel(k) }}</span>
            <div class="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div class="h-full rounded-full bg-blue-500" :style="{ width: distPct(overview.status_distribution, k) + '%' }"></div>
            </div>
            <span class="text-sm font-semibold w-8 text-right">{{ v }}</span>
          </div>
        </div>
      </div>

      <!-- Topics & difficulty -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Analitik per Topik</h4>
          <div v-if="topics.length" class="space-y-3">
            <div v-for="t in topics" :key="t.topic" class="flex items-center gap-3">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate">{{ t.topic }}</p>
                <p class="text-xs text-gray-500">{{ t.materials }} materi · {{ t.students_started }} siswa mulai</p>
              </div>
              <div class="w-28">
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div class="h-full rounded-full bg-green-600" :style="{ width: t.average_progress + '%' }"></div>
                  </div>
                  <span class="text-xs font-bold w-8 text-right">{{ t.average_progress }}%</span>
                </div>
              </div>
            </div>
          </div>
          <p v-else class="text-sm text-gray-500">Belum ada data topik.</p>
        </div>

        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Kinerja per Tingkat Kesulitan</h4>
          <div class="space-y-4">
            <div>
              <p class="text-xs font-semibold text-gray-500 mb-2">Soal Interaktif</p>
              <div v-for="(v, k) in difficulty.interactive" :key="'i-' + k" class="flex items-center gap-3 mb-1.5">
                <span class="w-16 text-sm capitalize text-gray-600 dark:text-gray-300">{{ k }}</span>
                <div class="flex-1 h-2.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div class="h-full rounded-full bg-amber-500" :style="{ width: (v.accuracy || 0) + '%' }"></div>
                </div>
                <span class="text-xs font-semibold w-10 text-right">{{ v.accuracy || 0 }}%</span>
              </div>
              <p v-if="Object.keys(difficulty.interactive || {}).length === 0" class="text-xs text-gray-400">Belum ada.</p>
            </div>
            <div>
              <p class="text-xs font-semibold text-gray-500 mb-2">Kuis</p>
              <div v-for="(v, k) in difficulty.quiz" :key="'q-' + k" class="flex items-center gap-3 mb-1.5">
                <span class="w-16 text-sm capitalize text-gray-600 dark:text-gray-300">{{ k }}</span>
                <div class="flex-1 h-2.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div class="h-full rounded-full bg-blue-500" :style="{ width: (v.accuracy || 0) + '%' }"></div>
                </div>
                <span class="text-xs font-semibold w-10 text-right">{{ v.accuracy || 0 }}%</span>
              </div>
              <p v-if="Object.keys(difficulty.quiz || {}).length === 0" class="text-xs text-gray-400">Belum ada.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Materials table -->
      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden mb-6">
        <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100">Per Materi</h4>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-gray-500 uppercase bg-gray-50 dark:bg-gray-800">
                <th class="px-4 py-2">Materi</th>
                <th class="px-4 py-2">Fase/Topik</th>
                <th class="px-4 py-2 text-right">Progres Rata-rata</th>
                <th class="px-4 py-2 text-right">Siswa Selesai</th>
                <th class="px-4 py-2 text-right">Akurasi Interaktif</th>
                <th class="px-4 py-2 text-right">Kuis</th>
                <th class="px-4 py-2 text-right">Waktu Rata-rata</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="m in materialSummary" :key="m.material_id" class="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer" @click="toggleMaterial(m.material_id)">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <Icon name="material-symbols:expand-more" class="w-4 h-4 text-gray-400 shrink-0" :class="{ 'rotate-180': expandedMaterial === m.material_id }" />
                    <span class="font-medium">{{ m.title }}</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-gray-500">{{ m.phase ? 'Fase ' + m.phase : '-' }} / {{ m.topic || '-' }}</td>
                <td class="px-4 py-2.5 text-right font-semibold">{{ m.students_completed ? ((m.students_completed / m.total_students) * 100).toFixed(0) : 0 }}%</td>
                <td class="px-4 py-2.5 text-right">{{ m.students_completed }}/{{ m.total_students }}</td>
                <td class="px-4 py-2.5 text-right">{{ m.interactive.accuracy }}%</td>
                <td class="px-4 py-2.5 text-right">{{ m.quiz.attempts }} percobaan</td>
                <td class="px-4 py-2.5 text-right">{{ (m.average_learning_seconds / 60).toFixed(1) }} mnt</td>
              </tr>
              <tr v-if="materialSummary.length === 0">
                <td colspan="7" class="px-4 py-10 text-center text-gray-500">Belum ada data materi.</td>
              </tr>
              <tr v-if="materialDetail" class="bg-green-50/50 dark:bg-green-900/10">
                <td colspan="7" class="p-4">
                  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                      <p class="text-xs font-semibold text-gray-500 mb-2">Penyelesaian Bagian</p>
                      <div v-for="s in materialDetail.section_completion" :key="s.section_id" class="flex items-center gap-2 mb-1.5">
                        <span class="text-xs flex-1 truncate">{{ s.title }}</span>
                        <div class="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div class="h-full bg-green-600 rounded-full" :style="{ width: s.completion_rate + '%' }"></div>
                        </div>
                        <span class="text-xs font-semibold w-10 text-right">{{ s.completion_rate }}%</span>
                      </div>
                      <NuxtLink :to="`/teacher/materials/analytics/${materialDetail.material_id}`" class="text-xs text-green-600 hover:underline">
                        Lihat analitik materi lengkap →
                      </NuxtLink>
                    </div>
                    <div>
                      <p class="text-xs font-semibold text-gray-500 mb-2">Siswa (paling aktif)</p>
                      <div v-for="s in materialDetail.per_student.slice(0, 6)" :key="s.student_id" class="flex items-center gap-2 mb-1.5 text-xs">
                        <span class="flex-1 truncate text-gray-700 dark:text-gray-200">Siswa #{{ s.student_id }}</span>
                        <div class="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div class="h-full rounded-full" :class="s.completed ? 'bg-green-600' : 'bg-blue-500'" :style="{ width: s.progress_percentage + '%' }"></div>
                        </div>
                        <span class="w-10 text-right font-semibold">{{ s.progress_percentage }}%</span>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Students table -->
      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden mb-6">
        <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100">Siswa</h4>
          <span class="text-xs text-gray-500">{{ students.total }} siswa</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-gray-500 uppercase bg-gray-50 dark:bg-gray-800">
                <th class="px-4 py-2">Nama</th>
                <th class="px-4 py-2 text-right">Progres</th>
                <th class="px-4 py-2 text-right">Kuis</th>
                <th class="px-4 py-2 text-right">Interaktif</th>
                <th class="px-4 py-2 text-right">Waktu</th>
                <th class="px-4 py-2">Status</th>
                <th class="px-4 py-2 text-right">Penguasaan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in students.students" :key="s.student_id" class="border-t border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800">
                <td class="px-4 py-2.5">
                  <NuxtLink :to="`/teacher/analytics/students/${s.student_id}`" class="font-medium hover:text-green-600">
                    {{ s.name }}
                  </NuxtLink>
                  <p class="text-xs text-gray-400">{{ s.email }}</p>
                </td>
                <td class="px-4 py-2.5 text-right font-semibold">{{ s.average_progress }}%</td>
                <td class="px-4 py-2.5 text-right">{{ s.quiz_attempts }} ({{ s.quiz_avg }}%)</td>
                <td class="px-4 py-2.5 text-right">{{ s.interactive_answered }} ({{ s.interactive_accuracy }}%)</td>
                <td class="px-4 py-2.5 text-right">{{ minutesOf(s.learning_seconds) }}</td>
                <td class="px-4 py-2.5">
                  <span class="text-xs px-2 py-1 rounded-full font-medium" :class="statusClass(s.status_learning)">{{ statusLabel(s.status_learning) }}</span>
                </td>
                <td class="px-4 py-2.5 text-right">
                  <span class="text-sm font-bold" :class="masteryColor(s.mastery.label)">{{ s.mastery.label }}</span>
                  <p class="text-xs text-gray-400">{{ s.mastery.score }}</p>
                </td>
              </tr>
              <tr v-if="students.students.length === 0">
                <td colspan="7" class="px-4 py-10 text-center text-gray-500">Tidak ada siswa yang cocok.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="students.total_pages > 1" class="px-4 py-3 flex items-center justify-between border-t border-gray-100 dark:border-gray-800">
          <button :disabled="students.page <= 1" @click="page--; loadStudents()" class="px-3 py-1.5 rounded-lg text-sm bg-gray-200 dark:bg-gray-700 disabled:opacity-40">Sebelumnya</button>
          <span class="text-sm text-gray-500">Hal {{ students.page }} dari {{ students.total_pages }}</span>
          <button :disabled="students.page >= students.total_pages" @click="page++; loadStudents()" class="px-3 py-1.5 rounded-lg text-sm bg-gray-200 dark:bg-gray-700 disabled:opacity-40">Berikutnya</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const loading = ref(true);
const overview = ref({ mastery_distribution: {}, status_distribution: {} });
const options = ref({ courses: [], phases: [], topics: [], materials: [], mastery_statuses: [], status_learnings: [] });
const topics = ref([]);
const difficulty = ref({ interactive: {}, quiz: {} });
const materialSummary = ref([]);
const students = ref({ students: [], page: 1, total_pages: 1, total: 0 });
const page = ref(1);
const expandedMaterial = ref(null);
const materialDetail = ref(null);

const filters = ref({
  course_id: "", phase: "", topic: "", material_id: "", search: "",
  date_from: "", date_to: "", status_learning: "", mastery_status: "",
});

const authHeaders = () => ({ Authorization: `Bearer ${token}` });

const paramsOf = () => {
  const p = {};
  for (const [k, v] of Object.entries(filters.value)) if (v) p[k] = v;
  return p;
};

const overviewCards = computed(() => {
  const o = overview.value || {};
  return [
    { label: "Materi", value: o.materials ?? 0, icon: "material-symbols:menu-book" },
    { label: "Siswa Terdaftar", value: o.students ?? 0, icon: "material-symbols:group" },
    { label: "Siswa Aktif", value: o.students_active ?? 0, icon: "material-symbols:bolt" },
    { label: "Progres Rata-rata", value: o.average_progress ? o.average_progress + "%" : "0%", icon: "material-symbols:percent" },
    { label: "Waktu Belajar", value: o.learning_hours ? o.learning_hours + " jam" : "0 jam", icon: "material-symbols:schedule" },
    { label: "Percobaan Kuis", value: o.quiz_attempts ?? 0, icon: "material-symbols:quiz" },
    { label: "Rata-rata Kuis", value: o.quiz_avg ? o.quiz_avg + "%" : "0%", icon: "material-symbols:monitoring" },
    { label: "Akurasi Interaktif", value: o.interactive_accuracy ? o.interactive_accuracy + "%" : "0%", icon: "material-symbols:verified" },
  ];
});

const minutesOf = (s) => {
  s = s || 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}j ${m}m` : `${m}m`;
};
const distPct = (dist, k) => {
  const total = Object.values(dist || {}).reduce((a, b) => a + b, 0);
  return total ? Math.round((dist[k] / total) * 100) : 0;
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

const loadAll = async () => {
  loading.value = true;
  const get = (url) => $fetch(url, { headers: authHeaders() });
  try {
    const [ov, opts, top, diff, mats, studs] = await Promise.allSettled([
      get(`${config.public.backend}/api/teacher/analytics?${new URLSearchParams(paramsOf())}`),
      get(`${config.public.backend}/api/teacher/analytics/options`),
      get(`${config.public.backend}/api/teacher/analytics/topics?${new URLSearchParams(paramsOf())}`),
      get(`${config.public.backend}/api/teacher/analytics/difficulty?${new URLSearchParams(paramsOf())}`),
      get(`${config.public.backend}/api/teacher/analytics/materials?${new URLSearchParams(paramsOf())}`),
      get(`${config.public.backend}/api/teacher/analytics/students?${new URLSearchParams({ ...paramsOf(), page: page.value, per_page: 10 })}`),
    ]);
    if (ov.status === "fulfilled") overview.value = ov.value;
    if (opts.status === "fulfilled") options.value = opts.value;
    if (top.status === "fulfilled") topics.value = top.value;
    if (diff.status === "fulfilled") difficulty.value = diff.value;
    if (studs.status === "fulfilled") students.value = studs.value;
    if (mats.status === "fulfilled" && mats.value) materialSummary.value = mats.value;
    else materialSummary.value = [];
  } catch (e) {
    toast.add({ title: "Gagal memuat analitik", color: "red" });
  } finally {
    loading.value = false;
  }
};

const toggleMaterial = async (materialId) => {
  if (expandedMaterial.value === materialId) {
    expandedMaterial.value = null;
    materialDetail.value = null;
    return;
  }
  expandedMaterial.value = materialId;
  try {
    materialDetail.value = await $fetch(
      `${config.public.backend}/api/teacher/analytics/materials/${materialId}`,
      { headers: authHeaders() }
    );
    const idx = materialSummary.value.findIndex((m) => m.material_id === materialId);
    if (idx >= 0 && materialDetail.value && !materialDetail.value.empty) {
      materialSummary.value[idx] = {
        ...materialSummary.value[idx],
        total_students: materialDetail.value.total_students,
        students_completed: materialDetail.value.students_completed,
        interactive: materialDetail.value.interactive,
        quiz: materialDetail.value.quiz,
        average_learning_seconds: materialDetail.value.average_learning_seconds,
      };
    }
  } catch (e) {
    materialDetail.value = null;
  }
};

const loadStudents = async () => {
  try {
    const res = await $fetch(
      `${config.public.backend}/api/teacher/analytics/students?${new URLSearchParams({ ...paramsOf(), page: page.value, per_page: 10 })}`,
      { headers: authHeaders() }
    );
    students.value = res;
  } catch (e) {
    toast.add({ title: "Gagal memuat daftar siswa", color: "red" });
  }
};

const applyFilters = () => {
  page.value = 1;
  loadAll();
  loadStudents();
};
const resetFilters = () => {
  filters.value = { course_id: "", phase: "", topic: "", material_id: "", search: "", date_from: "", date_to: "", status_learning: "", mastery_status: "" };
  page.value = 1;
  loadAll();
  loadStudents();
};

loadAll();
loadStudents();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>