<template>
  <div v-if="loading" class="text-gray-500 text-center py-12">Menyiapkan kuis...</div>

  <div v-else-if="error" class="text-center py-12">
    <Icon name="material-symbols:error" class="w-12 h-12 text-red-400 mx-auto mb-3" />
    <p class="text-gray-700 dark:text-gray-300">{{ error }}</p>
    <NuxtLink
      to="/student/quizzes"
      class="inline-block mt-4 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg"
    >
      Kembali ke Daftar Kuis
    </NuxtLink>
  </div>

  <div v-else-if="attempt" class="max-w-5xl mx-auto">
    <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-4 sticky top-0 z-10">
      <div class="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 class="font-semibold truncate">{{ attempt.title }}</h3>
          <p class="text-xs text-gray-500">Percobaan {{ attempt.attempt_number }}</p>
        </div>
        <div class="flex items-center gap-2">
          <QuizTimer :seconds="remaining" @timeout="autoSubmit" />
          <button
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            @click="confirmSubmit"
          >
            <Icon name="material-symbols:send" class="w-4 h-4 inline" /> Kumpulkan
          </button>
        </div>
      </div>
      <div class="mt-2 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div class="h-full bg-green-500 transition-all" :style="{ width: progressPct + '%' }"></div>
      </div>
    </div>

    <div class="mt-4 grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-5">
      <div>
        <QuizQuestionView
          v-for="(q, i) in attempt.questions"
          :key="q.question_id"
          v-show="i === currentIndex"
          :question="q"
          :index="i"
          :model-value="answers[q.question_id] ?? null"
          @update:model-value="onSelect(q, $event)"
        />
        <QuizQuestionView
          v-if="!attempt.questions.length"
          class="text-center py-10 text-gray-500"
          >
        </QuizQuestionView>

        <div v-if="!attempt.questions.length" class="bg-white dark:bg-gray-900 border rounded-xl p-10 text-center text-gray-500">
          Kuis ini belum memiliki soal.
        </div>

        <div class="flex items-center justify-between gap-2 mt-4">
          <button
            class="flex-1 sm:flex-none border border-gray-300 dark:border-gray-600 px-4 py-2.5 rounded-lg text-sm disabled:opacity-30 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
            :disabled="currentIndex === 0"
            @click="currentIndex--"
          >
            <Icon name="material-symbols:arrow-back" class="w-4 h-4 inline" /> Sebelumnya
          </button>
          <span class="text-sm text-gray-500 text-center whitespace-nowrap">
            {{ currentIndex + 1 }} / {{ attempt.questions.length }}
          </span>
          <button
            class="flex-1 sm:flex-none bg-green-600 hover:bg-green-700 text-white px-4 py-2.5 rounded-lg text-sm transition"
            :disabled="currentIndex === attempt.questions.length - 1"
            @click="currentIndex++"
          >
            Berikutnya <Icon name="material-symbols:arrow-forward" class="w-4 h-4 inline" />
          </button>
        </div>
      </div>

      <aside class="space-y-4">
        <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-sm p-4">
          <p class="text-sm font-medium mb-3">Navigasi Soal</p>
          <QuizNavigation
            :questions="attempt.questions"
            :answers="answers"
            :current-index="currentIndex"
            @select="(i) => (currentIndex = i)"
          />
        </div>
        <button
          v-if="unansweredCount > 0"
          class="w-full bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400 text-sm px-4 py-2 rounded-lg"
        >
          {{ unansweredCount }} soal belum dijawab
        </button>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const props = defineProps({
  quizId: { type: Number, required: true },
});
const emit = defineEmits(["submitted"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const attempt = ref(null);
const answers = ref({});
const loading = ref(true);
const error = ref("");
const currentIndex = ref(0);
const remaining = ref(null);

const progressPct = computed(() => {
  if (!attempt.value?.questions?.length) return 0;
  const n = attempt.value.questions.length;
  return Math.round(((currentIndex.value + 1) / n) * 100);
});

const answeredCount = computed(() => Object.keys(answers.value).filter((k) => answers.value[k] != null).length);
const unansweredCount = computed(() =>
  attempt.value ? attempt.value.questions.length - answeredCount.value : 0
);

const start = async () => {
  loading.value = true;
  try {
    const payload = await $fetch(`${config.public.backend}/api/student/quizzes/${props.quizId}/start`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    attempt.value = payload;
    answers.value = { ...(payload.answers || {}) };
    remaining.value = payload.remaining_seconds;
    currentIndex.value = 0;
  } catch (e) {
    error.value = e?.data?.error || "Tidak dapat memulai kuis";
  } finally {
    loading.value = false;
  }
};

const onSelect = (q, optId) => {
  answers.value[q.question_id] = optId;
  saveAnswer(q.question_id, optId);
};

let savePromise = null;
const saveAnswer = async (questionId, optId) => {
  try {
    await $fetch(`${config.public.backend}/api/student/attempts/${attempt.value.attempt_id}/answer`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: questionId, selected_option_id: optId }),
    });
  } catch (e) {
    if (e?.data?.result) {
      emit("submitted", e.data.result);
    } else {
      toast.add({ title: e?.data?.error || "Gagal menyimpan jawaban", color: "red" });
    }
  }
};

const submit = async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/student/attempts/${attempt.value.attempt_id}/submit`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    emit("submitted", res.result);
  } catch (e) {
    if (e?.data?.result) emit("submitted", e.data.result);
    else toast.add({ title: e?.data?.error || "Gagal mengumpulkan kuis", color: "red" });
  }
};

const confirmSubmit = async () => {
  const result = await swal.fire({
    title: "Kumpulkan kuis?",
    text: unansweredCount.value > 0
      ? `${unansweredCount.value} soal belum dijawab. Yakin ingin mengumpulkan?`
      : "Anda tidak bisa mengubah jawaban setelah dikumpulkan.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Kumpulkan",
    cancelButtonText: "Batal",
  });
  if (result.isConfirmed) submit();
};

const autoSubmit = () => {
  swal.fire({
    title: "Waktu habis!",
    text: "Kuis dikumpulkan otomatis.",
    icon: "info",
  });
  submit();
};

start();
</script>