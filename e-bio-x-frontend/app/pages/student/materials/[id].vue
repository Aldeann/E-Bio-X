<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";

const route = useRoute();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const material = ref(null);
const loading = ref(true);
const stateBusy = ref(false);
const activeSectionId = ref(null);
const studentState = ref(null);
const bookmarks = ref([]);
const notes = ref([]);
const quizzes = ref([]);
const sidebarOpen = ref(false);
// Kartu panduan belajar: pengantar selalu terbuka, petunjuk & kebutuhan bisa
// dilipat supaya halaman tidak terlalu panjang saat dibuka pertama kali.
const studyGuideOpen = ref(true);
const learningNeedsOpen = ref(true);
// Kata Pengantar global (satu teks untuk semua materi) dari pengaturan
// aplikasi. Sama di setiap materi, jadi tidak disimpan per materi.
const foreword = ref("");
const forewordOpen = ref(true);
const showCompletion = ref(false);
const heartbeatTimer = ref(null);
const viewedContentIds = ref(new Set());
const hasViewedCompletion = ref(false);
// Latihan adaptif per bagian: tombol langsung di halaman materi supaya murid
// tidak perlu kembali ke dashboard setelah selesai membaca.
const practiceOpen = ref(false);
const practiceSectionId = ref(null);
const practiceSectionTitle = ref("");
// section_id -> jumlah soal latihan yang sudah disetujui guru.
const practiceAvailable = ref({});
// Asesmen diagnostik per bagian (non-adaptif): tombolnya berdampingan dengan
// latihan adaptif, tapi memakai set soal dan endpoint yang berbeda.
const diagnosticOpen = ref(false);
const diagnosticSectionId = ref(null);
const diagnosticSectionTitle = ref("");
const diagnosticAvailable = ref({});
// Gerbang "selesaikan asesmen dulu": berapa soal diagnostik yang sudah dijawab
// siswa ini per bagian, dan berapa yang wajib diselesaikan. `required` dibatasi
// jumlah yang benar-benar disajikan server, jadi tak mungkin mustahil dipenuhi.
const diagnosticAnswered = ref({});
const diagnosticRequired = ref({});
// Rekomendasi materi berikutnya, ditampilkan di layar "Materi Selesai".
const nextMaterials = ref([]);
// Langkah berikutnya (Fase 5b): SATU aksi yang diprioritaskan server,
// ditampilkan di layar "Materi Selesai" supaya murid tahu harus apa.
const nextAction = ref(null);
const lastNbaShownKey = ref(null);
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

const signalActivity = async (eventType, sectionId = null, contentId = null, data = null) => {
  try {
    await $fetch(`${config.public.backend}/api/materials/${route.params.id}/activity`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { event_type: eventType, section_id: sectionId, content_id: contentId, data },
    });
  } catch (e) {
    // aktivitas bersifat opsional, jangan ganggu alur belajar
  }
};

const pingSession = async () => {
  try {
    await $fetch(`${config.public.backend}/api/materials/${route.params.id}/session/ping`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: {},
    });
  } catch (e) {
    // heartbeat opsional
  }
};

watch(activeSectionId, (id, oldId) => {
  if (!id) return;
  const sec = sections.value.find((s) => s.id === id);
  signalActivity("section_opened", id);
  (sec?.contents || []).forEach((c) => {
    if (!viewedContentIds.value.has(c.id)) {
      viewedContentIds.value.add(c.id);
      signalActivity("content_viewed", id, c.id);
    }
  });
});

const sections = computed(() => material.value?.sections || []);
const activeIndex = computed(() =>
  sections.value.findIndex((s) => s.id === activeSectionId.value)
);
const activeSection = computed(
  () => sections.value.find((s) => s.id === activeSectionId.value) || null
);
const completedSectionIds = computed(
  () => studentState.value?.completed_section_ids || []
);
const progressPct = computed(
  () => studentState.value?.student_progress?.percentage || 0
);
const activePracticeTotal = computed(
  () => practiceAvailable.value[activeSectionId.value] || 0
);
const activeDiagnosticTotal = computed(
  () => diagnosticAvailable.value[activeSectionId.value] || 0
);
// Bagian yang punya soal latihan, untuk tombol di layar "Materi Selesai".
const practiceSections = computed(() =>
  sections.value.filter((s) => (practiceAvailable.value[s.id] || 0) > 0)
);
// Bagian yang punya soal diagnostik (pool terpisah, non-adaptif).
const diagnosticSections = computed(() =>
  sections.value.filter((s) => (diagnosticAvailable.value[s.id] || 0) > 0)
);
const activeDiagnosticAnswered = computed(
  () => diagnosticAnswered.value[activeSectionId.value] || 0
);
const activeDiagnosticRequired = computed(
  () => diagnosticRequired.value[activeSectionId.value] || 0
);
// Bagian aktif punya asesmen yang belum tuntas -> perpindahan ditahan.
const activeDiagnosticPending = computed(
  () =>
    activeDiagnosticRequired.value > 0 &&
    activeDiagnosticAnswered.value < activeDiagnosticRequired.value
);

// Gerbang perpindahan bagian. Niat berpindah disimpan dulu, baru dijalankan
// setelah asesmen bagian aktif selesai. TIDAK ada opsi "lewati": satu-satunya
// jalan keluar adalah mengerjakan asesmen (atau membatalkan perpindahan dan
// tetap di bagian ini).
const diagnosticGateOpen = ref(false);
const diagnosticGateTitle = ref("");
let pendingNav = null;
const guardNavigation = (proceed) => {
  if (activeDiagnosticPending.value) {
    pendingNav = proceed;
    diagnosticGateTitle.value = activeSection.value?.title || "";
    diagnosticGateOpen.value = true;
    return;
  }
  proceed();
};
const startGateDiagnostic = () => {
  diagnosticGateOpen.value = false;
  pendingNav = null; // tetap di bagian ini; membatalkan perpindahan, bukan melewati asesmen
  openDiagnostic(activeSectionId.value, activeSection.value?.title || "");
};
const dismissGate = () => {
  diagnosticGateOpen.value = false;
  pendingNav = null;
};

const noteFor = (contentId) =>
  notes.value.find(
    (n) => n.section_id === activeSectionId.value && n.content_id === contentId
  ) || null;

const quizStatusLabel = (q) =>
  q.student_status === "in_progress"
    ? "Sedang Berjalan"
    : q.student_status === "completed"
    ? (q.passed ? "Lulus" : "Belum Lulus")
    : "Belum Dikerjakan";

const quizStatusClass = (q) =>
  q.student_status === "in_progress"
    ? "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400"
    : q.student_status === "completed"
    ? (q.passed
        ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400"
        : "bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-400")
    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300";

const refetchLearningData = async (withState = true) => {
  const tasks = [];
  if (withState)
    tasks.push(
      $fetch(`${config.public.backend}/api/materials/${route.params.id}/state`, {
        headers: { Authorization: `Bearer ${token}` },
      }).then((r) => (studentState.value = r))
    );
  tasks.push(
    $fetch(`${config.public.backend}/api/materials/${route.params.id}/bookmarks`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => (bookmarks.value = r || []))
  );
  tasks.push(
    $fetch(`${config.public.backend}/api/materials/${route.params.id}/notes`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => (notes.value = r || []))
  );
  await Promise.all(tasks);
};

// Ketersediaan soal latihan per bagian (satu request), dipakai tombol
// "Latihan adaptif". Sumbernya endpoint latihan siswa yang sudah ada.
const fetchPracticeAvailability = async () => {
  try {
    const res = await $fetch(
      `${config.public.backend}/api/student/practice/${route.params.id}/sections`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const map = {};
    const diag = {};
    const diagDone = {};
    const diagNeed = {};
    (res.sections || []).forEach((s) => {
      if (s.available) map[s.section_id] = s.practice_total || 0;
      if (s.diagnostic_available) {
        diag[s.section_id] = s.diagnostic_total || 0;
        diagDone[s.section_id] = s.diagnostic_answered || 0;
        diagNeed[s.section_id] = s.diagnostic_required || 0;
      }
    });
    practiceAvailable.value = map;
    diagnosticAvailable.value = diag;
    diagnosticAnswered.value = diagDone;
    diagnosticRequired.value = diagNeed;
  } catch (e) {
    practiceAvailable.value = {};
    diagnosticAvailable.value = {};
    diagnosticAnswered.value = {};
    diagnosticRequired.value = {};
  }
};

const openPractice = (sectionId, title = "") => {
  if (!sectionId) return;
  practiceSectionId.value = sectionId;
  practiceSectionTitle.value = title;
  practiceOpen.value = true;
};

const openDiagnostic = (sectionId, title = "") => {
  if (!sectionId) return;
  diagnosticSectionId.value = sectionId;
  diagnosticSectionTitle.value = title;
  diagnosticOpen.value = true;
};

const closeDiagnostic = () => {
  diagnosticOpen.value = false;
  fetchPracticeAvailability();
};

const closePractice = () => {
  practiceOpen.value = false;
  // Segarkan jumlah soal setelah latihan (mis. status bagian berubah).
  fetchPracticeAvailability();
  // Bila layar "Materi Selesai" sedang terbuka, perbarui langkah berikutnya
  // supaya ikut memperhitungkan jawaban yang barusan masuk.
  if (showCompletion.value) loadNextAction();
};

// Rekomendasi materi berikutnya (bukan materi yang sedang dibuka). Dipakai di
// layar "Materi Selesai" supaya murid tahu harus melanjutkan ke mana.
const fetchRecommendations = async () => {
  try {
    const recs = await $fetch(
      `${config.public.backend}/api/student/recommendations`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    nextMaterials.value = (recs.recommendations || [])
      .filter((r) => String(r.material_id) !== String(route.params.id))
      .slice(0, 3);
  } catch (e) {
    nextMaterials.value = [];
  }
};

const openRecommendedMaterial = async (r) => {
  try {
    await $fetch(`${config.public.backend}/api/student/recommendations/click`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { material_id: r.material_id },
    });
  } catch (e) {
    // pencatatan klik tidak boleh menghalangi navigasi
  }
  navigateTo(`/student/materials/${r.material_id}`);
};

// --- Langkah berikutnya (Fase 5b) ---------------------------------------
const nbaKey = (action) => {
  const c = (action && action.cta) || {};
  return [action?.type, c.material_id, c.section_id, c.quiz_id].join(":");
};

// Catat tayang/klik. Endpoint ini TIDAK menyentuh status materi, jadi
// menampilkan kartu tidak akan menandai materi lain sebagai "dimulai".
const logNbaEvent = async (eventType, action) => {
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
        surface: "material_completion",
      },
    });
  } catch (e) {
    // pencatatan opsional
  }
};

const loadNextAction = async () => {
  try {
    const q = new URLSearchParams();
    q.set("material_id", route.params.id);
    if (activeSectionId.value) q.set("section_id", activeSectionId.value);
    q.set("context", "just_finished_section");
    nextAction.value = await $fetch(
      `${config.public.backend}/api/student/next-action?${q.toString()}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const act = nextAction.value && nextAction.value.action;
    if (act && act.cta && act.type !== "done") {
      const k = nbaKey(act);
      if (k !== lastNbaShownKey.value) {
        lastNbaShownKey.value = k;
        logNbaEvent("next_action_shown", act);
      }
    }
  } catch (e) {
    nextAction.value = null;
  }
};

const runAction = (action) => {
  const cta = action && action.cta;
  if (!cta) return;
  logNbaEvent("next_action_clicked", action);
  if (cta.kind === "practice" && cta.section_id) {
    openPractice(cta.section_id, cta.section_title || action.title);
    return;
  }
  if (cta.kind === "quiz" && cta.quiz_id) {
    navigateTo(`/student/quizzes/${cta.quiz_id}`);
    return;
  }
  if (cta.material_id) {
    const s = cta.section_id ? `?section=${cta.section_id}` : "";
    navigateTo(`/student/materials/${cta.material_id}${s}`);
  }
};

// Layar "Materi Selesai" muncul -> minta server menentukan langkah berikutnya.
watch(showCompletion, (v) => {
  if (v) loadNextAction();
});

const fetchForeword = async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/app-settings`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    foreword.value = (res && res.foreword) || "";
  } catch (e) {
    // Kata pengantar bersifat pelengkap; kalau gagal, halaman tetap jalan.
    foreword.value = "";
  }
};

const fetchDetail = async () => {
  loading.value = true;
  try {
    const detail = await $fetch(
      `${config.public.backend}/api/materials/${route.params.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    material.value = detail;
    await refetchLearningData(true);

    try {
      quizzes.value = await $fetch(
        `${config.public.backend}/api/student/quizzes?material_id=${route.params.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (e) {
      quizzes.value = [];
    }

    await fetchPracticeAvailability();
    await fetchRecommendations();

    const listed = [];
    // ?section= dipakai rekomendasi per bagian (Fase 3e): bagian yang
    // disarankan harus langsung terbuka, bukan hanya materinya.
    const wanted = route.query.section ? Number(route.query.section) : null;
    if (wanted && detail.sections.some((s) => s.id === wanted)) listed.push(wanted);
    const last = studentState.value?.last_section_id;
    if (last && detail.sections.some((s) => s.id === last)) listed.push(last);
    const first = detail.sections.length > 0 ? detail.sections[0].id : null;
    activeSectionId.value = listed.length ? listed[0] : first;
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Materi tidak dapat diakses.";
    toast.add({ title: msg, color: "red" });
  } finally {
    loading.value = false;
  }
};

const persistSection = async (sectionId) => {
  if (!sectionId || stateBusy.value) return;
  stateBusy.value = true;
  // Simpan status selesai SEBELUM request. Materi yang sudah pernah selesai
  // tetap melaporkan `completed: true` dari server (memang fakta historis),
  // jadi layar "Materi Selesai" hanya boleh muncul saat transisi
  // belum-selesai -> selesai, bukan setiap kali posisi bagian disimpan.
  // Tanpa ini, mengulang/meninjau materi yang sudah selesai akan langsung
  // memantulkan layar selesai lagi.
  const wasCompleted = !!(studentState.value && studentState.value.completed);
  try {
    await $fetch(
      `${config.public.backend}/api/materials/${route.params.id}/progress`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: { section_id: sectionId },
      }
    ).catch(() => {});
    try {
      const res = await $fetch(
        `${config.public.backend}/api/materials/${route.params.id}/state`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: { section_id: sectionId },
        }
      );
      if (res && res.state) {
        studentState.value = res.state;
        if (res.state.completed && !wasCompleted && !hasViewedCompletion.value) showCompletion.value = true;
      }
    } catch (e) {
      // abaikan error menyimpan posisi
    }
  } finally {
    stateBusy.value = false;
  }
};

const selectSection = (id) => {
  if (id === activeSectionId.value) return;
  guardNavigation(() => setSection(id));
};

const setSection = (id) => {
  // Jangan biarkan layar "Materi Selesai" muncul lagi saat user
  // sedang meninjau ulang materi yang sudah pernah selesai.
  if (hasViewedCompletion.value) {
    showCompletion.value = false;
  } else {
    showCompletion.value = false;
  }
  activeSectionId.value = id;
  sidebarOpen.value = false;
  persistSection(id);
  window.scrollTo({ top: 0, behavior: "smooth" });
};

const goTo = (offset) => {
  guardNavigation(() => {
    const next = activeIndex.value + offset;
    if (next >= 0 && next < sections.value.length) {
      setSection(sections.value[next].id);
    } else if (offset > 0 && activeIndex.value === sections.value.length - 1) {
      finishMaterial();
    }
  });
};

// Tombol "Selesai!" juga lewat gerbang yang sama: bagian terakhir pun harus
// tuntas asesmennya sebelum layar "Materi Selesai" ditampilkan.
const requestFinish = () => guardNavigation(finishMaterial);

const finishMaterial = async () => {
  try {
    const res = await $fetch(
      `${config.public.backend}/api/materials/${route.params.id}/state`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: { section_id: activeSectionId.value, completed: true },
      }
    );
    if (res.state) studentState.value = res.state;
  } catch (e) {
    // abaikan
  }
  studentState.value = {
    ...(studentState.value || {}),
    student_progress: { ...(studentState.value?.student_progress || {}), finished: true },
    completed: true,
  };
  hasViewedCompletion.value = false;
  showCompletion.value = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
};

const restartLearning = async () => {
  showCompletion.value = false;
  hasViewedCompletion.value = true;
  if (sections.value.length > 0) {
    activeSectionId.value = sections.value[0].id;
    try {
      persistSection(sections.value[0].id);
    } catch (e) {}
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
};

const toggleBookmark = async () => {
  const sectionId = activeSectionId.value;
  if (!sectionId) return;
  const existing = bookmarks.value.find((b) => b.section_id === sectionId);
  try {
    if (existing) {
      await $fetch(
        `${config.public.backend}/api/materials/${route.params.id}/bookmarks/${existing.id}`,
        { method: "DELETE", headers: { Authorization: `Bearer ${token}` } }
      );
      bookmarks.value = bookmarks.value.filter((b) => b.id !== existing.id);
      toast.add({ title: "Bookmark dihapus.", color: "green" });
    } else {
      const res = await $fetch(
        `${config.public.backend}/api/materials/${route.params.id}/bookmarks`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: { section_id: sectionId },
        }
      );
      if (res && !bookmarks.value.some((b) => b.section_id === sectionId)) {
        bookmarks.value.push({
          id: res.bookmark?.id,
          section_id: sectionId,
          content_id: null,
          created_at: new Date().toISOString(),
        });
      }
      toast.add({ title: "Bookmark tersimpan.", color: "green" });
    }
  } catch (e) {
    toast.add({ title: "Gagal mengubah bookmark.", color: "red" });
  }
};

const refreshNotes = () => refetchLearningData(false);

onMounted(async () => {
  await fetchForeword();
  await fetchDetail();
  await pingSession();
  signalActivity("material_opened", activeSectionId.value);
  heartbeatTimer.value = setInterval(pingSession, 60000);
});

onUnmounted(() => {
  if (heartbeatTimer.value) clearInterval(heartbeatTimer.value);
  signalActivity("material_closed", activeSectionId.value);
});

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>

<template>
  <div v-if="loading" class="flex justify-center py-20 text-green-600">
    <Icon name="mdi:loading" class="w-10 h-10 animate-spin" />
  </div>

  <template v-else-if="material">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
      <div>
        <NuxtLink
          to="/student/materials"
          class="text-sm text-green-600 hover:underline flex items-center gap-1 mb-1"
        >
          <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
          Kembali ke Materi
        </NuxtLink>
        <h1 class="text-xl md:text-2xl font-bold text-gray-800 dark:text-gray-100">
          {{ material.title }}
        </h1>
        <p class="text-sm text-gray-500">
          {{ material.subject }} · Topik: {{ material.topic || "-" }} · Fase {{ material.phase
          }}
          <span v-if="material.estimated_time" class="inline-flex items-center gap-1 ml-1">
            · {{ material.estimated_time }}
          </span>
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <NuxtLink
          :to="`/student/forum/new?material_id=${material.id}&course_id=${material.course_id || ''}&topic=${encodeURIComponent(material.title)}&category=${encodeURIComponent(material.topic || '')}`"
          class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-green-300 dark:border-green-700 text-sm font-semibold text-green-700 dark:text-green-300 hover:bg-green-50 dark:hover:bg-green-900/30 transition"
        >
          <Icon name="mdi:forum-outline" class="w-4 h-4" />
          Diskusi di Forum
        </NuxtLink>

        <button
          @click="sidebarOpen = !sidebarOpen"
          class="lg:hidden inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm font-semibold text-gray-700 dark:text-gray-200"
        >
          <Icon name="material-symbols:menu-book" class="w-4 h-4" />
          Daftar Bagian
        </button>
      </div>
    </div>

    <div
      v-if="foreword"
      class="mb-6 rounded-xl border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/30 overflow-hidden"
    >
      <button
        type="button"
        class="w-full flex items-center justify-between gap-2 p-4 text-left"
        @click="forewordOpen = !forewordOpen"
      >
        <span class="font-semibold text-sm text-purple-800 dark:text-purple-200 flex items-center gap-1">
          <Icon name="material-symbols:auto-stories" class="w-4 h-4" />
          Kata Pengantar
        </span>
        <Icon
          name="material-symbols:expand-more"
          class="w-5 h-5 text-purple-700 dark:text-purple-300 transition-transform"
          :class="forewordOpen ? 'rotate-180' : ''"
        />
      </button>
      <div v-show="forewordOpen" class="px-4 pb-4 space-y-1">
        <p
          v-for="(line, i) in foreword.split('\n').map((s) => s.trim()).filter(Boolean)"
          :key="i"
          class="text-sm text-purple-800 dark:text-purple-200"
        >
          {{ line }}
        </p>
      </div>
    </div>

    <div
      v-if="material.introduction"
      class="mb-6 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/30 p-4"
    >
      <p class="font-semibold text-sm text-indigo-800 dark:text-indigo-200 flex items-center gap-1">
        <Icon name="material-symbols:menu-book" class="w-4 h-4" />
        Pengantar
      </p>
      <p
        v-for="(line, i) in (material.introduction || '').split('\n').map((s) => s.trim()).filter(Boolean)"
        :key="i"
        class="text-sm text-indigo-800 dark:text-indigo-200 mt-1"
      >
        {{ line }}
      </p>
    </div>

    <div v-if="material.learning_objectives" class="mb-6 rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/30 p-4">
      <p class="font-semibold text-sm text-blue-800 dark:text-blue-200 flex items-center gap-1">
        <Icon name="material-symbols:flag" class="w-4 h-4" />
        Tujuan Pembelajaran
      </p>
      <ul class="list-disc list-inside text-sm text-blue-800 dark:text-blue-200 mt-1 space-y-1">
        <li
          v-for="(line, i) in (material.learning_objectives || '').split('\n').filter(Boolean)"
          :key="i"
        >
          {{ line }}
        </li>
      </ul>
    </div>

    <div
      v-if="material.learning_guide"
      class="mb-6 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 overflow-hidden"
    >
      <button
        type="button"
        class="w-full flex items-center justify-between gap-2 p-4 text-left"
        @click="studyGuideOpen = !studyGuideOpen"
      >
        <span class="font-semibold text-sm text-amber-800 dark:text-amber-200 flex items-center gap-1">
          <Icon name="material-symbols:list-alt-check" class="w-4 h-4" />
          Petunjuk Pembelajaran
        </span>
        <Icon
          name="material-symbols:expand-more"
          class="w-5 h-5 text-amber-700 dark:text-amber-300 transition-transform"
          :class="studyGuideOpen ? 'rotate-180' : ''"
        />
      </button>
      <ul
        v-show="studyGuideOpen"
        class="list-disc list-inside text-sm text-amber-800 dark:text-amber-200 px-4 pb-4 space-y-1"
      >
        <li
          v-for="(line, i) in (material.learning_guide || '').split('\n').map((s) => s.trim()).filter(Boolean)"
          :key="i"
        >
          {{ line }}
        </li>
      </ul>
    </div>

    <div
      v-if="material.learning_needs"
      class="mb-6 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 overflow-hidden"
    >
      <button
        type="button"
        class="w-full flex items-center justify-between gap-2 p-4 text-left"
        @click="learningNeedsOpen = !learningNeedsOpen"
      >
        <span class="font-semibold text-sm text-emerald-800 dark:text-emerald-200 flex items-center gap-1">
          <Icon name="material-symbols:checklist" class="w-4 h-4" />
          Kebutuhan Belajar
        </span>
        <Icon
          name="material-symbols:expand-more"
          class="w-5 h-5 text-emerald-700 dark:text-emerald-300 transition-transform"
          :class="learningNeedsOpen ? 'rotate-180' : ''"
        />
      </button>
      <ul
        v-show="learningNeedsOpen"
        class="list-disc list-inside text-sm text-emerald-800 dark:text-emerald-200 px-4 pb-4 space-y-1"
      >
        <li
          v-for="(line, i) in (material.learning_needs || '').split('\n').map((s) => s.trim()).filter(Boolean)"
          :key="i"
        >
          {{ line }}
        </li>
      </ul>
    </div>

    <div
      v-if="quizzes.length"
      class="mb-6 rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-4"
    >
      <p class="font-semibold text-sm text-green-800 dark:text-green-200 flex items-center gap-1 mb-3">
        <Icon name="material-symbols:quiz" class="w-4 h-4" />
        Kuis Terkait
      </p>
      <div class="space-y-3">
        <div
          v-for="qz in quizzes"
          :key="qz.id"
          class="flex flex-wrap items-center gap-3 bg-white dark:bg-gray-900 border border-green-200 dark:border-green-800 rounded-lg p-3"
        >
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-sm">{{ qz.title }}</p>
            <div class="flex flex-wrap gap-1.5 text-xs mt-1">
              <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                {{ qz.question_count }} soal
              </span>
              <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                {{ qz.duration || "-" }} menit
              </span>
              <span
                class="px-2 py-0.5 rounded-full"
                :class="quizStatusClass(qz)"
              >
                {{ quizStatusLabel(qz) }}
              </span>
            </div>
          </div>
          <NuxtLink
            v-if="qz.student_status === 'completed'"
            :to="`/student/quizzes/${qz.id}/result`"
            class="text-sm px-3 py-2 rounded-lg bg-white dark:bg-gray-800 border border-green-600 text-green-700 dark:text-green-400 hover:bg-green-100 dark:hover:bg-gray-700 transition text-center"
          >
            Lihat Hasil
          </NuxtLink>
          <NuxtLink
            :to="`/student/quizzes/${qz.id}`"
            class="text-sm px-3 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white transition text-center"
          >
            {{ qz.student_status === 'in_progress' ? 'Lanjutkan' : 'Kerjakan Kuis' }}
          </NuxtLink>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[290px_1fr] gap-6 items-start">
      <aside
        class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4"
        :class="sidebarOpen ? 'block' : 'hidden lg:block'"
      >
        <MaterialLearningSidebar
          :title="material.title"
          :sections="sections"
          :active-section-id="activeSectionId"
          :completed-section-ids="completedSectionIds"
          :bookmarks="bookmarks"
          :percentage="progressPct"
          @select="selectSection"
        />
      </aside>

      <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5 md:p-6 min-w-0">
        <MaterialCompletion
          v-if="showCompletion"
          :title="material.title"
          :total="sections.length"
          :completed="sections.length"
          :percentage="100"
          @restart="restartLearning"
        >
          <template #next>
            <!-- Langkah berikutnya (Fase 5b): satu aksi utama dari server.
                 Bila tidak tersedia, blok lama (latihan per bagian + materi
                 berikutnya) dipakai sebagai cadangan agar layar tetap berguna. -->
            <div
              v-if="nextAction && nextAction.action && nextAction.action.type !== 'done'"
              class="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800 text-left"
            >
              <div class="rounded-xl border border-green-300 dark:border-green-700 bg-green-50/60 dark:bg-green-900/20 p-4">
                <p class="text-[11px] uppercase tracking-wide font-semibold text-green-700 dark:text-green-400 flex items-center gap-1">
                  <Icon :name="nbaIcon" class="w-4 h-4" />
                  Langkah berikutnya
                </p>
                <p class="font-semibold text-gray-800 dark:text-gray-100 mt-1">
                  {{ nextAction.action.title }}
                </p>
                <p v-if="nextAction.action.reason" class="text-sm text-gray-600 dark:text-gray-300 mt-0.5">
                  {{ nextAction.action.reason }}
                </p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <button
                    v-if="nextAction.action.cta"
                    @click="runAction(nextAction.action)"
                    class="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold flex items-center gap-1.5"
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

            <template v-else>
              <div v-if="practiceSections.length" class="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800">
                <p class="text-sm font-semibold text-indigo-700 dark:text-indigo-300 mb-2 flex items-center justify-center gap-1">
                  <Icon name="material-symbols:auto-awesome" class="w-4 h-4" />
                  Latihan adaptif
                </p>
                <div class="flex flex-wrap justify-center gap-2">
                  <button
                    v-for="s in practiceSections"
                    :key="s.id"
                    @click="openPractice(s.id, s.title)"
                    class="px-3 py-2 rounded-lg border border-indigo-300 dark:border-indigo-700 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 text-sm font-medium"
                  >
                    {{ s.title }}
                  </button>
                </div>
              </div>

              <div v-if="diagnosticSections.length" class="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800">
                <p class="text-sm font-semibold text-cyan-700 dark:text-cyan-300 mb-2 flex items-center justify-center gap-1">
                  <Icon name="material-symbols:fact-check" class="w-4 h-4" />
                  Asesmen diagnostik
                </p>
                <p class="text-xs text-gray-500 mb-2">
                  Soal tetap (tidak menyesuaikan jawabanmu). Dipakai mengukur tingkat materi ini.
                </p>
                <div class="flex flex-wrap justify-center gap-2">
                  <button
                    v-for="s in diagnosticSections"
                    :key="s.id"
                    @click="openDiagnostic(s.id, s.title)"
                    class="px-3 py-2 rounded-lg border border-cyan-300 dark:border-cyan-700 hover:bg-cyan-50 dark:hover:bg-cyan-900/20 text-cyan-700 dark:text-cyan-300 text-sm font-medium"
                  >
                    {{ s.title }}
                  </button>
                </div>
              </div>

              <div v-if="nextMaterials.length" class="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800 text-left">
                <p class="text-sm font-semibold text-green-700 dark:text-green-400 mb-2 flex items-center justify-center gap-1">
                  <Icon name="material-symbols:play-circle" class="w-4 h-4" />
                  Materi berikutnya
                </p>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <button
                    v-for="r in nextMaterials"
                    :key="r.material_id"
                    @click="openRecommendedMaterial(r)"
                    class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900 p-3 text-left hover:shadow-md transition"
                  >
                    <p class="font-semibold text-sm text-gray-800 dark:text-gray-100 truncate">{{ r.title }}</p>
                    <p class="text-xs text-gray-500 mt-0.5 truncate">Topik: {{ r.topic || "-" }}</p>
                  </button>
                </div>
              </div>
            </template>
          </template>
        </MaterialCompletion>

        <template v-else-if="activeSection">
          <div class="flex flex-wrap items-center gap-3 mb-5">
            <h2 class="text-lg font-bold text-green-700 dark:text-green-400 mr-auto">
              {{ activeSection.title }}
            </h2>
            <BookmarkButton
              :active="bookmarks.some((b) => b.section_id === activeSectionId)"
              :loading="stateBusy"
              @toggle="toggleBookmark"
            />
          </div>

          <div class="space-y-6">
            <div v-for="content in activeSection.contents" :key="content.id" class="space-y-3">
              <MaterialContentViewer
                :block="content"
                :interactive="true"
                :material-id="material.id"
                :section-id="activeSectionId"
                @submitted="refreshNotes"
              />
              <StudentNote
                :material-id="material.id"
                :section-id="activeSectionId"
                :content-id="content.id"
                :note="noteFor(content.id)"
                @saved="refreshNotes"
              />
            </div>
          </div>

          <div v-if="activePracticeTotal > 0 || activeDiagnosticTotal > 0" class="mt-6 flex flex-wrap gap-2">
            <button
              v-if="activePracticeTotal > 0"
              @click="openPractice(activeSectionId, activeSection.title)"
              class="w-full sm:w-auto px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold flex items-center justify-center gap-1"
            >
              <Icon name="material-symbols:auto-awesome" class="w-4 h-4" />
              Latihan adaptif ({{ activePracticeTotal }} soal)
            </button>
            <button
              v-if="activeDiagnosticTotal > 0"
              @click="openDiagnostic(activeSectionId, activeSection.title)"
              class="w-full sm:w-auto px-4 py-2.5 rounded-lg border border-cyan-300 dark:border-cyan-700 text-cyan-700 dark:text-cyan-300 hover:bg-cyan-50 dark:hover:bg-cyan-900/20 text-sm font-semibold flex items-center justify-center gap-1"
              title="Soal tetap, dipakai mengukur tingkat materi ini"
            >
              <Icon name="material-symbols:fact-check" class="w-4 h-4" />
              Asesmen Diagnostik ({{ activeDiagnosticTotal }} soal)
            </button>
          </div>

          <p
            v-if="activeDiagnosticPending"
            class="mt-3 text-xs text-amber-600 dark:text-amber-400 flex items-start gap-1"
          >
            <Icon name="material-symbols:lock" class="w-3.5 h-3.5 mt-0.5 shrink-0" />
            Selesaikan asesmen diagnostik bagian ini ({{ activeDiagnosticAnswered }}/{{ activeDiagnosticRequired }})
            sebelum lanjut ke bagian berikutnya.
          </p>

          <div class="flex items-center justify-between mt-8 pt-4 border-t border-gray-100 dark:border-gray-800">
            <button
              @click="goTo(-1)"
              :disabled="activeIndex <= 0"
              class="px-4 py-2 rounded-lg text-sm font-semibold bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-100 disabled:opacity-40 flex items-center gap-1"
            >
              <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
              Sebelumnya
            </button>
            <span class="text-xs text-gray-400">
              Bagian {{ activeIndex + 1 }} dari {{ sections.length }}
            </span>
            <button
              v-if="activeIndex < sections.length - 1"
              @click="goTo(1)"
              class="px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white flex items-center gap-1"
            >
              Berikutnya
              <Icon name="material-symbols:arrow-forward" class="w-4 h-4" />
            </button>
            <button
              v-else
              @click="requestFinish"
              class="px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white flex items-center gap-1"
            >
              <Icon name="material-symbols:check-circle" class="w-4 h-4" />
              Selesai!
            </button>
          </div>
        </template>
      </section>
    </div>

    <StudentSectionPracticeModal
      :open="practiceOpen"
      :material-id="route.params.id"
      :section-id="practiceSectionId"
      :section-title="practiceSectionTitle"
      @close="closePractice"
    />

    <StudentSectionDiagnosticModal
      :open="diagnosticOpen"
      :material-id="route.params.id"
      :section-id="diagnosticSectionId"
      :section-title="diagnosticSectionTitle"
      @close="closeDiagnostic"
    />

    <StudentDiagnosticGateModal
      :open="diagnosticGateOpen"
      :section-title="diagnosticGateTitle"
      :answered="activeDiagnosticAnswered"
      :required="activeDiagnosticRequired"
      @start="startGateDiagnostic"
      @dismiss="dismissGate"
    />
  </template>
</template>