<template>
  <div class="container mx-auto px-4 py-6">
    <div class="mb-6">
      <h2 class="text-2xl font-semibold">Machine Learning Insights</h2>
      <p class="text-sm text-gray-500">
        Analisis penguasaan, profil belajar, dan rekomendasi berbasis data.
      </p>
    </div>

    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="data">
      <!-- Overview -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:groups" class="w-5 h-5 text-green-600 dark:text-green-500" />
            <span class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ data.analyzed }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Siswa Dianalisis</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:hourglass-disabled" class="w-5 h-5 text-amber-500" />
            <span class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ data.insufficient_data }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Data Belum Cukup</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:psychology" class="w-5 h-5 text-blue-500" />
            <span class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ modelVersion }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Versi Model</p>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
          <div class="flex items-center justify-between">
            <Icon name="material-symbols:dataset" class="w-5 h-5 text-purple-500" />
            <span class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{
              data.model && data.model.training_sample_count != null ? data.model.training_sample_count : "-"
            }}</span>
          </div>
          <p class="text-xs text-gray-500 mt-2">Sampel Training</p>
        </div>
      </div>

      <!-- Distributions -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Distribusi Mastery Level</h4>
          <div
            v-for="(v, k) in masteryLabels(data.mastery_distribution)"
            :key="k"
            class="flex items-center gap-3 mb-2"
          >
            <span class="w-36 text-sm text-gray-600 dark:text-gray-300">{{ v.name }}</span>
            <div class="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div class="h-full rounded-full" :class="v.color" :style="{ width: pct(data.mastery_distribution, v.key) + '%' }"></div>
            </div>
            <span class="text-sm font-semibold w-8 text-right">{{ data.mastery_distribution[v.key] || 0 }}</span>
          </div>
          <p v-if="!counts(data.mastery_distribution)" class="text-sm text-gray-500">Belum ada data mastery.</p>
        </div>

        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Distribusi Learning Profile</h4>
          <div
            v-for="(v, k) in Object.entries(data.profile_distribution || {})"
            :key="k"
            class="flex items-center gap-3 mb-2"
          >
            <span class="w-36 text-sm text-gray-600 dark:text-gray-300">{{ profileLabel(v[0]) }}</span>
            <div class="flex-1 h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div class="h-full rounded-full bg-blue-500" :style="{ width: pct(data.profile_distribution, v[0]) + '%' }"></div>
            </div>
            <span class="text-sm font-semibold w-8 text-right">{{ v[1] }}</span>
          </div>
          <p v-if="!counts(data.profile_distribution)" class="text-sm text-gray-500">Belum ada data profil belajar.</p>
        </div>
      </div>

      <!-- Model performance -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 flex items-center gap-2">
            <Icon name="material-symbols:schema" class="w-5 h-5" />
            Model Decision Tree
          </h4>
          <template v-if="data.model && data.model.metrics">
            <p v-if="data.model.metrics.evaluation_note" class="text-sm text-amber-600 mb-2">{{ data.model.metrics.evaluation_note }}</p>
            <div v-if="data.model.metrics.accuracy !== undefined" class="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div class="rounded-lg bg-gray-100 dark:bg-gray-800 p-3 text-center">
                <p class="text-lg font-bold text-gray-800 dark:text-gray-100">{{ data.model.metrics.accuracy }}</p>
                <p class="text-xs text-gray-500">Accuracy</p>
              </div>
              <div class="rounded-lg bg-gray-100 dark:bg-gray-800 p-3 text-center">
                <p class="text-lg font-bold text-gray-800 dark:text-gray-100">{{ data.model.metrics.precision }}</p>
                <p class="text-xs text-gray-500">Precision</p>
              </div>
              <div class="rounded-lg bg-gray-100 dark:bg-gray-800 p-3 text-center">
                <p class="text-lg font-bold text-gray-800 dark:text-gray-100">{{ data.model.metrics.recall }}</p>
                <p class="text-xs text-gray-500">Recall</p>
              </div>
              <div class="rounded-lg bg-gray-100 dark:bg-gray-800 p-3 text-center">
                <p class="text-lg font-bold text-gray-800 dark:text-gray-100">{{ data.model.metrics.f1_score }}</p>
                <p class="text-xs text-gray-500">F1</p>
              </div>
            </div>
            <p class="text-xs text-gray-400 mt-2">
              Dilatih: {{ data.model.trained_at ? new Date(data.model.trained_at).toLocaleDateString() : "-" }}
              · Sampel: {{ data.model.training_sample_count }}
            </p>
          </template>
          <p v-else class="text-sm text-gray-500">
            {{
              data.model && data.model.metrics && data.model.metrics.evaluation_note
                ? data.model.metrics.evaluation_note
                : "Model belum memiliki evaluasi yang valid."
            }}
          </p>
        </div>

        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 flex items-center gap-2">
            <Icon name="material-symbols:scatter-plot" class="w-5 h-5" />
            Klaster K-Means
          </h4>
          <template v-if="data.clusters">
            <p class="text-sm text-gray-600 dark:text-gray-300 mb-2">
              Jumlah klaster: <b>{{ data.clusters.k }}</b>
              <span v-if="data.clusters.silhouette != null" class="ml-2">
                Silhouette: <b>{{ data.clusters.silhouette }}</b>
              </span>
            </p>
            <div class="space-y-2">
              <div
                v-for="p in data.clusters.profiles"
                :key="p.cluster_id"
                class="border border-gray-100 dark:border-gray-700 rounded-lg p-2"
              >
                <p class="text-sm font-semibold text-gray-800 dark:text-gray-100">
                  {{ profileLabel(p.label) }}
                  <span class="text-xs font-normal text-gray-500">({{ p.member_count }} siswa)</span>
                </p>
                <p class="text-xs text-gray-500">{{ p.description }}</p>
              </div>
            </div>
            <p class="text-xs text-gray-400 mt-2">Nilai silhouette digunakan untuk melihat seberapa baik data terpisah dalam cluster.</p>
          </template>
          <p v-else class="text-sm text-gray-500">Model K-Means belum tersedia.</p>
        </div>
      </div>

      <!-- Topics & recommendations -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Topik Perlu Penguatan</h4>
          <div v-if="data.topics_needing_reinforcement && data.topics_needing_reinforcement.length" class="space-y-2">
            <div
              v-for="(t, i) in data.topics_needing_reinforcement"
              :key="i"
              class="flex items-center justify-between gap-3"
            >
              <p class="text-sm text-gray-700 dark:text-gray-200 truncate">{{ i + 1 }}. {{ t.topic }}</p>
              <span class="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-400 shrink-0">
                {{ t.average_progress }}%
              </span>
            </div>
          </div>
          <p v-else class="text-sm text-gray-500">Belum ada topik yang perlu penguatan.</p>
        </div>

        <div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5">
          <h4 class="font-semibold text-gray-800 dark:text-gray-100 mb-3">Rekomendasi Terpopuler</h4>
          <div v-if="data.top_recommendations && data.top_recommendations.length" class="space-y-2">
            <div
              v-for="(r, i) in data.top_recommendations"
              :key="i"
              class="flex items-center justify-between gap-3"
            >
              <p class="text-sm text-gray-700 dark:text-gray-200 truncate">{{ i + 1 }}. {{ r.title }}</p>
              <span class="text-xs text-gray-500 shrink-0">{{ r.count }} siswa</span>
            </div>
          </div>
          <p v-else class="text-sm text-gray-500">Belum ada rekomendasi tercatat.</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from "vue";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const data = ref(null);
const loading = ref(true);

const modelVersion = computed(() => (data.value?.model?.model_version || "-"));

const counts = (obj) => {
  if (!obj) return 0;
  return Object.values(obj).reduce((a, b) => a + (b || 0), 0);
};

const pct = (obj, key) => {
  const total = counts(obj);
  return total ? Math.round(((obj[key] || 0) / total) * 100) : 0;
};

const masteryLabels = (dist) => {
  const order = [
    { key: "VERY_GOOD", name: "Sangat Baik", color: "bg-green-600" },
    { key: "GOOD", name: "Baik", color: "bg-emerald-500" },
    { key: "FAIR", name: "Cukup", color: "bg-amber-500" },
    { key: "NEEDS_REINFORCEMENT", name: "Perlu Penguatan", color: "bg-red-500" },
  ];
  return order.filter((o) => dist && dist[o.key] !== undefined);
};

const profileLabelMap = {
  "High Achievement": "Pencapaian Tinggi",
  "Active Learner": "Pembelajar Aktif",
  "Moderate Learner": "Pembelajar Sedang",
  "Needs Support": "Perlu Pendampingan",
  "Low Activity": "Aktivitas Rendah",
};
const profileLabel = (l) => profileLabelMap[l] || l;

const load = async () => {
  loading.value = true;
  try {
    data.value = await $fetch(`${config.public.backend}/api/teacher/analytics/ml`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat insights", color: "red" });
  } finally {
    loading.value = false;
  }
};

load();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>