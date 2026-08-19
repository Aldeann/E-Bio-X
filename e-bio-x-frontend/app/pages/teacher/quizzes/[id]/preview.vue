<template>
  <div class="container mx-auto px-4 py-6 max-w-4xl">
    <div class="flex items-center gap-2 mb-6">
      <button class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" @click="$router.push(`/teacher/quizzes/${quizId}`)">
        <Icon name="material-symbols:arrow-back" class="w-6 h-6" />
      </button>
      <h2 class="text-2xl font-semibold">Pratinjau Kuis</h2>
    </div>
    <QuizPreview :quiz-id="quizId" />
  </div>
</template>

<script setup>
const quizId = Number(useRoute().params.id);

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>