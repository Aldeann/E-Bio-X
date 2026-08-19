<template>
  <div class="flex flex-wrap gap-1.5">
    <button
      v-for="(q, i) in questions"
      :key="q.question_id"
      type="button"
      class="w-9 h-9 rounded-lg text-sm font-medium transition border"
      :class="navClass(q, i)"
      @click="$emit('select', i)"
    >
      {{ i + 1 }}
    </button>
  </div>
  <div class="mt-4 grid grid-cols-2 gap-1.5 text-xs">
    <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-green-500 inline-block"></span> Dijawab</span>
    <span class="flex items-center gap-1"><span class="w-3 h-3 rounded bg-gray-200 dark:bg-gray-700 border inline-block"></span> Belum</span>
  </div>
</template>

<script setup>
defineProps({
  questions: { type: Array, required: true },
  answers: { type: Object, required: true },
  currentIndex: { type: Number, required: true },
});
defineEmits(["select"]);

const navClass = (q, i) => {
  const base = "text-gray-700 dark:text-gray-200 ";
  const isAnswered = answers[q.question_id] !== undefined && answers[q.question_id] !== null;
  if (i === currentIndex) {
    return base + "border-green-600 bg-green-600 text-white";
  }
  return base + (isAnswered
    ? "border-green-500 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300"
    : "border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800");
};
</script>