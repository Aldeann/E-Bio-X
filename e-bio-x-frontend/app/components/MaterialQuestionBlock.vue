<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  question: { type: String, default: "" },
  options: { type: Array, default: () => [] },
  correctAnswer: { type: [Number, null], default: null },
  explanation: { type: String, default: "" },
  interactive: { type: Boolean, default: false },
});

const selected = ref(null);
const checked = ref(false);

const letter = (i) => String.fromCharCode(65 + i);

const isCorrect = computed(
  () => props.correctAnswer !== null && selected.value === props.correctAnswer
);

const selectOption = (i) => {
  if (!props.interactive || checked.value) return;
  selected.value = i;
  checked.value = false;
};

const checkAnswer = () => {
  if (!props.interactive || selected.value === null || checked.value) return;
  checked.value = true;
};

const reset = () => {
  selected.value = null;
  checked.value = false;
};

const optionClass = (i) => {
  const base =
    "w-full text-left flex items-center gap-3 px-4 py-3 rounded-lg border transition text-sm md:text-base";
  if (!props.interactive) {
    return `${base} bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700`;
  }
  if (checked.value) {
    if (i === props.correctAnswer) {
      return `${base} bg-green-50 dark:bg-green-900/40 border-green-400 text-green-800 dark:text-green-200`;
    }
    if (i === selected.value && !isCorrect.value) {
      return `${base} bg-red-50 dark:bg-red-900/40 border-red-400 text-red-700 dark:text-red-200`;
    }
    return `${base} bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 opacity-60`;
  }
  return `${base} bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:border-green-400 cursor-pointer`;
};
</script>

<template>
  <div class="space-y-2">
    <button
      v-for="(opt, i) in options"
      :key="i"
      :class="optionClass(i)"
      @click="selectOption(i)"
    >
      <span
        class="w-7 h-7 shrink-0 rounded-full flex items-center justify-center text-sm font-semibold"
        :class="
          checked.value && i === props.correctAnswer
            ? 'bg-green-500 text-white'
            : checked.value && i === selected.value && !isCorrect
              ? 'bg-red-500 text-white'
              : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
        "
      >
        {{ letter(i) }}
      </span>
      <span>{{ opt }}</span>
    </button>

    <div
      v-if="interactive && selected !== null && !checked && correctAnswer === null"
      class="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-1"
    >
      <Icon name="material-symbols:check-circle-outline" class="w-4 h-4" />
      Jawaban nomor {{ letter(selected) }} dipilih.
    </div>

    <div
      v-if="interactive && selected !== null && !checked && correctAnswer !== null"
      class="flex flex-wrap gap-2 mt-2"
    >
      <button
        @click="checkAnswer"
        class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-semibold"
      >
        Periksa Jawaban
      </button>
      <button
        @click="reset"
        class="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 text-gray-700 dark:text-gray-100 px-4 py-2 rounded-lg text-sm font-semibold"
      >
        Ulangi
      </button>
    </div>

    <div
      v-if="checked && correctAnswer !== null"
      class="mt-3 rounded-lg p-4 text-sm border"
      :class="
        isCorrect
          ? 'bg-green-50 dark:bg-green-900/40 border-green-300 text-green-800 dark:text-green-100'
          : 'bg-red-50 dark:bg-red-900/40 border-red-300 text-red-800 dark:text-red-100'
      "
    >
      <p class="font-semibold flex items-center gap-1">
        <Icon
          :name="
            isCorrect
              ? 'material-symbols:check-circle'
              : 'material-symbols:error'
          "
          class="w-5 h-5"
        />
        {{ isCorrect ? "Benar!" : "Belum tepat." }}
        <span v-if="!isCorrect" class="font-normal">
          Jawaban yang benar: {{ letter(correctAnswer) }}
        </span>
      </p>
      <p v-if="explanation" class="mt-1 text-sm">{{ explanation }}</p>
    </div>
  </div>
</template>