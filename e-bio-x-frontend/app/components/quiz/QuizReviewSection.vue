<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between flex-wrap gap-3">
      <div>
        <h3 class="text-lg font-semibold flex items-center gap-2">
          <Icon name="material-symbols:lightbulb" class="w-6 h-6 text-amber-400" />
          Telaah Pembahasan AI
        </h3>
        <p class="text-sm text-gray-500">Pembahasan dibuat berdasarkan kunci jawaban yang ditetapkan guru.</p>
      </div>
      <button
        v-if="items.length"
        class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition"
        @click="reviewAll"
      >
        <Icon name="material-symbols:visibility" class="w-4 h-4" />
        Review Semua Pembahasan
      </button>
    </div>

    <div v-if="loading" class="text-center py-6 text-gray-500">Memuat pembahasan...</div>

    <div v-else-if="error" class="text-center py-6 text-red-500">
      <p>{{ error }}</p>
    </div>

    <div v-else-if="!items.length" class="bg-white dark:bg-gray-900 border rounded-xl p-8 text-center text-gray-500">
      Belum ada jawaban yang terekam untuk percobaan ini.
    </div>

    <QuizExplanationCard
      v-for="(item, i) in items"
      v-show="expanded || item.is_correct === false"
      :key="item.question_id"
      :explanation="item.explanation"
      :personal="item.personal"
      :answer="item.answer"
      :is-correct="item.is_correct"
      :status="item.status"
      :index="i"
      :question-options="item.options || []"
      class="fade-enter"
    />
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const props = defineProps({
  attemptId: { type: Number, required: true },
});

const items = ref([]);
const loading = ref(true);
const error = ref("");
const expanded = ref(false);

const load = async () => {
  loading.value = true;
  try {
    const payload = await $fetch(`${config.public.backend}/api/student/attempts/${props.attemptId}/explanations`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    items.value = payload.results || [];
  } catch (e) {
    error.value = e?.data?.error || "Tidak dapat memuat pembahasan";
    toast.add({ title: error.value, color: "red" });
  } finally {
    loading.value = false;
  }
};

const reviewAll = () => {
  expanded.value = true;
};

load();

watch(() => props.attemptId, load);
</script>

<style scoped>
.fade-enter {
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>