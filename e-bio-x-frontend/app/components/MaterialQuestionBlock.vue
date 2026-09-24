<script setup>
import { ref, computed } from "vue";

// Blok soal interaktif dengan variasi tipe:
// - multiple_choice : pilihan ganda (opsi: options, kunci: correct_answer → index)
// - true_false      : benar/salah (options: ["Benar","Salah"], kunci: correct_answer → 0|1)
// - multi_select    : pilihan ganda multi-jawaban (kunci: correct_answer → [index...])
// - short_answer    : isian singkat (kunci: correct_answer → [teks diterima...])
// - matching        : menjodohkan (left/right, kunci: answer → [index kanan per kiri...])
const props = defineProps({
  qdata: { type: Object, default: null }, // objek soal lengkap
  interactive: { type: Boolean, default: false },
  externalResult: { type: Object, default: null }, // { correct, explanation, expected } dari backend
});

const emit = defineEmits(["submit", "answered"]);

const QTYPES = ["multiple_choice", "true_false", "multi_select", "short_answer", "matching"];

const q = computed(() => props.qdata || {});
const qtype = computed(() =>
  QTYPES.includes(q.value.qtype) ? q.value.qtype : "multiple_choice"
);
const options = computed(() => q.value.options || []);
const leftItems = computed(() => q.value.left || []);
const rightItems = computed(() => q.value.right || []);
const explanation = computed(() =>
  props.externalResult ? props.externalResult.explanation : (q.value.explanation || "")
);

const letter = (i) => String.fromCharCode(65 + i);

// ---- state jawaban ----
const selected = ref(null);   // multiple_choice / true_false
const multiSel = ref([]);     // multi_select
const shortText = ref("");    // short_answer
const matchSel = ref([]);     // matching: index kanan per item kiri
const checked = ref(false);

const isLocalGraded = computed(() => {
  if (props.externalResult) return false;
  const v = q.value.correct_answer;
  if (qtype.value === "matching") return Array.isArray(q.value.answer);
  if (qtype.value === "short_answer")
    return v !== undefined && v !== null && v !== "";
  return v !== undefined && v !== null && v !== "";
});

const feedbackShown = computed(
  () => (isLocalGraded.value && checked.value) || !!props.externalResult
);

const isCorrect = computed(() => {
  if (props.externalResult) return !!props.externalResult.correct;
  if (!isLocalGraded.value || !checked.value) return false;
  switch (qtype.value) {
    case "multi_select": {
      const key = (q.value.correct_answer || []).map(Number).sort((a, b) => a - b);
      const pick = multiSel.value.slice().sort((a, b) => a - b);
      return key.length > 0 && JSON.stringify(key) === JSON.stringify(pick);
    }
    case "short_answer": {
      const norm = (s) =>
        (s || "").toString().trim().toLowerCase().replace(/\s+/g, " ");
      const acc = Array.isArray(q.value.correct_answer)
        ? q.value.correct_answer
        : [q.value.correct_answer];
      return acc.some((a) => norm(a) === norm(shortText.value));
    }
    case "matching": {
      const ans = (q.value.answer || []).map(Number);
      return (
        ans.length > 0 &&
        matchSel.value.length === ans.length &&
        matchSel.value.every((v, i) => v === ans[i])
      );
    }
    default:
      return selected.value === Number(q.value.correct_answer);
  }
});

const correctDisplay = computed(() => {
  if (props.externalResult?.expected) return `Jawaban yang benar: ${props.externalResult.expected}`;
  if (!isLocalGraded.value) return "";
  switch (qtype.value) {
    case "multi_select": {
      const list = (q.value.correct_answer || []).map(Number);
      return "Jawaban yang benar: " + list.map((i) => letter(i)).join(", ");
    }
    case "short_answer": {
      const acc = Array.isArray(q.value.correct_answer)
        ? q.value.correct_answer
        : [q.value.correct_answer];
      return "Jawaban yang benar: " + acc.join(" / ");
    }
    case "matching": {
      const ans = (q.value.answer || []).map(Number);
      const right = rightItems.value;
      return (
        "Pasangan benar: " +
        ans.map((ri, i) => `${letter(i)} → ${right[ri] ?? "?"}`).join(" · ")
      );
    }
    default:
      return `Jawaban yang benar: ${letter(Number(q.value.correct_answer))}`;
  }
});

const canSubmit = computed(() => {
  switch (qtype.value) {
    case "short_answer":
      return shortText.value.trim() !== "";
    case "matching":
      return (
        matchSel.value.length === leftItems.value.length &&
        matchSel.value.every((v) => v !== undefined && v !== null && v !== "")
      );
    case "multi_select":
      return multiSel.value.length > 0;
    default:
      return selected.value !== null;
  }
});

// ---- interaksi ----
const selectOption = (i) => {
  if (!props.interactive || feedbackShown.value) return;
  selected.value = i;
  checked.value = false;
};

const toggleMulti = (i) => {
  if (!props.interactive || feedbackShown.value) return;
  const idx = multiSel.value.indexOf(i);
  if (idx >= 0) multiSel.value.splice(idx, 1);
  else multiSel.value.push(i);
  checked.value = false;
};

const setMatch = (i, v) => {
  if (!props.interactive || feedbackShown.value) return;
  matchSel.value[i] = Number(v);
  checked.value = false;
};

const rawAnswer = () => {
  switch (qtype.value) {
    case "short_answer":
      return shortText.value.trim();
    case "multi_select":
      return multiSel.value.slice();
    case "matching":
      return matchSel.value.slice();
    default:
      return selected.value;
  }
};

const checkAnswer = () => {
  if (!props.interactive || feedbackShown.value || !isLocalGraded.value || !canSubmit.value)
    return;
  checked.value = true;
  emit("answered", { selected: rawAnswer(), is_correct: isCorrect.value, qtype: qtype.value });
};

const submitToServer = () => {
  if (!props.interactive || feedbackShown.value || isLocalGraded.value || !canSubmit.value) return;
  emit("submit", rawAnswer());
};

const reset = () => {
  selected.value = null;
  multiSel.value = [];
  shortText.value = "";
  matchSel.value = [];
  checked.value = false;
};

// ---- gaya visual ----
const rowBase = "w-full text-left flex items-center gap-3 px-4 py-3 rounded-lg border transition text-sm md:text-base";
const optionClass = (i) => {
  const isPicked = qtype.value === "multi_select" ? multiSel.value.includes(i) : selected.value === i;
  if (!props.interactive) {
    return `${rowBase} bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700`;
  }
  if (feedbackShown.value) {
    if (isPicked && isCorrect.value) {
      return `${rowBase} bg-green-50 dark:bg-green-900/40 border-green-400 text-green-800 dark:text-green-200`;
    }
    if (isPicked) {
      return `${rowBase} bg-red-50 dark:bg-red-900/40 border-red-400 text-red-700 dark:text-red-200`;
    }
    return `${rowBase} bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 opacity-60`;
  }
  return `${rowBase} bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 hover:border-green-400 cursor-pointer`;
};

const badgeClass = (i) => {
  const isPicked = qtype.value === "multi_select" ? multiSel.value.includes(i) : selected.value === i;
  if (feedbackShown.value && isPicked && isCorrect.value)
    return "bg-green-500 text-white";
  if (feedbackShown.value && isPicked) return "bg-red-500 text-white";
  if (isPicked) return "bg-green-600 text-white";
  return "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300";
};
</script>

<template>
  <div class="space-y-2">
    <!-- Pilihan ganda / benar-salah / multi-pilih -->
    <template v-if="qtype === 'multiple_choice' || qtype === 'true_false' || qtype === 'multi_select'">
      <button
        v-for="(opt, i) in options"
        :key="i"
        :class="optionClass(i)"
        @click="qtype === 'multi_select' ? toggleMulti(i) : selectOption(i)"
      >
        <span
          class="w-7 h-7 shrink-0 rounded-full flex items-center justify-center text-sm font-semibold"
          :class="badgeClass(i)"
        >
          <Icon
            v-if="qtype === 'multi_select' && feedbackShown"
            :name="multiSel.includes(i) && isCorrect ? 'material-symbols:check' : multiSel.includes(i) ? 'material-symbols:close' : ''"
            class="w-4 h-4"
          />
          <Icon
            v-else-if="feedbackShown && (qtype === 'multiple_choice' || qtype === 'true_false') && i === selected"
            :name="isCorrect ? 'material-symbols:check' : 'material-symbols:close'"
            class="w-4 h-4"
          />
          <template v-else>{{ letter(i) }}</template>
        </span>
        <span>{{ opt }}</span>
      </button>
      <p
        v-if="qtype === 'multi_select' && interactive && !feedbackShown"
        class="text-xs text-gray-400"
      >
        Boleh memilih lebih dari satu jawaban.
      </p>
    </template>

    <!-- Isian singkat -->
    <div v-else-if="qtype === 'short_answer'" class="space-y-2">
      <input
        v-model="shortText"
        type="text"
        :disabled="!interactive || feedbackShown"
        :class="
          'w-full p-2 border rounded bg-white dark:bg-gray-900 text-sm focus:outline-green-500 ' +
          (feedbackShown && !isCorrect
            ? 'border-red-400'
            : 'border-gray-300 dark:border-gray-700')
        "
        placeholder="Ketik jawaban singkat..."
        @input="checked = false"
      />
      <p v-if="isLocalGraded && !feedbackShown && interactive" class="text-xs text-gray-400">
        Jawaban dicocokkan otomatis (tidak membedakan huruf besar/kecil).
      </p>
    </div>

    <!-- Menjodohkan -->
    <div v-else-if="qtype === 'matching'" class="space-y-2">
      <div
        v-for="(l, i) in leftItems"
        :key="i"
        class="flex items-center gap-2 text-sm"
      >
        <span class="w-6 h-6 shrink-0 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 flex items-center justify-center font-semibold">
          {{ letter(i) }}
        </span>
        <span class="flex-1 text-gray-700 dark:text-gray-200">{{ l }}</span>
        <select
          :value="matchSel[i] ?? ''"
          :disabled="!interactive || feedbackShown"
          class="p-1.5 text-sm border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 focus:outline-green-500"
          @change="(e) => setMatch(i, e.target.value)"
        >
          <option value="" disabled>Pilih...</option>
          <option v-for="(r, ri) in rightItems" :key="ri" :value="ri">
            {{ letter(ri) }}. {{ r }}
          </option>
        </select>
      </div>
      <p v-if="!interactive && isLocalGraded && rightItems.length" class="text-xs text-gray-400">
        Kiri dihubungkan ke kanan sesuai kunci.
      </p>
    </div>

    <!-- server-graded: submit -->
    <div
      v-if="interactive && !isLocalGraded && canSubmit && !feedbackShown"
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

    <!-- locally-graded: check -->
    <div
      v-if="interactive && isLocalGraded && canSubmit && !checked"
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

    <!-- feedback -->
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
        <span v-if="!isCorrect && correctDisplay" class="font-normal">
          {{ correctDisplay }}
        </span>
      </p>
      <p v-if="explanation" class="mt-1">{{ explanation }}</p>
    </div>
  </div>
</template>