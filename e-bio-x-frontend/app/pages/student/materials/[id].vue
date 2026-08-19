<script setup>
import { ref, computed, onMounted, watch } from "vue";

const route = useRoute();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const material = ref(null);
const loading = ref(true);
const activeSectionId = ref(null);

const sections = computed(() => material.value?.sections || []);
const activeIndex = computed(() =>
  sections.value.findIndex((s) => s.id === activeSectionId.value)
);
const activeSection = computed(
  () => sections.value.find((s) => s.id === activeSectionId.value) || null
);

const fetchDetail = async () => {
  loading.value = true;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/materials/${route.params.id}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    material.value = res;
    if (res.sections.length > 0) activeSectionId.value = res.sections[0].id;
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Materi tidak dapat diakses.";
    toast.add({ title: msg, color: "red" });
  } finally {
    loading.value = false;
  }
};

const recordProgress = async (sectionId) => {
  if (!sectionId) return;
  try {
    await $fetch(`${config.public.backend}/api/materials/${route.params.id}/progress`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { section_id: sectionId },
    });
  } catch (e) {
    // abaikan error progress, jangan ganggu pengalaman belajar
  }
};

const selectSection = (id) => {
  activeSectionId.value = id;
};

watch(activeSectionId, (id) => {
  if (id) recordProgress(id);
});

const goTo = (offset) => {
  const next = activeIndex.value + offset;
  if (next >= 0 && next < sections.value.length) {
    activeSectionId.value = sections.value[next].id;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
};

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
    <div class="mb-4">
      <NuxtLink
        to="/student/materials"
        class="text-sm text-green-600 hover:underline flex items-center gap-1 mb-1"
      >
        <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
        Kembali ke Materi
      </NuxtLink>
      <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ material.title }}</h1>
      <p class="text-sm text-gray-500">
        {{ material.subject }} · Topik: {{ material.topic }} · Fase {{ material.phase }}
        <span v-if="material.estimated_time" class="inline-flex items-center gap-1 ml-1">
          · {{ material.estimated_time }}
        </span>
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

    <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6 items-start">
      <aside class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
        <h3 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 text-sm">
          Daftar Section ({{ sections.length }})
        </h3>
        <ul class="space-y-2">
          <li v-for="(section, index) in sections" :key="section.id">
            <button
              @click="selectSection(section.id)"
              class="w-full flex items-center gap-2 px-3 py-2 rounded-lg border text-left text-sm transition"
              :class="
                activeSectionId === section.id
                  ? 'border-green-300 bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-200'
                  : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300'
              "
            >
              <span
                class="w-7 h-7 shrink-0 rounded-full text-white text-xs font-bold flex items-center justify-center"
                :class="activeSectionId === section.id ? 'bg-green-600' : 'bg-gray-400'"
              >
                {{ index + 1 }}
              </span>
              <span class="truncate">{{ section.title }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6">
        <template v-if="activeSection">
          <h2 class="text-lg font-bold text-green-700 dark:text-green-400 mb-4">
            {{ activeSection.title }}
          </h2>

          <div class="space-y-6">
            <MaterialContentViewer
              v-for="content in activeSection.contents"
              :key="content.id"
              :block="content"
              :interactive="true"
            />
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
              Section {{ activeIndex + 1 }} dari {{ sections.length }}
            </span>
            <button
              v-if="activeIndex < sections.length - 1"
              @click="goTo(1)"
              class="px-4 py-2 rounded-lg text-sm font-semibold bg-green-600 hover:bg-green-700 text-white flex items-center gap-1"
            >
              Berikutnya
              <Icon name="material-symbols:arrow-forward" class="w-4 h-4" />
            </button>
            <span
              v-else
              class="px-4 py-2 rounded-lg text-sm font-semibold bg-green-100 text-green-700 flex items-center gap-1"
            >
              <Icon name="material-symbols:check-circle" class="w-4 h-4" />
              Selesai!
            </span>
          </div>
        </template>
      </section>
    </div>
  </template>
</template>