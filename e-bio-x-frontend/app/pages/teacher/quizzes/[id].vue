<template>
  <div class="container mx-auto px-4 py-6 max-w-4xl">
    <div class="flex items-center justify-between gap-3 mb-6">
      <div class="flex items-center gap-2">
        <button class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" @click="$router.push('/teacher/quizzes')">
          <Icon name="material-symbols:arrow-back" class="w-6 h-6" />
        </button>
        <h2 class="text-2xl font-semibold">Builder Kuis</h2>
      </div>
      <div class="flex gap-2">
        <button
          class="border border-green-600 text-green-700 dark:text-green-400 px-3 py-2 rounded-lg hover:bg-green-50 dark:hover:bg-gray-800 transition text-sm"
          @click="showSettings = !showSettings"
        >
          <Icon name="material-symbols:settings" class="w-4 h-4 inline" />
          {{ showSettings ? "Tutup Pengaturan" : "Pengaturan" }}
        </button>
        <button
          class="text-red-500 hover:text-red-700 border border-red-300 px-3 py-2 rounded-lg text-sm"
          @click="removeQuiz"
        >
          Hapus
        </button>
      </div>
    </div>

    <div v-if="showSettings" class="mb-6">
      <QuizSettingsForm
        v-if="quiz"
        :initial="quiz"
        :is-edit="true"
        @cancel="showSettings = false"
        @saved="onSettingsSaved"
      />
    </div>

    <QuizBuilder :quiz-id="quizId" @updated="onUpdated" />
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const route = useRoute();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const quizId = Number(route.params.id);
const quiz = ref(null);
const showSettings = ref(false);

const load = async () => {
  try {
    quiz.value = await $fetch(`${config.public.backend}/api/teacher/quizzes/${quizId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat kuis", color: "red" });
  }
};

const onSettingsSaved = (q) => {
  showSettings.value = false;
  quiz.value = q;
};

const onUpdated = (q) => {
  quiz.value = q;
};

const removeQuiz = async () => {
  const result = await swal.fire({
    title: "Hapus kuis ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/teacher/quizzes/${quizId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Kuis dihapus", color: "green" });
    navigateTo("/teacher/quizzes");
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal menghapus kuis", color: "red" });
  }
};

load();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>