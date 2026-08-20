<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex items-center gap-2 mb-6">
      <button class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" @click="$router.push('/student/quizzes')">
        <Icon name="material-symbols:arrow-back" class="w-6 h-6" />
      </button>
      <h2 class="text-2xl font-semibold">Hasil Kuis</h2>
    </div>

    <div v-if="loading" class="text-center py-10 text-gray-500">Memuat hasil...</div>

    <div v-else-if="error" class="text-center py-12">
      <Icon name="material-symbols:error" class="w-12 h-12 text-red-400 mx-auto mb-3" />
      <p class="text-gray-700 dark:text-gray-300">{{ error }}</p>
    </div>

    <div v-else-if="result" class="max-w-3xl mx-auto space-y-6">
      <QuizResultView :result="result" />
      <QuizReviewSection v-if="result.attempt_id" :attempt-id="result.attempt_id" />
      <div class="flex justify-center">
        <NuxtLink
          :to="`/student/quizzes/${quizId}`"
          class="bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg transition"
        >
          Kembali ke Kuis
        </NuxtLink>
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
const result = ref(null);
const loading = ref(true);
const error = ref("");

const load = async () => {
  loading.value = true;
  try {
    result.value = await $fetch(`${config.public.backend}/api/student/quizzes/${quizId}/result`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    error.value = e?.data?.error || "Belum ada hasil untuk kuis ini";
    toast.add({ title: error.value, color: "red" });
  } finally {
    loading.value = false;
  }
};

load();

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>