<template>
  <div class="space-y-3">
    <div
      v-for="(q, i) in questions"
      :key="q.question_id"
      class="bg-white dark:bg-gray-900 border rounded-xl shadow-sm p-5"
      :class="q.is_correct ? 'border-green-300 dark:border-green-700' : 'border-red-300 dark:border-red-700'"
    >
      <div class="flex items-center gap-2 flex-wrap">
        <span
          class="w-7 h-7 flex items-center justify-center rounded-full text-white text-sm font-semibold shrink-0"
          :class="q.is_correct ? 'bg-green-500' : 'bg-red-500'"
        >
          <Icon :name="q.is_correct ? 'material-symbols:check' : 'material-symbols:close'" class="w-4 h-4" />
        </span>
        <span class="font-semibold">Soal {{ i + 1 }}</span>
        <span class="text-xs text-gray-500 ml-auto">
          {{ q.points_earned }} / {{ q.points }} poin
        </span>
      </div>

      <p class="mt-2 font-medium">{{ q.text }}</p>
      <img
        v-if="q.image_url"
        :src="q.image_url"
        alt="Gambar soal"
        class="mt-3 max-h-48 rounded-lg border border-gray-200 dark:border-gray-700"
      />

      <div class="mt-3 space-y-1.5 text-sm">
        <div
          v-for="o in q.options"
          :key="o.option_id"
          class="flex items-center gap-2 p-2.5 rounded-lg border"
          :class="optionClass(o)"
        >
          <span class="w-5 h-5 shrink-0 flex items-center justify-center rounded-full border-2 text-white text-xs"
            :class="optionBadge(o)">
            <Icon v-if="o.correct" name="material-symbols:check" class="w-3.5 h-3.5" />
            <Icon v-else-if="o.selected" name="material-symbols:close" class="w-3.5 h-3.5" />
          </span>
          <span>{{ o.option_text }}</span>
          <span v-if="o.correct" class="ml-auto text-xs text-green-600 font-medium shrink-0">Kunci jawaban</span>
          <span v-else-if="o.selected" class="ml-auto text-xs text-red-500 font-medium shrink-0">Jawaban Anda</span>
        </div>
      </div>

      <div v-if="showExplanation" class="mt-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-sm text-blue-800 dark:text-blue-300">
        <span class="font-semibold">Pembahasan: </span>{{ q.explanation || "Tidak ada pembahasan." }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  questions: { type: Array, required: true },
  showExplanation: { type: Boolean, default: false },
});

const optionClass = (o) => {
  if (o.correct) return "border-green-500 bg-green-50 dark:bg-green-900/30";
  if (o.selected) return "border-red-500 bg-red-50 dark:bg-red-900/30";
  return "border-gray-200 dark:border-gray-700";
};

const optionBadge = (o) => {
  if (o.correct) return "bg-green-600 border-green-600";
  if (o.selected) return "bg-red-500 border-red-500";
  return "border-gray-300 dark:border-gray-600";
};
</script>