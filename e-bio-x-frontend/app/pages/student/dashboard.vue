<template>
  <div class="container mx-auto px-4 py-6">
    <div class="mb-6">
      <h2 class="text-2xl font-semibold">Dashboard Belajar</h2>
      <p class="text-sm text-gray-500">
        Pantau progres belajarmu, lanjutkan materi, dan lihat hasil kuismu.
      </p>
    </div>

    <!-- Langkah berikutnya (Fase 5): SATU arahan utama supaya siswa tidak
         bingung harus apa setelah membaca. Alasan ditampilkan apa adanya;
         alternatif disediakan bila siswa ingin memilih sendiri. -->
    <div
      v-if="nextAction && nextAction.action && nextAction.action.type !== 'done'"
      class="mb-6 rounded-xl border border-brand-300 dark:border-brand-700 bg-gradient-to-br from-brand-50 to-white dark:from-brand-900/30 dark:to-surface p-4"
    >
      <div class="flex items-start gap-3">
        <div class="shrink-0 w-9 h-9 rounded-full bg-brand-700 text-white flex items-center justify-center">
          <Icon :name="nbaIcon" class="w-5 h-5" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-[11px] uppercase tracking-wide font-semibold text-brand-700 dark:text-brand-300">
            Langkah berikutnya
          </p>
          <p class="font-semibold text-gray-800 dark:text-gray-100">
            {{ nextAction.action.title }}
          </p>
          <p v-if="nextAction.action.reason" class="text-sm text-gray-600 dark:text-gray-300 mt-0.5">
            {{ nextAction.action.reason }}
          </p>
          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-if="nextAction.action.cta"
              @click="runAction(nextAction.action)"
              class="px-4 py-2 rounded-lg bg-brand-700 hover:bg-brand-800 text-white text-sm font-semibold flex items-center gap-1.5"
            >
              <Icon :name="ctaIcon(nextAction.action.cta.kind)" class="w-4 h-4" />
              {{ nextAction.action.cta.label }}
            </button>
            <button
              v-for="(alt, ai) in (nextAction.alternatives || [])"
              :key="ai"
              @click="runAction(alt)"
              class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200 text-sm"
            >
              {{ alt.title }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="text-center py-16 text-brand-700">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="data">
      <!-- Summary cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
        <div
          v-for="card in summaryCards"
          :key="card.label"
          class="rounded-xl border border-line bg-surface p-4"
        >
          <div class="flex items-center justify-between">
            <Icon :name="card.icon" class="w-5 h-5 text-brand-700 dark:text-brand-300" />
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
          <h4 class="text-lg font-semibold text-brand-700 dark:text-brand-300 flex items-center gap-2">
            <Icon name="material-symbols:auto-awesome" class="w-5 h-5" />
            Rekomendasi Belajar Anda
          </h4>
          <span class="text-xs text-gray-400">Berdasarkan perkembangan belajarmu</span>
        </div>

        <div
          v-if="profile && profile.status === 'READY'"
          class="rounded-xl border border-line bg-brand-50 dark:bg-brand-900/30 p-4 mb-4"
        >
          <div class="flex flex-wrap items-center gap-2 mb-1">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-700 text-white">
              Penguasaan: {{ profile.mastery_label }}
            </span>
            <span
              v-if="profile.cluster_label"
              class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white dark:bg-gray-800 border border-line"
            >
              {{ clusterLabel(profile.cluster_label) }}
            </span>
          </div>
          <p v-if="profile.message" class="text-sm text-brand-800 dark:text-brand-200 mt-1">
            {{ profile.message }}
          </p>
          <!-- Which class model produced this label. A student can sit in
               more than one class, so without this the badge above looks
               like a verdict on the student when it is really the class's
               model speaking. -->
          <p
            v-if="profile.model_scope"
            class="text-xs mt-2 pt-2 border-t border-line text-gray-600 dark:text-gray-400"
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
            class="mt-2 pt-2 border-t border-line"
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
                  :class="f.direction === 'below' ? 'text-red-500' : 'text-brand-700'"
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
          class="rounded-xl border border-line bg-surface p-4 mb-4"
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
            class="rounded-xl border border-line bg-surface p-4 flex flex-col"
          >
            <div class="flex items-center gap-2">
              <span class="w-6 h-6 rounded-full bg-brand-700 text-white text-xs flex items-center justify-center shrink-0">
                {{ i + 1 }}
              </span>
              <p class="font-semibold text-gray-800 dark:text-gray-100 truncate flex-1">{{ r.title }}</p>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              Topik: {{ r.topic || "-" }} <span v-if="r.phase">· Fase {{ r.phase }}</span>
              <span v-if="r.estimated_time"> · ⏱ {{ r.estimated_time }}</span>
            </p>
            <div v-if="r.mastery != null" class="flex items-center gap-2 mt-2">
              <div class="flex-1 h-2 bg-surface-muted rounded-full overflow-hidden">
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
                <Icon name="material-symbols:check-circle" class="w-3.5 h-3.5 text-brand-700 mt-0.5 shrink-0" />
                {{ reason }}
              </li>
            </ul>
            <button
              @click="openMaterial(r)"
              class="mt-3 w-full px-3 py-2 rounded-lg bg-brand-700 hover:bg-brand-800 text-white text-sm font-semibold flex items-center justify-center gap-1"
            >
              <Icon name="material-symbols:play-arrow" class="w-4 h-4" />
              Pelajari Sekarang
            </button>
          </div>
        </div>
        <p v-else class="text-sm text-gray-500">Belum ada rekomendasi materi untuk Anda.</p>

        <!-- Rekomendasi per BAGIAN (Fase 3e) -->
        <div v-if="sectionRecs.length" class="mt-6">
          <h5 class="text-sm font-semibold text-brand-700 dark:text-brand-300 mb-1 flex items-center gap-2">
            <Icon name="material-symbols:account-tree" class="w-4 h-4" />
            Bagian yang Perlu Diperkuat
          </h5>
          <p class="text-xs text-gray-500 mb-3">
            Diurutkan dari jawaban Anda sendiri per bagian
            (kuis, soal interaktif, dan latihan). Peringkatannya aturan transparan,
            bukan hasil model.
          </p>

          <div v-if="rankedSectionRecs.length" class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div
              v-for="(s, i) in rankedSectionRecs"
              :key="`${s.material_id}-${s.section_id}`"
              class="rounded-xl border border-amber-200 dark:border-amber-800 bg-surface p-4 flex flex-col"
            >
              <div class="flex items-start gap-2">
                <span class="w-6 h-6 rounded-full bg-amber-700 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">
                  {{ i + 1 }}
                </span>
                <div class="min-w-0">
                  <p class="font-semibold text-gray-800 dark:text-gray-100 truncate">
                    {{ s.section_title }}
                  </p>
                  <p class="text-xs text-gray-500 truncate">{{ s.material_title }}</p>
                </div>
              </div>

              <div v-if="s.mastery_score != null" class="flex items-center gap-2 mt-2">
                <div class="flex-1 h-2 bg-surface-muted rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :class="masteryBar(s.mastery_score)"
                    :style="{ width: Math.min(s.mastery_score, 100) + '%' }"
                  ></div>
                </div>
                <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">
                  Penguasaan {{ Math.round(s.mastery_score) }}%
                </span>
              </div>

              <ul v-if="s.reasons && s.reasons.length" class="mt-2 space-y-1 flex-1">
                <li
                  v-for="(reason, ri) in s.reasons"
                  :key="ri"
                  class="text-xs text-gray-600 dark:text-gray-300 flex items-start gap-1"
                >
                  <Icon name="material-symbols:check-circle" class="w-3.5 h-3.5 text-amber-600 mt-0.5 shrink-0" />
                  {{ reason }}
                </li>
              </ul>

              <div class="mt-3 flex flex-col gap-2">
                <button
                  @click="openPractice(s)"
                  :disabled="s.practice_available === false"
                  :title="s.practice_available === false
                    ? 'Belum ada soal latihan yang disetujui guru untuk bagian ini.'
                    : 'Buka sesi latihan yang menyesuaikan dengan jawabanmu.'"
                  class="w-full px-3 py-2 rounded-lg bg-amber-700 hover:bg-amber-800 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold flex items-center justify-center gap-1"
                >
                  <Icon name="material-symbols:auto-awesome" class="w-4 h-4" />
                  Latihan adaptif
                  <span v-if="s.practice_total" class="text-[11px] font-normal opacity-90">
                    ({{ s.practice_total }} soal)
                  </span>
                </button>
                <button
                  @click="openSection(s)"
                  class="w-full px-3 py-2 rounded-lg border border-amber-300 dark:border-amber-700 hover:bg-amber-50 dark:hover:bg-amber-900/20 text-amber-700 dark:text-amber-300 text-sm font-medium flex items-center justify-center gap-1"
                >
                  <Icon name="material-symbols:menu-book" class="w-4 h-4" />
                  Buka materi
                </button>
                <p v-if="s.practice_available === false" class="text-[11px] text-gray-500">
                  Belum ada soal latihan yang disetujui guru untuk bagian ini.
                </p>
                <p v-else-if="s.recently_practiced" class="text-[11px] text-gray-500">
                  Baru kamu latih - ulangi besok agar lebih efektif.
                </p>
              </div>
            </div>
          </div>

          <!-- Bagian yang jawabannya belum cukup: sengaja TIDAK diberi skor. -->
          <div
            v-if="hintSectionRecs.length"
            class="mt-3 rounded-xl border border-line bg-surface-muted p-3"
          >
            <p class="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">
              Belum bisa dinilai
            </p>
            <p class="text-xs text-gray-500 mb-2">
              Bagian berikut dijawab terlalu sedikit untuk dinilai, jadi sengaja
              tidak diberi peringkat.
            </p>
            <ul class="space-y-1">
              <li
                v-for="h in hintSectionRecs"
                :key="`hint-${h.material_id}-${h.section_id}`"
                class="flex items-center justify-between gap-2 text-xs text-gray-600 dark:text-gray-300"
              >
                <span class="min-w-0 truncate">
                  {{ h.section_title }}
                  <span class="text-gray-400">· {{ h.material_title }}</span>
                </span>
                <button
                  v-if="h.practice_available"
                  @click="openPractice(h)"
                  class="shrink-0 px-2.5 py-1 rounded-lg bg-brand-700 hover:bg-brand-800 text-white text-[11px] font-semibold flex items-center gap-1"
                >
                  <Icon name="material-symbols:auto-awesome" class="w-3.5 h-3.5" />
                  Latihan adaptif
                </button>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Continue learning -->
      <div v-if="data.continue_learning && data.continue_learning.length" class="mb-8">
        <h4 class="text-lg font-semibold text-brand-700 dark:text-brand-300 mb-3 flex items-center gap-2">
          <Icon name="material-symbols:play-circle" class="w-5 h-5" />
          Lanjutkan Belajar
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <NuxtLink
            v-for="m in data.continue_learning"
            :key="m.material_id"
            :to="`/student/materials/${m.material_id}`"
            class="rounded-xl border border-line bg-surface p-4 hover:shadow-lg transition"
          >
            <p class="font-semibold text-gray-800 dark:text-gray-100 truncate">{{ m.title }}</p>
            <p class="text-xs text-gray-500 mt-1 mb-2">
              Topik: {{ m.topic || "-" }} <span v-if="m.phase">· Fase {{ m.phase }}</span>
            </p>
            <div class="flex items-center gap-3">
              <div class="flex-1 h-2 bg-surface-muted rounded-full overflow-hidden">
                <div
                  class="h-full bg-brand-700 rounded-full"
                  :style="{ width: m.progress_percentage + '%' }"
                ></div>
              </div>
              <span class="text-xs font-semibold text-brand-700 dark:text-brand-300">
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
          <h4 class="text-lg font-semibold text-brand-700 dark:text-brand-300 flex items-center gap-2">
            <Icon name="material-symbols:menu-book" class="w-5 h-5" />
            Progres Materi
          </h4>
          <NuxtLink to="/student/progress" class="text-sm text-brand-700 hover:underline">
            Lihat riwayat →
          </NuxtLink>
        </div>
        <div class="rounded-xl border border-line overflow-hidden">
          <div
            v-for="m in data.materials"
            :key="m.material_id"
            class="flex flex-wrap md:flex-nowrap items-center gap-3 px-4 py-3 bg-surface border-b last:border-b-0 border-line"
          >
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-sm text-gray-800 dark:text-gray-100 truncate">{{ m.title }}</p>
              <p class="text-xs text-gray-500">{{ m.topic || "Tanpa topik" }} · {{ m.total_sections }} bagian</p>
            </div>
            <div class="w-full md:w-40">
              <div class="flex items-center gap-2">
                <div class="flex-1 h-2 bg-surface-muted rounded-full overflow-hidden">
                  <div class="h-full bg-brand-700 rounded-full" :style="{ width: m.progress_percentage + '%' }"></div>
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
              class="text-sm px-3 py-1.5 rounded-lg bg-brand-700 hover:bg-brand-800 text-white shrink-0"
            >
              {{ m.status === 'selesai' ? 'Ulangi' : 'Buka' }}
            </NuxtLink>
          </div>
        </div>
      </div>
    </template>

    <!-- Latihan adaptif langsung dari saran (Tahap 1): tanpa lompat halaman. -->
    <StudentSectionPracticeModal
      :open="practiceOpen"
      :material-id="practiceMaterialId"
      :section-id="practiceSectionId"
      :section-title="practiceSectionTitle"
      @close="closePractice"
    />
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
// Rekomendasi per bagian (Fase 3e). `ranked: true` = ada skor nyata;
// `ranked: false` = datanya belum cukup, jadi TIDAK diberi skor sama sekali.
const sectionRecs = ref([]);
const rankedSectionRecs = computed(() => sectionRecs.value.filter((s) => s.ranked));
const hintSectionRecs = computed(() => sectionRecs.value.filter((s) => !s.ranked));

// Tahap 1 rekomendasi adaptif: state modal latihan yang dibuka langsung dari
// kartu saran (tanpa pindah ke halaman materi lebih dulu).
const practiceOpen = ref(false);
const practiceMaterialId = ref(null);
const practiceSectionId = ref(null);
const practiceSectionTitle = ref("");

// Langkah berikutnya (Fase 5): satu aksi tunggal dari server.
const nextAction = ref(null);
const nbaIcon = computed(() => {
  const t = nextAction.value?.action?.type;
  const map = {
    practice_weak: "material-symbols:fitness-center",
    practice_after_read: "material-symbols:fitness-center",
    continue_reading: "material-symbols:menu-book",
    take_quiz: "material-symbols:quiz",
    start_next_material: "material-symbols:rocket-launch",
    review_mastered: "material-symbols:refresh",
  };
  return map[t] || "material-symbols:bolt";
});
const ctaIcon = (kind) => {
  const map = {
    practice: "material-symbols:auto-awesome",
    read: "material-symbols:menu-book",
    quiz: "material-symbols:quiz",
    material: "material-symbols:rocket-launch",
  };
  return map[kind] || "material-symbols:arrow-forward";
};

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
  // "interactive_accuracy" tidak lagi ada: fitur itu dihapus dari backend
  // bersama tipe soal interaktifnya. Kunci mati di peta label hanya membiarkan
  // fitur lama tampil sebagai kunci mentah, karena fallback-nya `f`.
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
  // "interactive_accuracy" sengaja tidak ikut: kolomnya sudah tidak dikirim
  // backend (feature_version 1.1). Kini easy/medium/hard_accuracy berasal dari
  // jawaban latihan, bukan soal interaktif.
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
  if (v >= 75) return "bg-brand-700";
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
      }).catch(() => ({ recommendations: [], section_recommendations: [] })),
    ]);
    profile.value = prof;
    recommendations.value = recs.recommendations || [];
    sectionRecs.value = recs.section_recommendations || [];
  } catch (e) {
    recommendations.value = [];
    sectionRecs.value = [];
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

// Klik saran bagian: kirim section_id supaya yang tercatat adalah baris
// bagian, bukan baris materi, lalu buka tepat bagiannya.
const openSection = async (s) => {
  try {
    await $fetch(`${config.public.backend}/api/student/recommendations/click`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { material_id: s.material_id, section_id: s.section_id },
    });
  } finally {
    navigateTo(`/student/materials/${s.material_id}?section=${s.section_id}`);
  }
};

// Buka latihan adaptif langsung dari kartu saran. Klik tetap dicatat supaya
// evaluasi saran (Fase 3e) tidak kehilangan sinyal, tetapi pencatatan yang
// gagal tidak boleh menghalangi siswa mulai berlatih.
const openPractice = async (s) => {
  try {
    await $fetch(`${config.public.backend}/api/student/recommendations/click`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { material_id: s.material_id, section_id: s.section_id },
    });
  } catch (e) {
    // diamkan: membuka latihan tidak boleh gagal karena pencatatan klik
  }
  practiceMaterialId.value = s.material_id;
  practiceSectionId.value = s.section_id;
  practiceSectionTitle.value = s.section_title;
  practiceOpen.value = true;
};

// Setelah latihan ditutup, segarkan saran supaya angka penguasaan dan
// prioritas ikut memperhitungkan jawaban yang barusan masuk.
const closePractice = () => {
  practiceOpen.value = false;
  loadRecs();
  loadNextAction();
};

// Langkah berikutnya (Fase 5): ambil satu aksi utama dari server.
const nbaKey = (action) => {
  const c = (action && action.cta) || {};
  return [action?.type, c.material_id, c.section_id, c.quiz_id].join(":");
};

// Catat tayang/klik langkah berikutnya (Fase 5b). Endpoint ini tidak
// menyentuh status materi, jadi aman dipanggil dari dasbor.
const logNbaEvent = async (eventType, action, surface) => {
  const cta = action && action.cta;
  if (!cta || !cta.material_id) return;
  try {
    await $fetch(`${config.public.backend}/api/student/next-action/event`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: {
        event_type: eventType,
        material_id: cta.material_id,
        section_id: cta.section_id || null,
        action_type: action.type,
        surface,
      },
    });
  } catch (e) {
    // pencatatan opsional, jangan ganggu alur belajar
  }
};

const lastNbaShownKey = ref(null);

const loadNextAction = async () => {
  try {
    nextAction.value = await $fetch(
      `${config.public.backend}/api/student/next-action`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    const act = nextAction.value && nextAction.value.action;
    if (act && act.cta && act.type !== "done") {
      const k = nbaKey(act);
      // Satu tayang per aksi: hindari menggandakan impression saat refresh.
      if (k !== lastNbaShownKey.value) {
        lastNbaShownKey.value = k;
        logNbaEvent("next_action_shown", act, "dashboard");
      }
    }
  } catch (e) {
    nextAction.value = null;
  }
};

// Jalankan aksi yang disarankan. Latihan memakai jalur modal yang sudah ada;
// aksi lain hanya berpindah halaman.
const runAction = (action) => {
  const cta = action && action.cta;
  if (!cta) return;
  logNbaEvent("next_action_clicked", action, "dashboard");
  if (cta.kind === "practice" && cta.section_id) {
    openPractice({
      material_id: cta.material_id,
      section_id: cta.section_id,
      section_title: cta.section_title || action.title,
    });
    return;
  }
  if (cta.kind === "quiz" && cta.quiz_id) {
    navigateTo(`/student/quizzes/${cta.quiz_id}`);
    return;
  }
  if (cta.material_id) {
    const q = cta.section_id ? `?section=${cta.section_id}` : "";
    navigateTo(`/student/materials/${cta.material_id}${q}`);
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
    // Dua kartu "Soal Interaktif" dan "Akurasi Interaktif" dihapus: tipe soal
    // itu sudah tidak ada di produk dan angkanya selalu 0, jadi ia hanya
    // menampilkan keadaan kosong kepada siswa yang tidak bisa berbuat apa-apa
    // atasnya.
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
    selesai: "bg-brand-100 dark:bg-brand-900/40 text-brand-800 dark:text-brand-200",
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
loadNextAction();

definePageMeta({
  layout: "student",
  middleware: "auth",
  role: "student",
});
</script>