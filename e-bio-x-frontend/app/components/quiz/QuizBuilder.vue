<template>
  <div class="space-y-4">
    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat kuis...</div>

    <template v-else-if="quiz">
      <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 class="text-lg font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
              <Icon name="material-symbols:quiz" class="w-5 h-5" />
              {{ quiz.title }}
            </h3>
            <div class="flex flex-wrap gap-2 mt-2 text-xs">
              <span
                class="px-2 py-1 rounded-full"
                :class="statusClass(quiz.status)"
              >{{ statusLabel(quiz.status) }}</span>
              <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                {{ quiz.question_count }} soal
              </span>
              <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                Total {{ quiz.total_points }} poin
              </span>
              <span v-if="quiz.material_title" class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                {{ quiz.material_title }}
              </span>
              <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                Durasi {{ quiz.duration || "-" }} menit
              </span>
              <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                Lulus {{ quiz.passing_grade }}%
              </span>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <NuxtLink
              :to="`/teacher/quizzes/${quiz.id}/preview`"
              class="border border-green-600 text-green-700 dark:text-green-400 px-3 py-2 rounded-lg hover:bg-green-50 dark:hover:bg-gray-800 transition flex items-center gap-1 text-sm"
            >
              <Icon name="material-symbols:visibility" class="w-4 h-4" /> Pratinjau
            </NuxtLink>
            <NuxtLink
              :to="`/teacher/quizzes/${quiz.id}/analytics`"
              class="border border-green-600 text-green-700 dark:text-green-400 px-3 py-2 rounded-lg hover:bg-green-50 dark:hover:bg-gray-800 transition flex items-center gap-1 text-sm"
            >
              <Icon name="material-symbols:monitoring" class="w-4 h-4" /> Analitik
            </NuxtLink>
            <button
              class="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded-lg transition flex items-center gap-1 text-sm"
              @click="publish"
            >
              <Icon name="material-symbols:publish" class="w-4 h-4" /> Publikasikan
            </button>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition flex items-center gap-1"
          @click="openQuestionForm()"
        >
          <Icon name="material-symbols:add" class="w-5 h-5" /> Tambah Soal
        </button>
        <button
          class="border border-green-600 text-green-700 dark:text-green-400 px-4 py-2 rounded-lg hover:bg-green-50 dark:hover:bg-gray-800 transition flex items-center gap-1"
          @click="openBankModal"
        >
          <Icon name="material-symbols:database" class="w-5 h-5" /> Dari Bank Soal
        </button>
      </div>

      <p v-if="quiz.questions.length === 0" class="text-gray-500 dark:text-gray-400 text-sm bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-dashed border-gray-300 dark:border-gray-600">
        Belum ada soal. Tambahkan soal baru atau pilih dari Bank Soal untuk mulai membangun kuis.
      </p>

      <div class="space-y-3">
        <div
          v-for="(q, qi) in sortedQuestions"
          :key="q.question_id"
          class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-sm p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="w-7 h-7 flex items-center justify-center rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400 text-sm font-semibold">
                  {{ qi + 1 }}
                </span>
                <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400">
                  {{ typeLabel(q.question_type) }}
                </span>
                <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400">
                  {{ difficultyLabel(q.difficulty) }}
                </span>
                <span class="text-xs text-gray-500">Bobot {{ q.points }} poin</span>
                <span v-if="q.bank_question_id" class="text-xs text-purple-600 dark:text-purple-400 flex items-center gap-1">
                  <Icon name="material-symbols:database" class="w-3.5 h-3.5" /> dari bank
                </span>
              </div>
              <p class="mt-2 font-medium">{{ q.question_text }}</p>
              <ul class="mt-2 space-y-1 text-sm">
                <li
                  v-for="o in q.options"
                  :key="o.option_id"
                  class="flex items-center gap-1.5"
                  :class="o.is_correct ? 'text-green-600 dark:text-green-400 font-medium' : ''"
                >
                  <Icon
                    :name="o.is_correct ? 'material-symbols:check-circle' : 'material-symbols:radio-button-unchecked'"
                    class="w-4 h-4 shrink-0"
                  />
                  <span>{{ o.option_text }}</span>
                  <span v-if="o.is_correct" class="text-xs text-green-600 dark:text-green-400">(kunci)</span>
                </li>
                <li v-if="q.explanation" class="pt-1 text-gray-500 dark:text-gray-400 italic">
                  Pembahasan: {{ q.explanation }}
                </li>
              </ul>
            </div>
            <div class="flex flex-col gap-1 shrink-0">
              <div class="flex gap-1 justify-end">
                <button
                  class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30"
                  :disabled="qi === 0"
                  title="Naikkan"
                  @click="move(q, -1)"
                >
                  <Icon name="material-symbols:arrow-upward" class="w-5 h-5" />
                </button>
                <button
                  class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30"
                  :disabled="qi === sortedQuestions.length - 1"
                  title="Turunkan"
                  @click="move(q, 1)"
                >
                  <Icon name="material-symbols:arrow-downward" class="w-5 h-5" />
                </button>
              </div>
              <div class="flex gap-1 justify-end">
                <button class="text-blue-500 hover:text-blue-600" title="Edit" @click="openQuestionForm(q)">
                  <Icon name="material-symbols:edit" class="w-5 h-5" />
                </button>
                <button class="text-purple-500 hover:text-purple-600" title="Duplikat" @click="duplicate(q)">
                  <Icon name="material-symbols:content-copy" class="w-5 h-5" />
                </button>
                <button class="text-red-500 hover:text-red-600" title="Hapus" @click="remove(q)">
                  <Icon name="material-symbols:delete" class="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <QuizQuestionForm
      :open="questionModal"
      :quiz-id="quizId"
      :question="editingQuestion"
      :bank-question="bankQuestion"
      @close="questionModal = false; editingQuestion = null; bankQuestion = null"
      @saved="onQuestionSaved"
    />

    <div v-if="bankModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="bankModal = false"></div>
      <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
            <Icon name="material-symbols:database" class="w-5 h-5" /> Bank Soal
          </h3>
          <button class="text-gray-500 hover:text-gray-700" @click="bankModal = false">
            <Icon name="material-symbols:close" class="w-6 h-6" />
          </button>
        </div>
        <div class="mb-3">
          <input
            v-model="bankSearch"
            type="text"
            placeholder="Cari soal bank..."
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div v-if="bankItems.length === 0" class="text-gray-500 text-sm py-6 text-center">
          Bank soal kosong. Tambahkan soal dulu di halaman Bank Soal.
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="b in filteredBank"
            :key="b.id"
            class="border border-green-200 dark:border-gray-700 rounded-lg p-3 flex items-start justify-between gap-3"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium">{{ b.question_text }}</p>
              <p class="text-xs text-gray-500 mt-1">
                {{ typeLabel(b.question_type) }} · {{ difficultyLabel(b.difficulty) }} · {{ b.points }} poin
                <template v-if="b.topic"> · {{ b.topic }}</template>
              </p>
            </div>
            <button
              class="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded text-sm shrink-0"
              @click="addFromBank(b)"
            >
              Gunakan
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const props = defineProps({
  quizId: { type: Number, required: true },
});
const emit = defineEmits(["updated"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const quiz = ref(null);
const loading = ref(true);
const questionModal = ref(false);
const editingQuestion = ref(null);
const bankQuestion = ref(null);
const bankModal = ref(false);
const bankItems = ref([]);
const bankSearch = ref("");

const sortedQuestions = computed(() =>
  [...(quiz.value?.questions || [])].sort((a, b) => a.order_index - b.order_index)
);

const filteredBank = computed(() => {
  const q = bankSearch.value.toLowerCase();
  if (!q) return bankItems.value;
  return bankItems.value.filter((b) => (b.question_text || "").toLowerCase().includes(q));
});

const load = async () => {
  loading.value = true;
  try {
    quiz.value = await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.quizId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat kuis", color: "red" });
  } finally {
    loading.value = false;
  }
};

const statusLabel = (s) => (s === "published" ? "Published" : s === "archived" ? "Archived" : "Draft");
const statusClass = (s) =>
  s === "published"
    ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400"
    : s === "archived"
    ? "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
    : "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400";
const typeLabel = (t) => (t === "true_false" ? "Benar/Salah" : "Pilihan Ganda");
const difficultyLabel = (d) =>
  d === "easy" ? "Mudah" : d === "hard" ? "Sulit" : "Sedang";

const openQuestionForm = (q = null) => {
  editingQuestion.value = q;
  bankQuestion.value = null;
  questionModal.value = true;
};

const onQuestionSaved = async () => {
  questionModal.value = false;
  editingQuestion.value = null;
  bankQuestion.value = null;
  await load();
  emit("updated", quiz.value);
};

const duplicate = async (q) => {
  try {
    await $fetch(`${config.public.backend}/api/questions/${q.question_id}/duplicate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    });
    toast.add({ title: "Soal diduplikasi", color: "green" });
    await load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal menduplikasi soal", color: "red" });
  }
};

const remove = async (q) => {
  const result = await swal.fire({
    title: "Hapus soal ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/questions/${q.question_id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Soal dihapus", color: "green" });
    await load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal menghapus soal", color: "red" });
  }
};

const move = async (q, dir) => {
  const list = sortedQuestions.value;
  const idx = list.findIndex((x) => x.question_id === q.question_id);
  const swapIdx = idx + dir;
  if (swapIdx < 0 || swapIdx >= list.length) return;
  const arr = [...list];
  [arr[idx], arr[swapIdx]] = [arr[swapIdx], arr[idx]];
  await reorder(arr);
};

const reorder = async (arr) => {
  try {
    await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.quizId}/questions/reorder`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ question_ids: arr.map((x) => x.question_id) }),
    });
    await load();
  } catch (e) {
    toast.add({ title: "Gagal mengubah urutan", color: "red" });
  }
};

const openBankModal = async () => {
  bankSearch.value = "";
  bankModal.value = true;
  await loadBank();
};

const loadBank = async () => {
  try {
    const data = await $fetch(`${config.public.backend}/api/teacher/question-bank`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    bankItems.value = data?.data || [];
  } catch (e) {
    toast.add({ title: "Gagal memuat bank soal", color: "red" });
  }
};

const addFromBank = (b) => {
  bankModal.value = false;
  bankQuestion.value = b;
  questionModal.value = true;
};

const publish = async () => {
  const result = await swal.fire({
    title: "Publikasikan kuis ini?",
    text: "Kuis akan langsung tersedia bagi siswa yang terdaftar di kelas materi tersebut.",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Publikasikan",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    const res = await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.quizId}/publish`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ status: "published" }),
    });
    toast.add({ title: "Kuis dipublikasikan", color: "green" });
    await load();
    emit("updated", quiz.value);
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal mempublikasikan kuis", color: "red" });
  }
};

load();
</script>