<template>
  <div class="container mx-auto px-3 sm:px-4 py-4 sm:py-6">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4 sm:mb-6">
      <div>
        <h2 class="text-xl sm:text-2xl font-semibold">Kuis Saya</h2>
        <p class="text-xs sm:text-sm text-gray-500">Kerjakan kuis dari gurumu dan ukur pemahamanmu.</p>
      </div>
      <div class="flex gap-1.5 text-[10px] sm:text-xs overflow-x-auto pb-1 -mb-1">
        <button
          v-for="f in filters"
          :key="f.value"
          class="px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg border transition whitespace-nowrap shrink-0"
          :class="activeFilter === f.value
            ? 'bg-green-600 border-green-600 text-white'
            : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300'"
          @click="activeFilter = f.value"
        >
          {{ f.label }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat kuis...</div>

    <div v-else-if="filtered.length === 0" class="text-center py-12 sm:py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-600 rounded-xl">
      <Icon name="material-symbols:quiz" class="w-12 h-12 sm:w-14 sm:h-14 text-gray-300 mx-auto mb-3" />
      <p class="text-sm text-gray-500">Belum ada kuis yang tersedia untuk Anda.</p>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
      <StudentQuizCard
        v-for="q in filtered"
        :key="q.id"
        :quiz="q"
      />
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const quizzes = ref([]);
const loading = ref(true);
const activeFilter = ref("all");

const filters = [
  { value: "all", label: "Semua" },
  { value: "not_started", label: "Belum" },
  { value: "in_progress", label: "Berjalan" },
  { value: "completed", label: "Selesai" },
];

const filtered = computed(() => {
  if (activeFilter.value === "all") return quizzes.value;
  return quizzes.value.filter((q) => q.student_status === activeFilter.value);
});

const load = async () => {
  loading.value = true;
  try {
    quizzes.value = await $fetch(`${config.public.backend}/api/student/quizzes`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat kuis", color: "red" });
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