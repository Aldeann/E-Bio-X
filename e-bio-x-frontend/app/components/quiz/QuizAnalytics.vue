<template>
  <div class="space-y-5">
    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat analitik...</div>

    <template v-else-if="data">
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-4 text-center">
          <p class="text-2xl font-bold text-green-700 dark:text-green-500">{{ data.summary.participants }}</p>
          <p class="text-xs text-gray-500 mt-1">Peserta</p>
        </div>
        <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-4 text-center">
          <p class="text-2xl font-bold text-green-700 dark:text-green-500">{{ data.summary.attempts }}</p>
          <p class="text-xs text-gray-500 mt-1">Total Percobaan</p>
        </div>
        <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-4 text-center">
          <p class="text-2xl font-bold text-green-700 dark:text-green-500">{{ data.summary.avg_percentage }}%</p>
          <p class="text-xs text-gray-500 mt-1">Rata-rata</p>
        </div>
        <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-4 text-center">
          <p class="text-2xl font-bold text-green-700 dark:text-green-500">{{ data.summary.highest }}%</p>
          <p class="text-xs text-gray-500 mt-1">Tertinggi</p>
        </div>
        <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-4 text-center">
          <p class="text-2xl font-bold text-green-700 dark:text-green-500">{{ data.summary.lowest }}%</p>
          <p class="text-xs text-gray-500 mt-1">Terendah</p>
        </div>
        <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-4 text-center">
          <p
            class="text-2xl font-bold"
            :class="data.summary.pass_rate >= 60 ? 'text-green-600' : 'text-red-500'"
          >{{ data.summary.pass_rate }}%</p>
          <p class="text-xs text-gray-500 mt-1">Tingkat Kelulusan</p>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-5">
        <h4 class="font-semibold text-green-700 dark:text-green-500 mb-3">Analisis per Soal</h4>

        <div v-if="data.questions.length === 0" class="text-gray-500 text-sm">Belum ada data hasil pengerjaan.</div>

        <div v-else class="space-y-3">
          <div v-for="(q, i) in data.questions" :key="q.question_id" class="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div class="flex items-start justify-between gap-2">
              <p class="font-medium flex-1">
                <span class="text-green-700 dark:text-green-500 font-semibold mr-1">Q{{ i + 1 }}.</span>
                {{ q.text }}
              </p>
              <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400 shrink-0">
                {{ q.correct_rate }}% benar
              </span>
            </div>
            <div class="mt-3 flex flex-col sm:flex-row sm:items-center gap-2">
              <div class="flex-1 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                <div
                  class="h-full bg-green-500"
                  :style="{ width: q.correct_rate + '%' }"
                ></div>
              </div>
              <span class="text-xs text-gray-500">
                {{ q.correct_count }}/{{ q.correct_count + q.wrong_count }} menjawab benar ·
                {{ q.unanswered }} tidak terjawab
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow p-5">
        <h4 class="font-semibold text-green-700 dark:text-green-500 mb-3">Skor per Siswa</h4>

        <div v-if="data.attempts_by_student.length === 0" class="text-gray-500 text-sm">Belum ada siswa yang mengerjakan.</div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-gray-500 border-b border-gray-200 dark:border-gray-700">
                <th class="py-2 pr-3">Siswa</th>
                <th class="py-2 pr-3">Percobaan</th>
                <th class="py-2 pr-3">Skor</th>
                <th class="py-2 pr-3">Status</th>
                <th class="py-2 pr-3">Dikumpulkan</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(a, i) in data.attempts_by_student"
                :key="i"
                class="border-b border-gray-100 dark:border-gray-800"
              >
                <td class="py-2 pr-3">{{ a.student_name }}</td>
                <td class="py-2 pr-3">#{{ a.attempt_number }}</td>
                <td class="py-2 pr-3 font-semibold">{{ a.percentage }}%</td>
                <td class="py-2 pr-3">
                  <span
                    class="px-2 py-0.5 rounded-full text-xs"
                    :class="a.passed ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400' : 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-400'"
                  >
                    {{ a.passed ? "Lulus" : "Tidak Lulus" }}
                  </span>
                </td>
                <td class="py-2 pr-3 text-gray-500">{{ formatDate(a.submitted_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="text-gray-500 text-center py-10">Tidak dapat memuat analitik.</div>
  </div>
</template>

<script setup>
const props = defineProps({
  quizId: { type: Number, required: true },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const data = ref(null);
const loading = ref(true);

const load = async () => {
  loading.value = true;
  try {
    data.value = await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.quizId}/analytics`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat analitik kuis", color: "red" });
  } finally {
    loading.value = false;
  }
};

const formatDate = (iso) => {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("id-ID", { dateStyle: "short", timeStyle: "short" });
};

load();
</script>