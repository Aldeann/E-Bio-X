<template>
  <div class="p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <h2 class="text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
      <Icon name="fluent:quiz-new-24-filled" class="text-green-500" /> Buat Kuis Baru
    </h2>

    <div class="my-4">
      <input v-model="quiz.title" type="text" placeholder="Judul Kuis" class="w-full dark:bg-gray-600 p-2 border rounded-lg border-gray-300 focus:outline-green-500" />
    </div>

    <div v-for="(q, qi) in quiz.questions" :key="qi" class="mb-6 border border-green-500 p-3 rounded">
      <div class="flex justify-between items-center">
        <label class="font-semibold mb-2 text-green-500">Pertanyaan {{ qi + 1 }}</label>
        <button @click="hapusPertanyaan(qi)" class="text-red-500">
          <Icon name="material-symbols:delete-rounded" />
        </button>
      </div>

      <input
        v-model="q.question_text"
        type="text"
        class="w-full dark:bg-gray-600 p-2 border rounded-lg border-gray-300 focus:outline-green-500"
        placeholder="Tulis pertanyaan..." />

      <div v-for="(o, oi) in q.options" :key="oi" class="flex items-center space-x-2 my-1">
        <input
          v-model="o.option_text"
          type="text"
          class="w-full dark:bg-gray-600 p-2 border rounded-lg border-gray-300 focus:outline-green-500 flex-1"
          placeholder="Opsi jawaban..." />
        <label class="flex items-center space-x-1">
          <input type="checkbox" v-model="o.is_correct" />
          <span>Benar</span>
        </label>
        <button @click="hapusOpsi(qi, oi)" class="text-red-400">
          <Icon name="material-symbols:backspace" />
        </button>
      </div>

      <button @click="tambahOpsi(qi)" class="text-green-500 text-sm mt-1 hover:text-green-400">+ Tambah Opsi</button>
    </div>

    <button @click="tambahPertanyaan" class="text-green-500 text-sm mb-4 hover:text-green-400">
      + Tambah Pertanyaan
    </button>

    <div>
      <button @click="buatKuis" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-500">
        Simpan Kuis
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const token = useCookie("access_token").value;
const toast = useToast();

const props = defineProps({
  courseId: {
    type: Number,
    required: true,
  },
});

const quiz = ref({
  course_id: props.courseId,
  title: "",
  questions: [],
});

const tambahPertanyaan = () => {
  quiz.value.questions.push({
    question_text: "",
    options: [],
  });
};

const hapusPertanyaan = (index) => {
  quiz.value.questions.splice(index, 1);
};

const tambahOpsi = (qi) => {
  quiz.value.questions[qi].options.push({
    option_text: "",
    is_correct: false,
  });
};

const hapusOpsi = (qi, oi) => {
  quiz.value.questions[qi].options.splice(oi, 1);
};

const buatKuis = async () => {
  try {
    await $fetch(`${useRuntimeConfig().public.backend}/api/quiz`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: quiz.value,
    });

    toast.add({title: 'Kuis berhasil dibuat.', color: 'green'});
    
    quiz.value = { course_id: null, title: "", questions: [] };
  } catch (err) {
    toast.add({title: 'Gagal membuat kuis.', color: 'red'})
  }
};
</script>
