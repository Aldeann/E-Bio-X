<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-semibold">Manajemen Kuis</h2>
        <p class="text-sm text-gray-500">Buat, publikasikan, dan pantau kuis interaktif materi.</p>
      </div>
      <div class="flex gap-2">
        <NuxtLink
          to="/teacher/question-bank"
          class="border border-green-600 text-green-700 dark:text-green-400 px-4 py-2 rounded-lg hover:bg-green-50 dark:hover:bg-gray-800 transition flex items-center gap-1"
        >
          <Icon name="material-symbols:database" class="w-5 h-5" /> Bank Soal
        </NuxtLink>
        <NuxtLink
          to="/teacher/quizzes/create"
          class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition flex items-center gap-1 shadow-md shadow-green-300/50"
        >
          <Icon name="material-symbols:add" class="w-5 h-5" /> Buat Kuis
        </NuxtLink>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat kuis...</div>

    <div v-else-if="quizzes.length === 0" class="text-center py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-600 rounded-xl">
      <Icon name="material-symbols:quiz" class="w-14 h-14 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">Belum ada kuis. Klik "Buat Kuis" untuk membuat kuis pertama.</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="q in quizzes"
        :key="q.id"
        class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md hover:shadow-lg hover:shadow-green-300/40 transition p-5 flex flex-col"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="flex items-center gap-2 text-sm">
            <span
              class="px-2 py-0.5 rounded-full text-xs"
              :class="statusClass(q.status)"
            >{{ statusLabel(q.status) }}</span>
            <span class="text-xs text-gray-500">{{ q.question_count }} soal · {{ q.total_points }} poin</span>
          </div>
          <button
            class="text-red-500 hover:text-red-700"
            title="Hapus kuis"
            @click="removeQuiz(q)"
          >
            <Icon name="material-symbols:delete" class="w-5 h-5" />
          </button>
        </div>

        <h3 class="mt-2 font-semibold text-lg">{{ q.title }}</h3>
        <p v-if="q.description" class="text-sm text-gray-500 line-clamp-2 mt-1">{{ q.description }}</p>

        <div class="mt-3 flex flex-wrap gap-1.5 text-xs">
          <span
            v-if="q.material_title"
            class="px-2 py-1 rounded-full bg-green-50 dark:bg-green-900/40 text-green-700 dark:text-green-400"
          >
            {{ q.material_title }}
          </span>
          <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            Durasi {{ q.duration || "-" }} mnt
          </span>
          <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            Lulus {{ q.passing_grade }}%
          </span>
        </div>

        <div v-if="q.stats" class="mt-3 grid grid-cols-3 gap-2 text-center text-xs border-t border-gray-100 dark:border-gray-800 pt-3">
          <div>
            <p class="font-semibold text-green-700 dark:text-green-500 text-base">{{ q.stats.participants }}</p>
            <p class="text-gray-500">Peserta</p>
          </div>
          <div>
            <p class="font-semibold text-green-700 dark:text-green-500 text-base">{{ q.stats.attempts }}</p>
            <p class="text-gray-500">Percobaan</p>
          </div>
          <div>
            <p class="font-semibold text-green-700 dark:text-green-500 text-base">{{ q.stats.avg_percentage }}%</p>
            <p class="text-gray-500">Rata-rata</p>
          </div>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-2 mt-auto pt-4">
          <NuxtLink
            :to="`/teacher/quizzes/${q.id}`"
            class="bg-green-600 hover:bg-green-700 text-white text-sm px-3 py-2 rounded-lg text-center transition"
          >
            Kelola
          </NuxtLink>
          <NuxtLink
            :to="`/teacher/quizzes/${q.id}/analytics`"
            class="border border-green-600 text-green-700 dark:text-green-400 text-sm px-3 py-2 rounded-lg text-center hover:bg-green-50 dark:hover:bg-gray-800 transition"
          >
            Analitik
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const quizzes = ref([]);
const loading = ref(true);

const load = async () => {
  loading.value = true;
  try {
    quizzes.value = await $fetch(`${config.public.backend}/api/teacher/quizzes`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat daftar kuis", color: "red" });
  } finally {
    loading.value = false;
  }
};

const statusLabel = (s) => (s === "published" ? "Published" : s === "archived" ? "Archived" : "Draft");
const statusClass = (s) =>
  s === "published"
    ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400"
    : s === "archived"
    ? "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
    : "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400";

const removeQuiz = async (q) => {
  const result = await swal.fire({
    title: `Hapus kuis "${q.title}"?`,
    text: "Semua soal dan hasil siswa akan ikut terhapus. Tidak dapat dikembalikan.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/teacher/quizzes/${q.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Kuis dihapus", color: "green" });
    await load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal menghapus kuis", color: "red" });
  }
};

load();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>