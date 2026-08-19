<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/50" @click="close"></div>
    <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
          <Icon name="material-symbols:quiz" class="w-5 h-5" />
          {{ isEdit ? "Edit Soal" : "Tambah Soal" }}
        </h3>
        <button class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" @click="close">
          <Icon name="material-symbols:close" class="w-6 h-6" />
        </button>
      </div>

      <form @submit.prevent="save" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Tipe Soal</label>
            <select
              v-model="form.question_type"
              class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500"
              :disabled="form.question_type === 'true_false' && isEdit"
              @change="onTypeChange"
            >
              <option value="multiple_choice">Pilihan Ganda</option>
              <option value="true_false">Benar / Salah</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Kesulitan</label>
            <select
              v-model="form.difficulty"
              class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500"
            >
              <option value="easy">Mudah</option>
              <option value="medium">Sedang</option>
              <option value="hard">Sulit</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Bobot Poin *</label>
            <input
              v-model.number="form.points"
              type="number"
              min="0"
              class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500"
              required
            />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">Pertanyaan *</label>
          <textarea
            v-model="form.question_text"
            rows="2"
            placeholder="Tulis pertanyaan..."
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500"
            required
          ></textarea>
        </div>

        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="block text-sm font-medium">Pilihan Jawaban *</label>
            <button
              v-if="form.question_type === 'multiple_choice'"
              type="button"
              class="text-sm text-green-600 hover:text-green-700 flex items-center gap-1"
              @click="addOption"
            >
              <Icon name="material-symbols:add-circle" class="w-4 h-4" /> Tambah Pilihan
            </button>
          </div>

          <div v-for="(o, i) in form.options" :key="i" class="flex items-center gap-2 mb-2">
            <button
              type="button"
              class="w-6 h-6 shrink-0 flex items-center justify-center rounded-full border-2 transition"
              :class="o.is_correct
                ? 'bg-green-600 border-green-600 text-white'
                : 'border-gray-300 text-transparent hover:border-green-400'"
              :title="o.is_correct ? 'Jawaban benar' : 'Tandai sebagai benar'"
              @click="toggleCorrect(i)"
            >
              <Icon name="material-symbols:check" class="w-4 h-4" />
            </button>
            <input
              v-model="o.option_text"
              type="text"
              placeholder="Pilihan jawaban..."
              class="flex-1 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500"
            />
            <span v-if="o.is_correct" class="text-xs text-green-600 dark:text-green-400 w-16 text-center">Benar</span>
            <button
              v-if="form.options.length > 2"
              type="button"
              class="text-red-500 hover:text-red-600"
              @click="form.options.splice(i, 1)"
            >
              <Icon name="material-symbols:delete" class="w-5 h-5" />
            </button>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">Pembahasan (opsional)</label>
          <textarea
            v-model="form.explanation"
            rows="2"
            placeholder="Penjelasan jawaban yang benar..."
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:ring-2 focus:ring-green-500"
          ></textarea>
        </div>

        <div class="flex gap-2 pt-2">
          <button
            type="submit"
            class="bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg transition flex items-center gap-1"
          >
            <Icon name="material-symbols:save" class="w-5 h-5" />
            {{ isEdit ? "Simpan Perubahan" : "Tambahkan Soal" }}
          </button>
          <button
            type="button"
            class="border border-gray-300 dark:border-gray-600 px-5 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
            @click="close"
          >
            Batal
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  open: { type: Boolean, default: false },
  quizId: { type: Number, default: null },
  question: { type: Object, default: null },
  bankQuestion: { type: Object, default: null },
});
const emit = defineEmits(["close", "saved"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const form = ref(defaultForm());

function defaultForm() {
  return {
    question_type: "multiple_choice",
    question_text: "",
    difficulty: "medium",
    explanation: "",
    points: 10,
    options: [
      { option_text: "", is_correct: false },
      { option_text: "", is_correct: false },
      { option_text: "", is_correct: false },
    ],
  };
}

const isEdit = computed(() => !!props.question);

const onTypeChange = () => {
  if (form.value.question_type === "true_false") {
    form.value.options = [
      { option_text: "Benar", is_correct: false },
      { option_text: "Salah", is_correct: false },
    ];
  } else if (form.value.options.length < 2) {
    form.value.options = [
      { option_text: "", is_correct: false },
      { option_text: "", is_correct: false },
    ];
  }
};

const addOption = () => {
  form.value.options.push({ option_text: "", is_correct: false });
};

const toggleCorrect = (i) => {
  if (form.value.options[i].is_correct) {
    form.value.options[i].is_correct = false;
    return;
  }
  form.value.options = form.value.options.map((o, idx) => ({ ...o, is_correct: idx === i }));
};

const fillFrom = (q) => {
  form.value.question_type = q.question_type || "multiple_choice";
  form.value.question_text = q.question_text || "";
  form.value.difficulty = q.difficulty || "medium";
  form.value.explanation = q.explanation || "";
  form.value.points = q.points || 10;
  if (q.question_type === "true_false") {
    form.value.options = [
      { option_text: "Benar", is_correct: false },
      { option_text: "Salah", is_correct: false },
    ];
  } else {
    form.value.options = (q.options || []).map((o) => ({
      option_text: o.option_text,
      is_correct: !!o.is_correct,
    }));
  }
  if (form.value.options.length === 0) {
    form.value.options = [
      { option_text: "", is_correct: false },
      { option_text: "", is_correct: false },
    ];
  }
};

const close = () => {
  emit("close");
};

const save = async () => {
  if (!form.value.question_text.trim()) {
    toast.add({ title: "Pertanyaan wajib diisi", color: "red" });
    return;
  }
  const options = form.value.options.map((o) => ({
    option_text: o.option_text,
    is_correct: o.is_correct,
  }));
  if (options.some((o) => !o.option_text.trim())) {
    toast.add({ title: "Semua pilihan jawaban wajib diisi", color: "red" });
    return;
  }
  const correctCount = options.filter((o) => o.is_correct).length;
  if (correctCount !== 1) {
    toast.add({ title: "Tandai tepat 1 jawaban benar", color: "red" });
    return;
  }
  if (form.value.question_type === "multiple_choice" && options.length < 2) {
    toast.add({ title: "Pilihan ganda minimal 2 pilihan", color: "red" });
    return;
  }

  const body = {
    question_type: form.value.question_type,
    question_text: form.value.question_text,
    difficulty: form.value.difficulty,
    explanation: form.value.explanation,
    points: Number(form.value.points) || 0,
    options,
  };

  try {
    if (isEdit.value) {
      await $fetch(`${config.public.backend}/api/questions/${props.question.question_id}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } else {
      const bq = props.bankQuestion;
      if (bq) {
        const extra = { ...body, bank_question_id: bq.id };
        await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.quizId}/questions`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify(extra),
        });
      } else {
        await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.quizId}/questions`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      }
    }
    toast.add({ title: "Soal berhasil disimpan", color: "green" });
    emit("saved");
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal menyimpan soal", color: "red" });
  }
};

watch(
  () => props.open,
  (val) => {
    if (val) {
      if (props.question) fillFrom(props.question);
      else if (props.bankQuestion) {
        form.value = defaultForm();
        fillFrom(props.bankQuestion);
      } else {
        form.value = defaultForm();
      }
    }
  }
);
</script>