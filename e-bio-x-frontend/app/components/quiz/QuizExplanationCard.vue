<template>
  <div
    class="bg-white dark:bg-gray-900 border rounded-xl shadow-sm p-5"
    :class="isCorrect ? 'border-green-300 dark:border-green-700' : 'border-red-300 dark:border-red-700'"
  >
    <div class="flex items-center gap-2 flex-wrap">
      <span
        class="w-7 h-7 flex items-center justify-center rounded-full text-white text-sm font-semibold shrink-0"
        :class="isCorrect ? 'bg-green-500' : 'bg-red-500'"
      >
        <Icon :name="isCorrect ? 'material-symbols:check' : 'material-symbols:close'" class="w-4 h-4" />
      </span>
      <span class="font-semibold">Soal {{ index + 1 }}</span>
      <span class="text-xs text-gray-500 ml-auto">
        Jawaban Anda: {{ answer || "—" }}
      </span>
      <span
        class="text-xs font-medium px-2 py-0.5 rounded-full"
        :class="status === 'TEACHER_APPROVED' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'"
      >
        {{ statusLabel }}
      </span>
    </div>

    <div v-if="explanation" class="mt-4 space-y-4">
      <div v-if="explanation.summary" class="text-sm text-gray-700 dark:text-gray-300">
        {{ explanation.summary }}
      </div>

      <div
        v-if="explanation.option_explanations?.length"
        class="space-y-2 text-sm"
      >
        <div
          v-for="o in explanation.option_explanations"
          :key="o.option"
          class="flex items-start gap-2 p-2.5 rounded-lg border"
          :class="o.is_correct
            ? 'border-green-400 bg-green-50 dark:bg-green-900/30'
            : 'border-gray-200 dark:border-gray-700'"
        >
          <span
            class="w-5 h-5 shrink-0 flex items-center justify-center rounded-full border-2 text-white text-xs"
            :class="o.is_correct ? 'bg-green-600 border-green-600' : 'border-gray-300 dark:border-gray-600'"
          >
            {{ o.option }}
          </span>
          <span>
            {{ optionText(o.option) }}
            <span v-if="o.is_correct" class="text-green-600 dark:text-green-400 font-medium">(kunci jawaban)</span>
            <span class="block mt-0.5 text-gray-500 dark:text-gray-400">{{ o.explanation }}</span>
          </span>
        </div>
      </div>

      <div
        v-if="explanation.correct_answer_explanation"
        class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-sm text-blue-800 dark:text-blue-300"
      >
        <span class="font-semibold">Pembahasan: </span>{{ explanation.correct_answer_explanation }}
      </div>

      <div
        v-if="personal?.analysis"
        class="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/30 text-sm text-amber-800 dark:text-amber-300"
      >
        <span class="font-semibold">Analisis jawaban Anda: </span>{{ personal.analysis }}
      </div>

      <div
        v-if="explanation.key_concept"
        class="text-sm text-gray-700 dark:text-gray-300"
      >
        <span class="font-semibold">Konsep kunci: </span>{{ explanation.key_concept }}
      </div>

      <div
        v-if="explanation.misconception"
        class="text-sm text-orange-700 dark:text-orange-300"
      >
        <span class="font-semibold">Kesalahan umum: </span>{{ explanation.misconception }}
      </div>

      <div class="flex flex-wrap items-center gap-2 pt-2 border-t border-gray-100 dark:border-gray-800">
        <button
          v-if="explanation.recommended_material_id"
          class="inline-flex items-center gap-1 text-sm text-green-600 hover:text-green-700 font-medium"
          @click="openRecommended"
        >
          <Icon name="material-symbols:menu-book" class="w-4 h-4" />
          Buka Materi Rekomendasi
        </button>

        <span v-if="feedback?.helpful" class="ml-auto text-xs text-green-600">
          {{ feedback.helpful }} orang merasa terbantu
        </span>
        <span v-if="feedback?.not_helpful" class="text-xs text-red-500">
          · {{ feedback.not_helpful }} tidak terbantu
        </span>

        <div class="flex items-center gap-1 ml-auto" v-if="!feedback?.helpful && !feedback?.not_helpful">
          <button
            class="text-xs px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-green-50 dark:hover:bg-green-900/30 transition"
            :disabled="submittingFeedback"
            @click="sendFeedback('helpful')"
          >
            👍 Membantu
          </button>
          <button
            class="text-xs px-2 py-1 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-red-50 dark:hover:bg-red-900/30 transition"
            :disabled="submittingFeedback"
            @click="sendFeedback('not_helpful')"
          >
            👎 Kurang membantu
          </button>
        </div>
      </div>
    </div>

    <div v-else class="mt-3 text-sm text-gray-500">
      <template v-if="status === 'MISSING'">
        Pembahasan belum tersedia untuk soal ini.
      </template>
      <template v-else-if="status === 'NOT_AVAILABLE'">
        Pembahasan sedang menunggu persetujuan guru.
      </template>
      <template v-else>
        Pembahasan belum dapat ditampilkan.
      </template>
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const props = defineProps({
  explanation: { type: Object, default: null },
  personal: { type: Object, default: null },
  answer: { type: String, default: "" },
  isCorrect: { type: Boolean, default: false },
  status: { type: String, default: "" },
  index: { type: Number, default: 0 },
  questionOptions: { type: Array, default: () => [] },
});

const feedback = computed(() => props.explanation?.feedback_summary || null);
const submittingFeedback = ref(false);

const statusLabel = computed(() => {
  if (props.status === "TEACHER_APPROVED") return "Pembahasan Guru";
  if (props.status === "APPROVED") return "Pembahasan AI";
  return props.status || "";
});

const optionText = (letter) => {
  const opt = props.questionOptions.find((o) => o.option === letter);
  return opt ? opt.text : "";
};

const sendFeedback = async (rating) => {
  submittingFeedback.value = true;
  try {
    await $fetch(`${config.public.backend}/api/quiz/explanations/${props.explanation.id}/feedback`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ rating }),
    });
    toast.add({ title: "Terima kasih atas umpan balik Anda!", color: "green" });
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal mengirim umpan balik", color: "red" });
  } finally {
    submittingFeedback.value = false;
  }
};

const openRecommended = async () => {
  const id = props.explanation.recommended_material_id;
  try {
    await $fetch(`${config.public.backend}/api/quiz/explanations/${props.explanation.id}/material-click`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
  } catch (e) {
    // ignore tracking errors
  }
  navigateTo(`/student/materials/${id}`);
};
</script>