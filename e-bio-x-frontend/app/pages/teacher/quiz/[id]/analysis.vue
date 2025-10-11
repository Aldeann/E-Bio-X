<template>
  <div class="">
    <div class="flex items-center gap-3 mb-4">
      <Icon name="material-symbols:bar-chart" class="text-green-600 dark:text-green-500" size="32" />
      <h1 class="text-2xl font-bold text-green-700 dark:text-green-500">Analisis Hasil Kuis</h1>
    </div>

    <div v-if="isLoading" class="bg-yellow-50 dark:text-white dark:bg-yellow-100 border border-yellow-300 rounded-xl p-4 mb-6">
      <p class="text-yellow-800 text-sm">Loading ...</p>
    </div>
    <div
      v-else-if="!analysisReady"
      class="bg-yellow-50 dark:text-white dark:bg-yellow-100 border border-yellow-300 rounded-xl p-4 mb-6">
      <p class="text-yellow-800 text-sm">
        Analisis belum dilakukan. Klik tombol di bawah untuk memulai.
      </p>
    </div>

    <div v-else>
      <div class="bg-green-50 dark:bg-green-900/50 border border-green-300 rounded-xl p-6 mb-6 space-y-4">
        <h2 class="text-xl font-bold text-green-800 dark:text-green-50 flex items-center gap-2">
          <Icon name="material-symbols:info" size="24" /> {{ quizInfo.title }}
        </h2>

        <div class="grid gap-4">
          <p class="text-sm text-green-700 dark:text-green-50">
            Jumlah soal: <span class="font-semibold">{{ quizInfo.total_questions }}</span>
          </p>
          <p class="text-sm text-green-700 dark:text-green-50">
            Jumlah siswa: <span class="font-semibold">{{ quizInfo.total_students }}</span>
          </p>
          <p class="text-sm text-green-700 dark:text-green-50">
            Rata-rata Nilai: <span class="font-semibold">{{ quizInfo.average }}</span>
          </p>
        </div>

        <div class="space-y-3">
          <h3 class="text-green-800 dark:text-green-100 text-base font-semibold border-b border-green-300 pb-1">
            Statistik Siswa
          </h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p class="text-sm text-green-700 dark:text-green-50 mb-1">Nilai Tertinggi</p>
              <AnalysisStudentCard
                :nama="quizInfo.highest.nama"
                :cluster="quizInfo.highest.cluster"
                :score="quizInfo.highest.score"
                :work_time="quizInfo.highest.work_time" />
            </div>

            <div>
              <p class="text-sm text-green-700 dark:text-green-50 mb-1">Nilai Terendah</p>
              <AnalysisStudentCard
                :nama="quizInfo.lowest.nama"
                :cluster="quizInfo.lowest.cluster"
                :score="quizInfo.lowest.score"
                :work_time="quizInfo.lowest.work_time" />
            </div>

            <div>
              <p class="text-sm text-green-700 dark:text-green-50 mb-1">Pengerjaan Tercepat</p>
              <AnalysisStudentCard
                :nama="quizInfo.fastest.nama"
                :cluster="quizInfo.fastest.cluster"
                :score="quizInfo.fastest.score"
                :work_time="quizInfo.fastest.work_time" />
            </div>

            <div>
              <p class="text-sm text-green-700 dark:text-green-50 mb-1">Pengerjaan Terlambat</p>
              <AnalysisStudentCard
                :nama="quizInfo.slowest.nama"
                :cluster="quizInfo.slowest.cluster"
                :score="quizInfo.slowest.score"
                :work_time="quizInfo.slowest.work_time" />
            </div>
          </div>
        </div>
        <div class="space-y-3">
          <h3 class="text-green-800 dark:text-green-100 text-base font-semibold border-b border-green-300 pb-1">
            Statistik Soal
          </h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              class="flex flex-row items-center justify-between p-3 border border-green-300 rounded shadow-sm bg-white dark:bg-gray-800">
              <div class="w-2/3 flex flex-col gap-1">
                <div class="flex items-center gap-2">
                  <Icon name="qlementine-icons:task-past-16" size="20" class="text-red-600" />
                  <span class="text-sm">Soal Tersulit</span>
                </div>
                <p class="font-semibold text-gray-700 dark:text-gray-200">
                  {{ quizInfo.hardest_question.question }}
                </p>
              </div>
              <div class="text-sm text-gray-700 dark:text-gray-200 flex flex-col gap-1">
                <div>
                  <Icon
                    name="material-symbols:check-circle-rounded"
                    size="16"
                    class="text-green-500 mr-1" />
                  {{ quizInfo.hardest_question.correct_answers }} / {{ quizInfo.hardest_question.total_answers }}
                </div>
              </div>
            </div>
            <div
              class="flex flex-row items-center justify-between p-3 border border-green-300 rounded shadow-sm bg-white dark:bg-gray-800">
              <div class="w-2/3 flex flex-col gap-1">
                <div class="flex items-center gap-2">
                  <Icon name="qlementine-icons:task-16" size="20" class="text-blue-500" />
                  <span class="text-sm">Soal Termudah</span>
                </div>
                <p class="font-semibold text-gray-700 dark:text-gray-200">
                  {{ quizInfo.easiest_question.question }}
                </p>
              </div>
              <div class="text-sm text-gray-700 dark:text-gray-200 flex flex-col gap-1">
                <div>
                  <Icon
                    name="material-symbols:check-circle-rounded"
                    size="16"
                    class="text-green-500 mr-1" />
                  {{ quizInfo.easiest_question.correct_answers }} / {{ quizInfo.easiest_question.total_answers }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white dark:bg-gray-900 border rounded-xl p-4 mb-6 shadow">
        <h3 class="text-green-800 dark:text-green-500 text-lg font-semibold">Analisis K-Means</h3>
        <AnalysisChartCluster :labels="chartLabels" :datasets="chartDatasets" />
        <div class="mb-2 flex gap-3 items-center" @click="showStudentList = !showStudentList">
          <h5 class="text-green-700 dark:text-green-500 text-md font-semibold">Daftar siswa</h5>
          <span class="text-green-700 dark:text-green-500 flex items-center">
            <Icon
              name="mdi:chevron-down"
              :class="[
                'w-5 h-5 transition-transform duration-200',
                showStudentList ? 'rotate-0' : 'rotate-180',
              ]" />
          </span>
        </div>
        <div
          class="overflow-hidden transition-all duration-300 ease-in-out"
          :class="showStudentList ? 'max-h-full opacity-100' : 'max-h-0 opacity-0'">
          <AnalysisClusterResult :clusters="clusters" />
        </div>
      </div>

      <AnalysisDecisionTree :rules="decisionTree" />
    </div>

    <div class="flex gap-2 mt-6">
      <button
        @click="startAnalysis"
        class="bg-green-600 text-white px-4 py-2 rounded-xl hover:bg-green-700 transition">
        <Icon name="material-symbols:play-arrow" size="20" />
        {{ analysisReady ? "Analisis Ulang" : "Mulai Analisis" }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import Cookies from "js-cookie";
import AnalysisChartCluster from "~/components/AnalysisChartCluster.vue";

const config = useRuntimeConfig();
const token = Cookies.get("access_token");
const route = useRoute();
const quizId = route.params.id;

const toast = useToast();

const clusters = ref([]);
const decisionTree = ref("");
const chartLabels = ref([]);
const chartDatasets = ref([]);
const isLoading = ref(true);
const showStudentList = ref(false);
const analysisReady = ref(false);
const quizInfo = ref({
  title: "",
  total_questions: 0,
  total_students: 0,
  highest: { nama: "-", cluster: "-", work_time: "-", score: 0 },
  lowest: { nama: "-", cluster: "-", work_time: "-", score: 0 },
  average: 0,
  fastest: { nama: "-", cluster: "-", work_time: "-", score: 0 },
  slowest: { nama: "-", cluster: "-", work_time: "-", score: 0 },
  hardest_question: { question: "-", correct_answers: 0, total_answers: 0 },
  easiest_question: { question: "-", correct_answers: 0, total_answers: 0 },
});

const startAnalysis = async () => {
  try {
    await $fetch(`${config.public.backend}/api/analysis/${quizId}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    await getAnalysis();
    
    toast.add({title: 'Analisis berhasil.', color: 'green' });
  } catch (error) {
    toast.add({title: 'Gagal melakukan analisis.', color: 'red' });
  }
};

const getAnalysis = async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/analysis/${quizId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    clusters.value = res.clusters;
    decisionTree.value = res.decision_tree_rules;

    quizInfo.value = {
      title: res.quiz_title,
      total_questions: res.total_questions,
      total_students: res.total_students,
      highest: res.highest_score,
      lowest: res.lowest_score,
      average: res.average_score.toFixed(2),
      fastest: res.fastest_work_time,
      slowest: res.slowest_work_time,
      hardest_question: res.hardest_question || {
        question: "-",
        correct_answers: 0,
        total_answers: 0,
      },
      easiest_question: res.easiest_question || {
        question: "-",
        correct_answers: 0,
        total_answers: 0,
      },
    };

    const clusterCounts = {};
    res.clusters.forEach((item) => {
      const clusterLabel = `${item.cluster}`;
      clusterCounts[clusterLabel] = (clusterCounts[clusterLabel] || 0) + 1;
    });

    chartLabels.value = Object.keys(clusterCounts);
    chartDatasets.value = [
      {
        label: "Jumlah Siswa",
        backgroundColor: ["#ef4444", "#3b82f6", "#facc15"],
        data: Object.values(clusterCounts),
      },
    ];

    analysisReady.value = true;
  } catch (error) {
    toast.add({title: 'Gagal melakukan analisis.', color: 'red' })
    analysisReady.value = false;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  getAnalysis();
});
</script>
