<script setup>
import { computed } from "vue";

const props = defineProps({
  material: { type: Object, required: true },
});

const progress = computed(() => props.material.student_progress || null);
const percentage = computed(() => progress.value?.percentage || 0);
const finished = computed(() => !!progress.value?.finished);

const actionLabel = computed(() => {
  if (!progress.value || progress.value.completed === 0) return "Mulai Belajar";
  if (finished.value) return "Pelajari Kembali";
  return "Lanjutkan Belajar";
});

const actionIcon = computed(() => {
  if (!progress.value || progress.value.completed === 0) return "material-symbols:play-circle";
  if (finished.value) return "material-symbols:replay";
  return "material-symbols:arrow-forward";
});

const difficultyColor = computed(() =>
  (
    {
      mudah: "bg-green-100 text-green-700",
      sedang: "bg-amber-100 text-amber-700",
      sulit: "bg-red-100 text-red-700",
    }[props.material.difficulty] || "bg-gray-100 text-gray-600"
  )
);
</script>

<template>
  <NuxtLink
    :to="`/student/materials/${material.id}`"
    class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md hover:border-green-400 transition group"
  >
    <div class="h-28 relative">
      <img
        v-if="material.thumbnail_url"
        :src="material.thumbnail_url"
        :alt="material.title"
        loading="lazy"
        class="w-full h-full object-cover"
      />
      <div v-else class="w-full h-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white">
        <Icon name="material-symbols:menu-book" class="w-12 h-12" />
      </div>
      <span
        v-if="finished"
        class="absolute top-2 right-2 px-2 py-0.5 text-[10px] uppercase font-bold rounded-full bg-green-600 text-white"
      >
        Selesai
      </span>
    </div>

    <div class="p-4 flex flex-col flex-1">
      <div class="flex flex-wrap gap-1.5 mb-1.5">
        <span
          v-for="c in material.courses"
          :key="c"
          class="px-2 py-0.5 text-[10px] rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300"
        >
          {{ c }}
        </span>
      </div>

      <h2 class="font-semibold text-gray-800 dark:text-gray-100 group-hover:text-green-600 line-clamp-2">
        {{ material.title }}
      </h2>
      <p class="text-sm text-gray-500 mt-1 line-clamp-2 leading-relaxed">{{ material.description }}</p>

      <div class="mt-3 flex flex-wrap gap-2 text-xs">
        <span class="px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">
          {{ material.subject }}
        </span>
        <span class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
          Fase {{ material.phase }}{{ material.class_level ? " · " + material.class_level : "" }}
        </span>
        <span
          v-if="material.estimated_time"
          class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 inline-flex items-center gap-1"
        >
          <Icon name="material-symbols:schedule" class="w-3.5 h-3.5" />
          {{ material.estimated_time }}
        </span>
      </div>

      <div class="mt-3 text-xs text-gray-400 flex items-center gap-2">
        <Icon name="material-symbols:category" class="w-3.5 h-3.5" />
        <span class="truncate">Topik: {{ material.topic || "-" }}</span>
      </div>

      <div class="mt-4">
        <MaterialProgress v-if="progress" :percentage="percentage" />
        <p v-else class="text-xs text-gray-400 text-center py-1">Belum ada progress</p>
        <p class="text-[11px] text-gray-400 mt-1">
          {{ progress ? `${progress.completed} dari ${progress.total} bagian selesai` : "Belum pernah dibuka" }}
        </p>
      </div>

      <div class="mt-4 flex items-center justify-between">
        <span
          class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full"
          :class="difficultyColor"
        >
          {{ material.difficulty || "sedang" }}
        </span>
        <span
          class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition"
          :class="
            finished
              ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-200 group-hover:bg-gray-200 dark:group-hover:bg-gray-600'
              : 'bg-green-600 text-white group-hover:bg-green-700'
          "
        >
          <Icon :name="actionIcon" class="w-4 h-4" />
          {{ actionLabel }}
        </span>
      </div>
    </div>
  </NuxtLink>
</template>