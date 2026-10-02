<template>
  <div class="container mx-auto px-4 py-6">
    <div class="mb-6">
      <h2 class="text-2xl font-semibold">Dashboard Belajar</h2>
      <p class="text-sm text-gray-500">
        Pantau progres belajarmu, lanjutkan materi, dan lihat hasil kuismu.
      </p>
    </div>

    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="data">
      <!-- Summary cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
        <div
          v-for="card in summaryCards"
          :key="card.label"
          class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4"
        >
          <div class="flex items-center justify-between">
            <Icon :name="card.icon" class="w-5 h-5 text-green-600 dark:text-green-500" />
            <span class="text-2xl font-bold text-gray-800 dark:text-gray-100">
              {{ card.value }}
            </span>
          </div>
          <p class="text-xs text-gray-500 mt-2">{{ card.label }}</p>
        </div>
      </div>

      <!-- Recommendations -->
      <div v-if="recommendationsLoaded" class="mb-8">
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-lg font-semibold text-green-700 dark:text-green-400 flex items-center gap-2">
            <Icon name="material-symbols:auto-awesome" class="w-5 h-5" />
            Rekomendasi Belajar Anda
          </h4>
          <span class="text-xs text-gray-400">Berdasarkan perkembangan belajarmu</span>
        </div>

        <div
          v-if="profile && profile.status === 'READY'"
          class="rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-4 mb-4"
        >
          <div class="flex flex-wrap items-center gap-2 mb-1">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-600 text-white">
              Penguasaan: {{ profile.mastery_label }}
            </span>
            <span
              v-if="profile.cluster_label"
              class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white dark:bg-gray-800 border border-green-200 dark:border-green-800"
            >
              {{ clusterLabel(profile.cluster_label) }}
            </span>
          </div>
          <p v-if="profile.message" class="text-sm text-green-800 dark:text-green-200 mt-1">
            {{ profile.message }}
          </p>
          <!-- Which class model produced this label. A student can sit in
               more than one class, so without this the badge above looks
               like a verdict on the student when it is really the class's
               model speaking. -->
          <p
            v-if="profile.model_scope"
            class="text-xs mt-2 pt-2 border-t border-green-200 dark:border-green-800 text-gray-600 dark:text-gray-400"
          >
            <Icon
              :name="profile.model_scope.scope === 'class' ? 'material-symbols:groups' : 'material-symbols:info'"
              class="w-3.5 h-3.5 inline -mt-0.5"
            />
            {{ profile.model_scope.note }}
          </p>
          <!-- The cluster badge can come from a different model than the
               mastery badge (another class's K-Means, or the pooled one).
               When it does, say so instead of letting it ride silently
               under the mastery model's note above. -->
          <p
            v-if="clusterScopeDiffers()"
            class="text-xs mt-1 text-gray-600 dark:text-gray-400"
          >
            <Icon
              name="material-symbols:scatter-plot"
              class="w-3.5 h-3.5 inline -mt-0.5"
            />
            {{ profile.cluster_scope.note }}
          </p>
          <!-- Evidence behind the label, not just the verdict. These are
               the Decision Tree's own feature importances compared against
               the real class averages stored at training time. -->
          <div
            v-if="profile.factors && profile.factors.length"
            class="mt-2 pt-2 border-t border-green-200 dark:border-green-800"
          >
            <p class="text-xs font-semibold text-gray-700 dark:text-gray-200 mb-1">
              Faktor utama:
            </p>
            <ul class="space-y-1">
              <li
                v-for="(f, fi) in profile.factors"
                :key="fi"
                class="text-xs text-gray-600 dark:text-gray-300"
              >
                <Icon
                  :name="f.direction === 'below' ? 'material-symbols:trending-down' : 'material-symbols:trending-up'"
                  class="w-3.5 h-3.5 inline -mt-0.5"
                  :class="f.direction === 'below' ? 'text-red-500' : 'text-green-600'"
                />
                {{ featureLabel(f.feature) }}:
                <span class="font-semibold">{{ formatFactorValue(f.feature, f.value) }}</span>
                <span class="text-gray-400">
                  (rata-rata kelas {{ formatFactorValue(f.feature, f.cohort_average) }})
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div
          v-else-if="profile && profile.status !== 'READY'"
          class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4 mb-4"
        >
          <p class="text-sm text-gray-600 dark:text-gray-300">
            <Icon name="material-symbols:info" class="w-4 h-4 inline -mt-0.5" />
            {{ profile.message || "Belum cukup data untuk menentukan profil belajar." }}
          </p>
        </div>

        <div v-if="recommendations.length" class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div
            v-for="(r, i) in recommendations"
            :key="r.material_id"
            class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4 flex flex-col"
          >
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-green-600 text-white text-xs flex items-center justify-center shrink-0">
                {{ i + 1 }}
              </span>
              <p class="font-semibold text-gray-800 dark:text-gray-100 truncate flex-1">{{ r.title }}</p>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Topik: {{ r.topic || "-" }} <span v-if="r.phase">· Fase {{ r.phase }}</span>
              <span v-if="r.estimated_time"> · ⏱ {{ r.estimated_time }}</span>
            </p>
            <div v-if="r.mastery != null" class="flex items-center gap-2 mt-2">
              <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full"
                  :class="masteryBar(r.mastery)"
                  :style="{ width: Math.min(r.mastery, 100) + '%' }"
                ></div>
              </div>
              <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">
                Penguasaan {{ Math.round(r.mastery) }}%
              </span>
            </div>
            <ul v-if="r.reasons && r.reasons.length" class="mt-2 space-y-1 flex-1">
              <li
                v-for="(reason, ri) in r.reasons"
                :key="ri"
                class="text-xs text-gray-600 dark:text-gray-300 flex items-start gap-1"
              >
                <Icon name="material-symbols:check-circle" class="w-3.5 h-3.5 text-green-600 mt-0.5 shrink-0" />
                {{ reason }}
              </li>
            </ul>
            <button
              @click="openMaterial(r)"
              class="mt-3 w-full px-3 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold flex items-center justify-center gap-1"
            >
              <Icon name="material-symbols:play-arrow" class="w-4 h-4" />
              Pelajari Sekarang
            </button>
          </div>
        </div>
        <p v-else class="text-sm text-gray-500">Belum ada rekomendasi materi untuk Anda.</p>
      </div>

      <!-- Continue learning -->
      <div v-if="data.continue_learning && data.continue_learning.length" class="mb-8">
        <h4 class="text-lg font-semibold text-green-700 dark:text-green-400 mb-3 flex items-center gap-2">
          <Icon name="material-symbols:play-circle" class="w-5 h-5" />
          Lanjutkan Belajar
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <NuxtLink
            v-for="m in data.continue_learning"
            :key="m.material_id"
            :to="`/student/materials/${m.material_id}`"
            class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-4 hover:shadow-lg transition"
          >
            <p class="font-semibold text-gray-800 dark:text-gray-100 truncate">{{ m.title }}</p>
            <p class="text-xs text-gray-500 mt-1 mb-2">
              Topik: {{ m.topic || "-" }} <span v-if="m.phase">· Fase {{ m.phase }}</span>
            </p>
            <div class="flex items-center gap-3">
              <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-green-600 rounded-full"
                  :style="{ width: m.progress_percentage + '%' }"
                ></div>
              </div>
              <span class="text-xs font-semibold text-green-700 dark:text-green-400">
                {{ Math.round(m.progress_percentage) }}%
              </span>
            </div>
            <p v-if="m.last_section_title" class="text-xs text-gray-400 mt-2 truncate">
              Terakhir: {{ m.last_section_title }}
            </p>
          </NuxtLink>
        </div>
      </div>

      <!-- Materials progress -->
      <div class="mb-8">
        <div class="flex items-center justify-between mb-3">
          <h4 class="text-lg font-semibold text-green-700 dark:text-green-400 flex items-center gap-2">
            <Icon name="material-symbols:menu-book" class="w-5 h-5" />
            Progres Materi
          </h4>
          <NuxtLink to="/student/progress" class="text-sm text-green-600 hover:underline">
            Lihat riwayat →
          </NuxtLink>
        </div>
        <div class="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div
            v-for="m in data.materials"
            :key="m.material_id"
            class="flex flex-wrap md:flex-nowrap items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900 border-b last:border-b-0 border-gray-100 dark:border-gray-800"
          >
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-sm text-gray-800 dark:text-gray-100 truncate">{{ m.title }}</p>
              <p class="text-xs text-gray-500">{{ m.topic || "Tanpa topik" }} · {{ m.total_sections }} bagian</p>
            </div>
            <div class="w-full md:w-40">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div class="h-full bg-green-600 rounded-full" :style="{ width: m.progress_percentage + '%' }"></div>
                </div>
                <span class="text-xs font-semibold w-9 text-right">{{ Math.round(m.progress_percentage) }}%</span>
              </div>
            </div>
            <span
              class="text-xs px-2 py-1 rounded-full font-medium shrink-0"
              :class="statusClass(m.status)"
            >
              {{ statusLabel(m.status) }}
            </span>
            <NuxtLink
              :to="`/student/materials/${m.material_id}`"
              class="text-sm px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white shrink-0"
            >
              {{ m.status === 'selesai' ? 'Ulangi' : 'Buka' }}
            </NuxtLink>
          </div>
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
const profile = ref(null);
const recommendations = ref([]);
const recommendationsLoaded = ref(false);

const clusterLabelMap = {
  "High Achievement": "Pencapaian Tinggi",
  "Active Learner": "Pembelajar Aktif",
  "Moderate Learner": "Pembelajar Sedang",
  "Needs Support": "Perlu Pendampingan",
  "Low Activity": "Aktivitas Rendah",
};

const clusterLabel = (label) => clusterLabelMap[label] || label;

// Human labels + number formatting for the Decision Tree's explanation
// factors. The backend emits raw feature keys and 0..1 ratios; showing
// "section_completion_rate 0.42" to a student helps nobody.
const featureLabelMap = {
  material_completion_rate: "Penyelesaian materi",
  section_completion_rate: "Penyelesaian bagian materi",
  interactive_accuracy: "Akurasi soal interaktif",
  quiz_average: "Rata-rata kuis",
  quiz_best_score: "Nilai kuis terbaik",
  easy_accuracy: "Akurasi soal mudah",
  medium_accuracy: "Akurasi soal sedang",
  hard_accuracy: "Akurasi soal sulit",
  learning_minutes: "Waktu belajar",
  quiz_attempts: "Percobaan kuis",
  correct_rate: "Tingkat jawaban benar",
  forum_posts_count: "Posting forum",
  forum_replies_count: "Balasan forum",
  forum_questions_asked: "Pertanyaan diajukan",
  forum_answers_given: "Jawaban diberikan",
  forum_reactions_received: "Reaksi diterima",
  ai_explanations_viewed: "Penjelasan AI dilihat",
  ai_explanations_helpful: "Penjelasan AI membantu",
};
const featureLabel = (f) => featureLabelMap[f] || f;

const RATIO_FEATURES = new Set([
  "material_completion_rate",
  "section_completion_rate",
  "interactive_accuracy",
  "quiz_average",
  "quiz_best_score",
  "easy_accuracy",
  "medium_accuracy",
  "hard_accuracy",
  "correct_rate",
]);
const formatFactorValue = (feature, value) => {
  const v = Number(value) || 0;
  if (RATIO_FEATURES.has(feature)) return Math.round(v * 100) + "%";
  if (feature === "learning_minutes") return Math.round(v) + " mnt";
  return String(Math.round(v));
};

// True unless the cluster badge clearly came from the same class model as
// the mastery badge. A pooled K-Means is always shown, because the mastery
// note names only the Decision Tree and must not be read as covering the
// cluster too.
const clusterScopeDiffers = () => {
  const p = profile.value;
  if (!p || !p.cluster_label || !p.cluster_scope) return false;
  const m = p.model_scope || {};
  const c = p.cluster_scope;
  if (c.scope !== "class") return true;
  return m.scope !== c.scope || m.teacher_id !== c.teacher_id;
};

const masteryBar = (v) => {
  if (v >= 75) return "bg-green-600";
  if (v >= 60) return "bg-amber-500";
  return "bg-red-500";
};

const loadRecs = async () => {
  try {
    const [prof, recs] = await Promise.all([
      $fetch(`${config.public.backend}/api/student/learning-profile`, {
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => null),
      $fetch(`${config.public.backend}/api/student/recommendations`, {
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => ({ recommendations: [] })),
    ]);
    profile.value = prof;
    recommendations.value = recs.recommendations || [];
  } catch (e) {
    recommendations.value = [];
  } finally {
    recommendationsLoaded.value = true;
  }
};

const openMaterial = async (r) => {
  try {
    await $fetch(`${config.public.backend}/api/student/recommendations/click`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { material_id: r.material_id },
    });
  } finally {
    navigateTo(`/student/materials/${r.material_id}`);
  }
};

const formatSeconds = (s) => {
  s = s || 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h} jam ${m} mnt` : `${m} mnt`;
};

const summaryCards = computed(() => {
  const s = data.value?.summary || {};
  return [
    { label: "Materi Selesai", value: s.materials_completed ?? 0, icon: "material-symbols:task-alt" },
    { label: "Progres Rata-rata", value: s.average_progress ? s.average_progress + "%" : "0%", icon: "material-symbols:percent" },
    { label: "Kuis Dikerjakan", value: s.quizzes_taken ?? 0, icon: "material-symbols:quiz" },
    { label: "Rata-rata Kuis", value: s.quiz_avg ? s.quiz_avg + "%" : "0%", icon: "material-symbols:monitoring" },
    { label: "Waktu Belajar", value: formatSeconds(s.learning_seconds), icon: "material-symbols:schedule" },
    { label: "Soal Interaktif", value: s.interactive_answered ?? 0, icon: "material-symbols:question-answer" },
    { label: "Akurasi Interaktif", value: s.interactive_accuracy ? s.interactive_accuracy + "%" : "0%", icon: "material-symbols:verified" },
    { label: "Materi Diikuti", value: s.materials_started ?? 0, icon: "material-symbols:menu-book" },
  ];
});

const statusLabel = (s) => {
  const map = {
    belum_dimulai: "Belum Dimulai",
    dimulai: "Dimulai",
    sedang_belajar: "Sedang Belajar",
    selesai: "Selesai",
  };
  return map[s] || s;
};

const statusClass = (s) => {
  const map = {
    belum_dimulai: "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300",
    dimulai: "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400",
    sedang_belajar: "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400",
    selesai: "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400",
  };
  return map[s] || map.belum_dimulai;
};

const load = async () => {
  loading.value = true;
  try {
    data.value = await $fetch(`${config.public.backend}/api/student/dashboard`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat dashboard", color: "red" });
  } finally {
    loading.value = false;
  }
};

load();
loadRecs();

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>