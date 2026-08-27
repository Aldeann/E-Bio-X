<template>
  <div class="space-y-4">
    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat pratinjau...</div>

    <template v-else-if="quiz">
      <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-5">
        <h3 class="text-lg font-semibold text-green-700 dark:text-green-500">{{ quiz.title }}</h3>
        <p v-if="quiz.description" class="text-sm text-gray-500 mt-1">{{ quiz.description }}</p>
        <div class="flex flex-wrap gap-2 mt-3 text-xs">
          <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            {{ quiz.question_count }} soal
          </span>
          <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            Total {{ quiz.total_points }} poin
          </span>
          <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            Durasi {{ quiz.duration || "-" }} menit
          </span>
          <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            Nilai lulus {{ quiz.passing_grade }}%
          </span>
        </div>
      </div>

      <div class="space-y-3">
        <div
          v-for="(q, i) in sortedQuestions"
          :key="q.question_id"
          class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-sm p-5"
        >
          <div class="flex items-center gap-2 flex-wrap">
            <span class="w-7 h-7 flex items-center justify-center rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400 text-sm font-semibold">
              {{ i + 1 }}
            </span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400">
              {{ typeLabel(q.question_type) }}
            </span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400">
              {{ difficultyLabel(q.difficulty) }}
            </span>
            <span class="text-xs text-gray-500">Bobot {{ q.points }} poin</span>
          </div>
          <p class="mt-2 font-medium">{{ q.question_text }}</p>
          <img
            v-if="q.image_url"
            :src="q.image_url"
            alt="Gambar soal"
            class="mt-2 max-h-48 rounded-lg border border-gray-200 dark:border-gray-700"
          />
          <div class="mt-3 space-y-2 text-sm">
            <div
              v-for="o in q.options"
              :key="o.option_id"
              class="flex items-center gap-2 p-2.5 rounded-lg border"
              :class="o.is_correct
                ? 'border-green-500 bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                : 'border-gray-200 dark:border-gray-700'"
            >
              <Icon
                :name="o.is_correct ? 'material-symbols:check-circle' : 'material-symbols:radio-button-unchecked'"
                class="w-5 h-5 shrink-0"
                :class="o.is_correct ? 'text-green-600' : 'text-gray-400'"
              />
              <span>{{ o.option_text }}</span>
              <span v-if="o.is_correct" class="text-xs">
                <Icon name="material-symbols:electric-bolt" class="w-4 h-4 inline" /> Kunci jawaban
              </span>
            </div>
          </div>
          <div v-if="q.explanation" class="mt-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-sm text-blue-800 dark:text-blue-300">
            <span class="font-semibold">Pembahasan: </span>{{ q.explanation }}
          </div>
        </div>
      </div>
    </template>

    <div v-else class="text-gray-500 text-center py-10">Kuis tidak ditemukan.</div>
  </div>
</template>

<script setup>
const props = defineProps({
  quizId: { type: Number, required: true },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const quiz = ref(null);
const loading = ref(true);

const sortedQuestions = computed(() =>
  [...(quiz.value?.questions || [])].sort((a, b) => a.order_index - b.order_index)
);

const typeLabel = (t) => (t === "true_false" ? "Benar/Salah" : "Pilihan Ganda");
const difficultyLabel = (d) => (d === "easy" ? "Mudah" : d === "hard" ? "Sulit" : "Sedang");

const load = async () => {
  loading.value = true;
  try {
    quiz.value = await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.quizId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat pratinjau kuis", color: "red" });
  } finally {
    loading.value = false;
  }
};

load();
</script>