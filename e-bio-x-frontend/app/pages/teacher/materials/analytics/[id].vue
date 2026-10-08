<script setup>
import { ref, computed, onMounted } from "vue";

const route = useRoute();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const data = ref(null);
const prereq = ref(null);
const loading = ref(true);

const analytics = computed(() => data.value?.analytics || {});
const students = computed(() => analytics.value.students_list || []);

// Hanya bagian yang benar-benar punya prasyarat yang ditampilkan.
const prereqRows = computed(() =>
  (prereq.value?.sections || []).filter((s) => (s.prerequisites || []).length)
);

const SOURCE_LABELS = {
  reference: "rujukan judul",
  similarity: "kemiripan isi",
  position: "urutan posisi",
};
const sourceLabel = (s) => SOURCE_LABELS[s] || s;
const sourceClass = (s) =>
  ({
    reference: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
    similarity: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
    position: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  }[s] || "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300");

const fetchData = async () => {
  loading.value = true;
  const headers = { Authorization: `Bearer ${token}` };
  try {
    const [res, peta] = await Promise.all([
      $fetch(`${config.public.backend}/api/materials/${route.params.id}/analytics`, {
        headers,
      }),
      // Peta prasyarat otomatis bersifat pelengkap: bila gagal, halaman
      // analitik tetap tampil (jangan sampai satu panel menjatuhkan semua).
      $fetch(
        `${config.public.backend}/api/teacher/materials/${route.params.id}/prerequisites`,
        { headers }
      ).catch(() => null),
    ]);
    data.value = res;
    prereq.value = peta;
  } catch (e) {
    toast.add({ title: "Gagal memuat analitik.", color: "red" });
  } finally {
    loading.value = false;
  }
};

onMounted(fetchData);

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>

<template>
  <div>
    <div class="mb-6">
      <NuxtLink
        to="/teacher/materials"
        class="text-sm text-green-600 hover:underline flex items-center gap-1 mb-2"
      >
        <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
        Kembali ke Materi
      </NuxtLink>
      <h1 class="text-2xl font-bold text-green-700 dark:text-green-400">Analitik Materi</h1>
      <p v-if="data" class="text-sm text-gray-500">{{ data.title }}</p>
    </div>

    <div v-if="loading" class="flex justify-center py-20 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin" />
    </div>

    <template v-else>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <p class="text-sm text-gray-500 flex items-center gap-1">
            <Icon name="mdi:account-multiple" class="w-4 h-4" />
            Siswa yang mengakses
          </p>
          <p class="text-3xl font-bold text-gray-800 dark:text-gray-100 mt-1">
            {{ analytics.students || 0 }}
          </p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
          <p class="text-sm text-gray-500 flex items-center gap-1">
            <Icon name="material-symbols:monitoring" class="w-4 h-4" />
            Rata-rata penyelesaian
          </p>
          <p class="text-3xl font-bold text-gray-800 dark:text-gray-100 mt-1">
            {{ analytics.completion_percentage || 0 }}%
          </p>
          <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mt-2">
            <div
              class="h-full bg-green-500 rounded-full"
              :style="{ width: (analytics.completion_percentage || 0) + '%' }"
            ></div>
          </div>
        </div>
      </div>

      <div
        v-if="prereq"
        class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden mb-6"
      >
        <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-800 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 class="font-semibold text-gray-800 dark:text-gray-100 flex items-center gap-1.5">
              <Icon name="material-symbols:hub" class="w-5 h-5 text-green-600" />
              Peta Prasyarat Otomatis
            </h3>
            <p class="text-xs text-gray-500 mt-0.5">{{ prereq.method }}</p>
            <p class="text-xs text-gray-400 mt-0.5">
              Diturunkan dari isi bagian — guru tidak mengisi apa pun. Bersifat saran, tidak mengunci akses.
            </p>
          </div>
          <div class="flex flex-wrap gap-1.5 text-xs">
            <span class="px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">
              rujukan judul: {{ prereq.source_counts?.reference || 0 }}
            </span>
            <span class="px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300">
              kemiripan isi: {{ prereq.source_counts?.similarity || 0 }}
            </span>
            <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
              urutan posisi: {{ prereq.source_counts?.position || 0 }}
            </span>
          </div>
        </div>

        <div v-if="prereqRows.length === 0" class="p-6 text-center text-gray-400 text-sm">
          Belum ada prasyarat yang bisa diturunkan dari konten materi ini.
        </div>

        <ul v-else class="divide-y divide-gray-100 dark:divide-gray-800">
          <li v-for="s in prereqRows" :key="s.section_id" class="px-4 py-3">
            <p class="text-sm font-medium text-gray-800 dark:text-gray-100">{{ s.title }}</p>
            <ul class="mt-1.5 space-y-1">
              <li
                v-for="p in s.prerequisites"
                :key="p.section_id + '-' + p.source"
                class="flex flex-wrap items-center gap-2 text-xs"
              >
                <span class="px-1.5 py-0.5 rounded font-medium" :class="sourceClass(p.source)">
                  {{ sourceLabel(p.source) }}
                </span>
                <span class="text-gray-700 dark:text-gray-200">
                  {{ p.title }}
                  <span
                    v-if="p.material_id && p.material_id !== prereq.material_id"
                    class="text-gray-400"
                  >· {{ p.material_title }}</span>
                </span>
                <span class="text-gray-400 italic">{{ p.rationale }}</span>
              </li>
            </ul>
          </li>
        </ul>
      </div>

      <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden">
        <h3 class="font-semibold text-gray-800 dark:text-gray-100 px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          Progress per Siswa
        </h3>

        <div v-if="students.length === 0" class="p-6 text-center text-gray-400">
          Belum ada siswa yang mengakses materi ini.
        </div>

        <table v-else class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 border-b border-gray-100 dark:border-gray-800">
              <th class="px-4 py-3 font-medium">Siswa</th>
              <th class="px-4 py-3 font-medium w-40">Progress</th>
              <th class="px-4 py-3 font-medium text-right">Selesai</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in students"
              :key="s.student_id"
              class="border-b border-gray-50 dark:border-gray-800"
            >
              <td class="px-4 py-3 text-gray-800 dark:text-gray-100">{{ s.name }}</td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-green-500 rounded-full"
                      :style="{ width: s.percentage + '%' }"
                    ></div>
                  </div>
                  <span class="text-xs text-gray-500 w-10 text-right">{{ s.percentage }}%</span>
                </div>
              </td>
              <td class="px-4 py-3 text-right text-gray-500">
                {{ s.completed }}/{{ s.total }} section
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>