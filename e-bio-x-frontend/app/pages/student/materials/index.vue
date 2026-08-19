<script setup>
import { ref, onMounted } from "vue";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const materials = ref([]);
const loading = ref(true);

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/materials`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    materials.value = res || [];
  } catch (e) {
    toast.add({ title: "Gagal memuat materi.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const difficultyColor = (v) =>
  ({ mudah: "bg-green-100 text-green-700", sedang: "bg-amber-100 text-amber-700", sulit: "bg-red-100 text-red-700" }[v] || "bg-gray-100 text-gray-600");

onMounted(fetchData);

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-green-700 dark:text-green-400 mb-1">
      Materi Pembelajaran
    </h1>
    <p class="text-sm text-gray-500 mb-6">Pilih materi untuk mulai belajar.</p>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 animate-pulse bg-white dark:bg-gray-900 h-48"></div>
    </div>

    <div v-else-if="materials.length === 0" class="text-center py-20 text-gray-400">
      <Icon name="material-symbols:auto-stories-outline" class="w-16 h-16 mx-auto mb-3" />
      <p>Belum ada materi yang dipublikasikan guru.</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <NuxtLink
        v-for="m in materials"
        :key="m.id"
        :to="`/student/materials/${m.id}`"
        class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md hover:border-green-400 transition group"
      >
        <div class="h-28 flex items-center justify-center">
          <img
            v-if="m.thumbnail_url"
            :src="m.thumbnail_url"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white">
            <Icon name="material-symbols:menu-book" class="w-12 h-12" />
          </div>
        </div>

        <div class="p-4 flex flex-col flex-1">
          <h2 class="font-semibold text-gray-800 dark:text-gray-100 group-hover:text-green-600 line-clamp-2">
            {{ m.title }}
          </h2>
          <p class="text-sm text-gray-500 mt-1 line-clamp-2">{{ m.description }}</p>

          <div class="mt-3 flex flex-wrap gap-2 text-xs">
            <span class="px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">
              {{ m.subject }}
            </span>
            <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
              Fase {{ m.phase }}{{ m.class_level ? " · " + m.class_level : "" }}
            </span>
            <span class="px-2 py-0.5 rounded-full" :class="difficultyColor(m.difficulty)">
              {{ m.difficulty }}
            </span>
          </div>

          <div class="mt-3 text-xs text-gray-400 flex items-center gap-3">
            <span class="inline-flex items-center gap-1">
              <Icon name="material-symbols:category" class="w-3.5 h-3.5" />
              Topik: {{ m.topic || "-" }}
            </span>
            <span v-if="m.estimated_time" class="inline-flex items-center gap-1">
              <Icon name="material-symbols:schedule" class="w-3.5 h-3.5" />
              {{ m.estimated_time }}
            </span>
          </div>
        </div>
      </NuxtLink>
    </div>
  </div>
</template>