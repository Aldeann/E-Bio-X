<template>
  <div class="p-4">
    <h1 class="text-2xl font-bold mb-4">Edit Quiz</h1>

    <div v-if="quiz">
      <!-- Title -->
      <div class="mb-6">
        <label class="block font-semibold mb-1">Quiz Title</label>
        <div class="flex gap-2">
          <input v-model="quiz.title" type="text" class="border p-2 rounded w-full" />
          <button @click="saveTitle" :disabled="!quiz.titleDirty"
            :class="quiz.titleDirty ? 'bg-blue-500 hover:bg-blue-600' : 'bg-gray-400 cursor-not-allowed'"
            class="text-white px-4 py-2 rounded">
            Save
          </button>
        </div>
      </div>

      <!-- Questions -->
      <div v-for="question in quiz.questions" :key="question.question_id"
        class="mb-6 border p-4 rounded shadow-lg border-green-200">
        <label class="block font-semibold mb-1">Question</label>
        <div class="flex gap-2">
          <input v-model="question.question_text" type="text" class="border p-2 rounded w-full" />
          <button @click="saveQuestion(question)" :disabled="!question.dirty"
            :class="question.dirty ? 'bg-green-500 hover:bg-green-600' : 'bg-gray-400 cursor-not-allowed'"
            class="text-white px-4 py-2 rounded">
            Save
          </button>
        </div>

        <!-- Options -->
        <div v-for="option in question.options" :key="option.option_id" class="mt-4 pl-4 border-l">
          <label class="block mb-1">Option</label>
          <div class="flex gap-2 items-center">
            <input v-model="option.option_text" type="text" class="border p-2 rounded w-full" />

            <input type="radio" :name="'correct-' + question.question_id" :checked="option.is_correct"
              @change="setCorrectOption(question, option)" />

            <button @click="saveOption(option)" :disabled="!option.dirty"
              :class="option.dirty ? 'bg-yellow-500 hover:bg-yellow-600' : 'bg-gray-400 cursor-not-allowed'"
              class="text-white px-3 py-2 rounded">
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-else>
      <p>Loading quiz data...</p>
    </div>
  </div>
</template>

<script setup>
import { useRoute, useRuntimeConfig } from "nuxt/app";
import Cookies from "js-cookie";

const route = useRoute();
const config = useRuntimeConfig();
const quiz = ref(null);
const toast = useToast();

const fetchQuiz = async () => {
  const token = Cookies.get("access_token");
  try {
    const res = await $fetch(`${config.public.backend}/api/quiz/${route.params.id}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    res.titleDirty = false;
    res.questions.forEach((q) => {
      q.dirty = false;
      q.options.forEach((o) => (o.dirty = false));
    });
    quiz.value = res;
  } catch (err) {
    toast.add({ title: 'Gagal mengambil data kuis.', color: 'red' })
  }
};

const saveTitle = async () => {
  const token = Cookies.get("access_token");
  try {
    await $fetch(`${config.public.backend}/api/quiz/${route.params.id}/edit_title`, {
      method: "PATCH",
      body: { title: quiz.value.title },
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    quiz.value.titleDirty = false;
    toast.add({ title: 'Berhasil mengubah nama kuis.', color: 'green' })
  } catch (err) {
    toast.add({ title: 'Gagal mengubah nama kuis.', color: 'red' })
  }
};

const saveQuestion = async (question) => {
  const token = Cookies.get("access_token");
  try {
    await $fetch(`${config.public.backend}/api/quiz/${question.question_id}/edit_question`, {
      method: "PATCH",
      body: { question_text: question.question_text },
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    question.dirty = false;
    toast.add({ title: 'Berhasil mengubah pertanyaan.', color: 'green' })
  } catch (err) {
    toast.add({ title: 'gagal mengubah pertanyaan.', color: 'red' })
  }
};

const saveOption = async (option) => {
  const token = Cookies.get("access_token");
  try {
    await $fetch(`${config.public.backend}/api/quiz/${option.option_id}/edit_option`, {
      method: "PATCH",
      body: {
        option_text: option.option_text,
        is_correct: option.is_correct,
      },
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    option.dirty = false;
    toast.add({ title: 'Berhasil mengubah opsi.', color: 'green' })
  } catch (err) {
    toast.add({ title: 'Gagal mengubah opsi.', color: 'red' })
  }
};

const setCorrectOption = (question, selectedOption) => {
  question.options.forEach((opt) => {
    opt.is_correct = opt.option_id === selectedOption.option_id;
    opt.dirty = true;
  });
};

watch(() => quiz.value?.title, (val, oldVal) => {
  if (quiz.value) quiz.value.titleDirty = true;
});

const watchQuestions = () => {
  quiz.value.questions.forEach((q) => {
    watch(
      () => q.question_text,
      () => {
        q.dirty = true;
      }
    );
    q.options.forEach((o) => {
      watch(
        () => o.option_text,
        () => {
          o.dirty = true;
        }
      );
    });
  });
};

onMounted(async () => {
  await fetchQuiz();
  watchQuestions();
});
</script>