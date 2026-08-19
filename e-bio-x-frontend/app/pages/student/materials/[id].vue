<script setup>
import { ref, computed, onMounted } from "vue";

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
const sidebarOpen = ref(false);
const showCompletion = ref(false);

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

const noteFor = (contentId) =>
  notes.value.find(
    (n) => n.section_id === activeSectionId.value && n.content_id === contentId
  ) || null;

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

const fetchDetail = async () => {
  loading.value = true;
  try {
    const detail = await $fetch(
      `${config.public.backend}/api/materials/${route.params.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    material.value = detail;
    await refetchLearningData(true);

    const listed = [];
    const last = studentState.value?.last_section_id;
    if (last && detail.sections.some((s) => s.id === last)) listed.push(last);
    const first = detail.sections.length > 0 ? detail.sections[0].id : null;
    activeSectionId.value = listed.length ? listed[0] : first;

    if (studentState.value?.completed && detail.sections.length > 0) {
      showCompletion.value = true;
      activeSectionId.value = studentState.value.last_section_id || detail.sections[0].id;
    }
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
        if (res.state.completed) showCompletion.value = true;
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
  setSection(id);
};

const setSection = (id) => {
  showCompletion.value = false;
  activeSectionId.value = id;
  sidebarOpen.value = false;
  persistSection(id);
  window.scrollTo({ top: 0, behavior: "smooth" });
};

const goTo = (offset) => {
  const next = activeIndex.value + offset;
  if (next >= 0 && next < sections.value.length) {
    setSection(sections.value[next].id);
  } else if (offset > 0 && activeIndex.value === sections.value.length - 1) {
    finishMaterial();
  }
};

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
  showCompletion.value = true;
  window.scrollTo({ top: 0, behavior: "smooth" });
};

const restartLearning = async () => {
  showCompletion.value = false;
  if (sections.value.length > 0) {
    activeSectionId.value = sections.value[0].id;
    persistSection(sections.value[0].id);
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

onMounted(fetchDetail);

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

      <button
        @click="sidebarOpen = !sidebarOpen"
        class="lg:hidden inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm font-semibold text-gray-700 dark:text-gray-200"
      >
        <Icon name="material-symbols:menu-book" class="w-4 h-4" />
        Daftar Bagian
      </button>
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
        />

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
              @click="finishMaterial"
              class="px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white flex items-center gap-1"
            >
              <Icon name="material-symbols:check-circle" class="w-4 h-4" />
              Selesai!
            </button>
          </div>
        </template>
      </section>
    </div>
  </template>
</template>