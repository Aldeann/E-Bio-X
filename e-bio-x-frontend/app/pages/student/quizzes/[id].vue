<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex items-center gap-2 mb-6">
      <button
        class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        @click="backToList"
      >
        <Icon name="material-symbols:arrow-back" class="w-6 h-6" />
      </button>
      <h2 class="text-2xl font-semibold">Kerjakan Kuis</h2>
    </div>

    <template v-if="!playing && !result">
      <div v-if="loading" class="text-center py-10 text-gray-500">Memuat kuis...</div>
      <QuizLanding
        v-else-if="quiz"
        :quiz="quiz"
        @start="startAttempt"
      />
      <p v-else class="text-center py-10 text-gray-500">Kuis tidak ditemukan.</p>
    </template>

    <QuizPlayer
      v-else-if="playing"
      :quiz-id="quizId"
      @submitted="onSubmitted"
    />

    <div v-else-if="result" class="max-w-3xl mx-auto">
      <QuizResultView :result="result" />
      <div class="mt-6 flex flex-wrap gap-3 justify-center">
        <NuxtLink
          :to="`/student/quizzes/${quizId}/result`"
          class="border border-green-600 text-green-700 dark:text-green-400 px-5 py-2 rounded-lg hover:bg-green-50 dark:hover:bg-gray-800 transition"
        >
          Buka Halaman Hasil
        </NuxtLink>
        <button
          class="bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg transition"
          @click="resetToLanding"
        >
          Kembali
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
const route = useRoute();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const quizId = Number(route.params.id);
const quiz = ref(null);
const loading = ref(true);
const playing = ref(false);
const result = ref(null);

const load = async () => {
  loading.value = true;
  try {
    quiz.value = await $fetch(`${config.public.backend}/api/student/quizzes/${quizId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: e?.data?.error || "Kuis tidak ditemukan", color: "red" });
    quiz.value = null;
  } finally {
    loading.value = false;
  }
};

const startAttempt = () => {
  playing.value = true;
};

const onSubmitted = (res) => {
  playing.value = false;
  result.value = res;
  quiz.value = null;
  load();
};

const resetToLanding = () => {
  result.value = null;
};

const backToList = () => {
  navigateTo("/student/quizzes");
};

load();

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>