<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  question: { type: String, default: "" },
  options: { type: Array, default: () => [] },
  correctAnswer: { type: [Number, null], default: null },
  explanation: { type: String, default: "" },
  interactive: { type: Boolean, default: false },
  externalResult: { type: Object, default: null }, // { correct, explanation } from backend grading
});

const emit = defineEmits(["submit", "answered"]);

const selected = ref(null);
const checked = ref(false);

const letter = (i) => String.fromCharCode(65 + i);

const isLocalGraded = computed(() => props.correctAnswer !== null);
const isCorrect = computed(() => {
  if (props.externalResult) return !!props.externalResult.correct;
  return isLocalGraded.value && selected.value === props.correctAnswer;
});
const explanation = computed(() =>
  props.externalResult ? props.externalResult.explanation : props.explanation
);
const feedbackShown = computed(
  () => (isLocalGraded.value && checked.value) || !!props.externalResult
);

const selectOption = (i) => {
  if (!props.interactive || feedbackShown.value) return;
  selected.value = i;
  checked.value = false;
};

const checkAnswer = () => {
  if (!props.interactive || selected.value === null || checked.value || !isLocalGraded.value) return;
  checked.value = true;
  emit("answered", { selected: selected.value, is_correct: isCorrect.value });
};

const submitToServer = () => {
  if (!props.interactive || selected.value === null || isLocalGraded.value) return;
  emit("submit", selected.value);
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
  if (feedbackShown.value) {
    if (i === selected.value && isCorrect.value) {
      return `${base} bg-green-50 dark:bg-green-900/40 border-green-400 text-green-800 dark:text-green-200`;
    }
    if (i === selected.value) {
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
          feedbackShown && i === selected && isCorrect
            ? 'bg-green-500 text-white'
            : feedbackShown && i === selected
              ? 'bg-red-500 text-white'
              : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
        "
      >
        {{ letter(i) }}
      </span>
      <span>{{ opt }}</span>
    </button>

    <!-- server-graded: submit button -->
    <div
      v-if="interactive && !isLocalGraded && selected !== null && !feedbackShown"
      class="flex flex-wrap gap-2 mt-2"
    >
      <button
        @click="submitToServer"
        class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-semibold"
      >
        Jawab
      </button>
      <button
        @click="reset"
        class="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 text-gray-700 dark:text-gray-100 px-4 py-2 rounded-lg text-sm font-semibold"
      >
        Ulangi
      </button>
    </div>

    <!-- locally-graded: check button -->
    <div
      v-if="interactive && isLocalGraded && selected !== null && !checked"
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
      v-if="feedbackShown"
      class="mt-3 rounded-lg p-4 text-sm border"
      :class="
        isCorrect
          ? 'bg-green-50 dark:bg-green-900/40 border-green-300 text-green-800 dark:text-green-100'
          : 'bg-red-50 dark:bg-red-900/40 border-red-300 text-red-800 dark:text-red-100'
      "
    >
      <p class="font-semibold flex items-center gap-1">
        <Icon
          :name="isCorrect ? 'material-symbols:check-circle' : 'material-symbols:error'"
          class="w-5 h-5"
        />
        {{ isCorrect ? "Jawaban benar!" : "Jawaban belum tepat." }}
        <span v-if="!isCorrect && isLocalGraded" class="font-normal">
          Jawaban yang benar: {{ letter(correctAnswer) }}
        </span>
      </p>
      <p v-if="explanation" class="mt-1 text-sm">{{ explanation }}</p>
    </div>
  </div>
</template>