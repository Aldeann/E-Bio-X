<template>
  <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-sm p-5">
    <div class="flex items-center gap-2 flex-wrap mb-3">
      <span class="text-sm font-semibold text-gray-600 dark:text-gray-300">Soal {{ index + 1 }}</span>
      <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400">
        {{ typeLabel }}
      </span>
      <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400">
        {{ difficultyLabel }}
      </span>
      <span class="text-xs text-gray-500 ml-auto">{{ question.points }} poin</span>
    </div>

    <p class="font-medium">{{ question.text }}</p>
    <img
      v-if="question.image_url"
      :src="question.image_url"
      alt="Gambar soal"
      class="mt-3 max-h-60 rounded-lg border border-gray-200 dark:border-gray-700 mx-auto"
    />

    <div class="mt-4 space-y-2.5">
      <button
        v-for="opt in question.options"
        :key="opt.option_id"
        type="button"
        class="w-full flex items-center gap-3 p-3 rounded-lg border text-left transition"
        :class="selectedClass(opt.option_id)"
        @click="select(opt.option_id)"
      >
        <span
          class="w-5 h-5 shrink-0 flex items-center justify-center rounded-full border-2"
          :class="selected === opt.option_id ? 'bg-green-600 border-green-600 text-white' : 'border-gray-300 dark:border-gray-600'"
        >
          <Icon v-if="selected === opt.option_id" name="material-symbols:check" class="w-4 h-4" />
        </span>
        <span>{{ opt.option_text }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  question: { type: Object, required: true },
  index: { type: Number, required: true },
  modelValue: { type: [Number, null], default: null },
});
const emit = defineEmits(["update:modelValue"]);

const selected = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const typeLabel = computed(() =>
  props.question.question_type === "true_false" ? "Benar/Salah" : "Pilihan Ganda"
);
const difficultyLabel = computed(() =>
  props.question.difficulty === "easy" ? "Mudah" : props.question.difficulty === "hard" ? "Sulit" : "Sedang"
);

const select = (optId) => {
  emit("update:modelValue", optId);
};

const selectedClass = (optId) =>
  selected.value === optId
    ? "border-green-500 bg-green-50 dark:bg-green-900/30"
    : "border-gray-200 dark:border-gray-700 hover:border-green-400";
</script>