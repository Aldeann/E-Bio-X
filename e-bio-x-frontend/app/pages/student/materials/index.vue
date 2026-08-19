<script setup>
import { ref, computed, onMounted } from "vue";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const materials = ref([]);
const courses = ref([]);
const loading = ref(true);

const search = ref("");
const filterPhase = ref("semua");
const filterCourse = ref("semua");
const filterDifficulty = ref("semua");
const filterStatus = ref("semua");
const sortBy = ref("terbaru");

const phases = ref([]);
const difficulties = ref(["mudah", "sedang", "sulit"]);

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/materials`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    materials.value = res || [];
    courses.value = [...new Set((res || []).flatMap((m) => m.courses || []))];
    phases.value = [...new Set((res || []).map((m) => m.phase))];
  } catch (e) {
    toast.add({ title: "Gagal memuat materi.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const filtered = computed(() => {
  let list = [];
  const q = search.value.trim().toLowerCase();
  if (q) {
    list = materials.value.filter(
      (m) =>
        (m.title || "").toLowerCase().includes(q) ||
        (m.topic || "").toLowerCase().includes(q) ||
        (m.subject || "").toLowerCase().includes(q)
    );
  } else {
    list = [...materials.value];
  }

  if (filterPhase.value !== "semua") list = list.filter((m) => m.phase === filterPhase.value);
  if (filterCourse.value !== "semua")
    list = list.filter((m) => (m.courses || []).includes(filterCourse.value));
  if (filterDifficulty.value !== "semua")
    list = list.filter((m) => m.difficulty === filterDifficulty.value);
  if (filterStatus.value === "belum") list = list.filter((m) => !m.student_progress || m.student_progress.completed === 0);
  if (filterStatus.value === "berlangsung")
    list = list.filter(
      (m) =>
        m.student_progress &&
        m.student_progress.completed > 0 &&
        !m.student_progress.finished
    );
  if (filterStatus.value === "selesai") list = list.filter((m) => m.student_progress && m.student_progress.finished);

  switch (sortBy.value) {
    case "terbaru":
      list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      break;
    case "terlama":
      list.sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
      break;
    case "az":
      list.sort((a, b) => (a.title || "").localeCompare(b.title || ""));
      break;
    case "za":
      list.sort((a, b) => (b.title || "").localeCompare(a.title || ""));
      break;
  }
  return list;
});

const activeFilterCount = computed(
  () =>
    (filterPhase.value !== "semua" ? 1 : 0) +
    (filterCourse.value !== "semua" ? 1 : 0) +
    (filterDifficulty.value !== "semua" ? 1 : 0) +
    (filterStatus.value !== "semua" ? 1 : 0) +
    (sortBy.value !== "terbaru" ? 1 : 0)
);

const resetFilters = () => {
  search.value = "";
  filterPhase.value = "semua";
  filterCourse.value = "semua";
  filterDifficulty.value = "semua";
  filterStatus.value = "semua";
  sortBy.value = "terbaru";
};

onMounted(fetchData);

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-green-700 dark:text-green-400 mb-1">
      Materi Pembelajaran
    </h1>
    <p class="text-sm text-gray-500 mb-6">
      Telusuri dan mulai belajar materi dari guru Anda.
    </p>

    <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-6 space-y-3">
      <div class="relative">
        <Icon
          name="material-symbols:search"
          class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5"
        />
        <input
          v-model="search"
          type="search"
          placeholder="Cari judul, topik, atau mata pelajaran..."
          class="w-full pl-10 pr-3 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
        />
      </div>

      <div class="flex flex-wrap gap-2 text-sm">
        <select
          v-model="filterCourse"
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:outline-none"
        >
          <option value="semua">Semua Kelas</option>
          <option v-for="c in courses" :key="c" :value="c">{{ c }}</option>
        </select>
        <select
          v-model="filterPhase"
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:outline-none"
        >
          <option value="semua">Semua Fase</option>
          <option v-for="f in phases" :key="f" :value="f">Fase {{ f }}</option>
        </select>
        <select
          v-model="filterDifficulty"
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:outline-none"
        >
          <option value="semua">Semua Kesulitan</option>
          <option v-for="d in difficulties" :key="d" :value="d">{{ d }}</option>
        </select>
        <select
          v-model="filterStatus"
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:outline-none"
        >
          <option value="semua">Semua Status</option>
          <option value="belum">Belum Dibuka</option>
          <option value="berlangsung">Sedang Berlangsung</option>
          <option value="selesai">Selesai</option>
        </select>
        <select
          v-model="sortBy"
          class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:outline-none"
        >
          <option value="terbaru">Terbaru</option>
          <option value="terlama">Terlama</option>
          <option value="az">A–Z</option>
          <option value="za">Z–A</option>
        </select>
        <button
          v-if="activeFilterCount > 0"
          @click="resetFilters"
          class="px-3 py-2 rounded-lg text-sm font-semibold bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-300 hover:bg-red-100"
        >
          Reset ({{ activeFilterCount }})
        </button>
      </div>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 animate-pulse bg-white dark:bg-gray-900 h-56"></div>
    </div>

    <div v-else-if="materials.length === 0" class="text-center py-20 text-gray-400">
      <Icon name="material-symbols:auto-stories-outline" class="w-16 h-16 mx-auto mb-3" />
      <p>Belum ada materi yang dipublikasikan guru.</p>
    </div>

    <div v-else-if="filtered.length === 0" class="text-center py-20 text-gray-400">
      <Icon name="material-symbols:manage-search" class="w-16 h-16 mx-auto mb-3" />
      <p>Tidak ada materi yang cocok dengan pencarian/filter.</p>
      <button
        @click="resetFilters"
        class="mt-3 px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white"
      >
        Reset Filter
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <StudentMaterialCard v-for="m in filtered" :key="m.id" :material="m" />
    </div>
  </div>
</template>