<template>
  <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md hover:shadow-lg hover:shadow-green-300/40 transition p-3 sm:p-5 flex flex-col">
    <div class="flex items-start justify-between gap-2">
      <span
        class="px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded-full text-[10px] sm:text-xs font-medium"
        :class="badgeClass"
      >
        {{ statusLabel }}
      </span>
      <span v-if="quiz.best_percentage !== null && quiz.best_percentage !== undefined" class="text-xs sm:text-sm font-semibold">
        Skor terbaik: <span class="text-green-700 dark:text-green-500">{{ quiz.best_percentage }}%</span>
      </span>
    </div>

    <h3 class="mt-2 font-semibold text-sm sm:text-lg">{{ quiz.title }}</h3>
    <p v-if="quiz.description" class="text-xs sm:text-sm text-gray-500 line-clamp-2 mt-1">{{ quiz.description }}</p>

    <div class="mt-2 sm:mt-3 flex flex-wrap gap-1 sm:gap-1.5 text-[10px] sm:text-xs">
      <span
        v-if="quiz.material_title"
        class="px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full bg-green-50 dark:bg-green-900/40 text-green-700 dark:text-green-400"
      >
        {{ quiz.material_title }}
      </span>
      <span class="px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
        {{ quiz.question_count }} soal
      </span>
      <span class="px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
        {{ quiz.duration || "-" }} menit
      </span>
      <span class="px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
        Lulus {{ quiz.passing_grade }}%
      </span>
      <span class="px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
        Percobaan {{ quiz.attempts_used }}/{{ quiz.max_attempts }}
      </span>
    </div>

    <div class="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-gray-100 dark:border-gray-800 mt-auto">
      <div v-if="quiz.student_status === 'completed'" class="grid grid-cols-2 gap-1.5 sm:gap-2">
        <NuxtLink
          :to="`/student/quizzes/${quiz.id}/result`"
          class="bg-green-600 hover:bg-green-700 text-white text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center transition"
        >
          Lihat Hasil
        </NuxtLink>
        <NuxtLink
          v-if="quiz.attempts_used < quiz.max_attempts"
          :to="`/student/quizzes/${quiz.id}`"
          class="border border-green-600 text-green-700 dark:text-green-400 text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center hover:bg-green-50 dark:hover:bg-gray-800 transition"
        >
          Ulangi
        </NuxtLink>
        <span
          v-else
          class="border border-gray-300 dark:border-gray-600 text-gray-400 text-xs sm:text-sm px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center"
        >
          Tidak ada sisa percobaan
        </span>
      </div>
      <NuxtLink
        v-else
        :to="`/student/quizzes/${quiz.id}`"
        class="block bg-green-600 hover:bg-green-700 text-white text-xs sm:text-sm px-3 py-1.5 sm:py-2 rounded-lg text-center transition"
      >
        {{ quiz.student_status === 'in_progress' ? 'Lanjutkan Mengerjakan' : 'Kerjakan Kuis' }}
      </NuxtLink>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  quiz: { type: Object, required: true },
});

const statusLabel = computed(() => {
  if (props.quiz.student_status === "in_progress") return "Sedang Berjalan";
  if (props.quiz.student_status === "completed") {
    return props.quiz.passed ? "Lulus" : "Belum Lulus";
  }
  return "Belum Dikerjakan";
});

const badgeClass = computed(() => {
  if (props.quiz.student_status === "in_progress")
    return "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400";
  if (props.quiz.student_status === "completed")
    return props.quiz.passed
      ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400"
      : "bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-400";
  return "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300";
});
</script>