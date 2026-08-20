<script setup>
import { ref, computed, onMounted } from "vue";

const route = useRoute();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const material = ref(null);
const loading = ref(true);
const activeSectionId = ref(null);

const sections = computed(() => material.value?.sections || []);
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
    toast.add({ title: "Materi tidak ditemukan.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const selectSection = (id) => (activeSectionId.value = id);

onMounted(fetchDetail);

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>

<template>
  <div v-if="loading" class="flex justify-center py-20 text-green-600">
    <Icon name="mdi:loading" class="w-10 h-10 animate-spin" />
  </div>

  <template v-else-if="material">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <NuxtLink
          :to="`/teacher/materials/builder/${material.id}`"
          class="text-sm text-green-600 hover:underline flex items-center gap-1 mb-1"
        >
          <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
          Kembali ke Builder
        </NuxtLink>
        <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">{{ material.title }}</h1>
        <p class="text-sm text-gray-500">{{ material.subject }} · Topik: {{ material.topic }}</p>
      </div>
      <span class="px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
        <span class="inline-flex items-center gap-1">
          <Icon name="material-symbols:visibility" class="w-4 h-4" />
          Preview sebagai Siswa
        </span>
      </span>
      <NuxtLink
        v-if="material.course_id"
        :to="`/teacher/forum/new?material_id=${material.id}&course_id=${material.course_id}&topic=${encodeURIComponent(material.title)}&category=${encodeURIComponent(material.topic || '')}`"
        class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-green-300 dark:border-green-700 text-sm font-semibold text-green-700 dark:text-green-300 hover:bg-green-50 dark:hover:bg-green-900/30 transition"
      >
        <Icon name="mdi:forum-outline" class="w-4 h-4" />
        Buat Forum dari Materi
      </NuxtLink>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6 items-start">
      <aside class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
        <h3 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 text-sm">
          Daftar Section
        </h3>
        <ul class="space-y-2">
          <li
            v-for="(section, index) in sections"
            :key="section.id"
            class="w-full"
          >
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

      <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-6 space-y-6">
        <template v-if="activeSection">
          <h2 class="text-lg font-bold text-green-700 dark:text-green-400">
            {{ activeSection.title }}
          </h2>
          <MaterialContentViewer
            v-for="content in activeSection.contents"
            :key="content.id"
            :block="content"
            :interactive="true"
          />
        </template>
      </section>
    </div>
  </template>
</template>