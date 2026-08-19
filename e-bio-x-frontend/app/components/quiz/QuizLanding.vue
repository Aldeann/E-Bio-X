<template>
  <div v-if="quiz" class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-8 max-w-3xl mx-auto">
    <div class="text-center">
      <span
        class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium"
        :class="landingBadge"
      >
        {{ statusLabel }}
      </span>
      <h3 class="text-2xl font-bold mt-3">{{ quiz.title }}</h3>
      <p v-if="quiz.description" class="text-gray-500 mt-2">{{ quiz.description }}</p>
      <p v-if="quiz.material_title" class="text-sm text-gray-500 mt-1">
        Materi: {{ quiz.material_title }}
        <template v-if="quiz.section_title"> · Bagian: {{ quiz.section_title }}</template>
      </p>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6 text-center">
      <div class="bg-green-50 dark:bg-green-900/40 rounded-xl py-4">
        <p class="text-xl font-bold text-green-700 dark:text-green-500">{{ quiz.question_count }}</p>
        <p class="text-xs text-gray-500">Soal</p>
      </div>
      <div class="bg-green-50 dark:bg-green-900/40 rounded-xl py-4">
        <p class="text-xl font-bold text-green-700 dark:text-green-500">{{ quiz.duration || "-" }}</p>
        <p class="text-xs text-gray-500">Menit</p>
      </div>
      <div class="bg-green-50 dark:bg-green-900/40 rounded-xl py-4">
        <p class="text-xl font-bold text-green-700 dark:text-green-500">{{ quiz.passing_grade }}%</p>
        <p class="text-xs text-gray-500">Nilai Lulus</p>
      </div>
      <div class="bg-green-50 dark:bg-green-900/40 rounded-xl py-4">
        <p class="text-xl font-bold text-green-700 dark:text-green-500">{{ quiz.attempts_used }}/{{ quiz.max_attempts }}</p>
        <p class="text-xs text-gray-500">Percobaan</p>
      </div>
    </div>

    <div v-if="quiz.student_status === 'completed'" class="mt-6">
      <div class="text-center">
        <p class="text-sm text-gray-600 dark:text-gray-300">
          Skor terbaik: <span class="text-lg font-bold text-green-700 dark:text-green-500">{{ quiz.best_percentage }}%</span>
          ({{ quiz.passed ? "Lulus" : "Belum lulus" }})
        </p>
      </div>
      <div class="mt-4 flex gap-3 justify-center">
        <NuxtLink
          :to="`/student/quizzes/${quiz.id}/result`"
          class="bg-green-600 hover:bg-green-700 text-white px-5 py-2.5 rounded-lg transition"
        >
          Lihat Pembahasan
        </NuxtLink>
        <button
          v-if="quiz.attempts_used < quiz.max_attempts"
          class="border border-green-600 text-green-700 dark:text-green-400 px-5 py-2.5 rounded-lg hover:bg-green-50 dark:hover:bg-gray-800 transition"
          @click="$emit('start')"
        >
          Kerjakan Lagi
        </button>
      </div>
    </div>

    <button
      v-else
      class="mt-8 w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg text-lg font-semibold transition shadow-lg shadow-green-300/40"
      @click="$emit('start')"
    >
      {{ quiz.student_status === 'in_progress' ? 'Lanjutkan Mengerjakan' : 'Mulai Kerjakan' }}
    </button>

    <div v-if="quiz.student_status === 'in_progress' && quiz.attempts_used >= quiz.max_attempts" class="text-center mt-4 text-xs text-red-500">
      Kesempatan mengerjakan tersisa, namun masih ada pengerjaan yang belum dikumpulkan.
    </div>

    <p v-if="quiz.student_status === 'completed' && quiz.attempts_used >= quiz.max_attempts" class="text-center mt-4 text-sm text-gray-500">
      Kesempatan mengerjakan sudah habis.
    </p>
  </div>
</template>

<script setup>
defineProps({
  quiz: { type: Object, required: true },
});
defineEmits(["start"]);

const statusLabel = computed(() => {
  if (props.quiz.student_status === "in_progress") return "Sedang Berjalan";
  if (props.quiz.student_status === "completed") return props.quiz.passed ? "Lulus" : "Belum Lulus";
  return "Belum Dikerjakan";
});

const landingBadge = computed(() => {
  if (props.quiz.student_status === "in_progress")
    return "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400";
  if (props.quiz.student_status === "completed")
    return props.quiz.passed
      ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400"
      : "bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-400";
  return "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300";
});
</script>