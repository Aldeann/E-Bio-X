<script setup>
import { computed } from "vue";

const props = defineProps({
  title: { type: String, default: "Materi" },
  sections: { type: Array, default: () => [] },
  activeSectionId: { type: [Number, null], default: null },
  completedSectionIds: { type: Array, default: () => [] },
  bookmarks: { type: Array, default: () => [] },
  percentage: { type: Number, default: 0 },
});

const emit = defineEmits(["select"]);

const completedSet = computed(() => new Set(props.completedSectionIds));
const bookmarkedSet = computed(() => new Set(props.bookmarks.map((b) => b.section_id)));

const statusOf = (section) => {
  if (completedSet.value.has(section.id)) return "done";
  if (section.id === props.activeSectionId) return "active";
  return "pending";
};
</script>

<template>
  <div class="flex flex-col h-full">
    <h3 class="font-semibold text-gray-800 dark:text-gray-100 mb-3 text-sm flex items-center gap-1">
      <Icon name="simple-icons:bookstack" class="text-green-500" />
      {{ title }}
    </h3>

    <ul class="space-y-1.5 flex-1 overflow-y-auto">
      <li v-for="(section, index) in sections" :key="section.id">
        <button
          @click="emit('select', section.id)"
          class="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-left text-sm transition"
          :class="
            section.id === activeSectionId
              ? 'border-green-300 bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-200'
              : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:border-green-300'
          "
        >
          <span class="shrink-0 w-5 h-5 flex items-center justify-center">
            <Icon
              v-if="statusOf(section) === 'done'"
              name="material-symbols:task-alt"
              class="w-5 h-5 text-green-500"
            />
            <Icon
              v-else-if="statusOf(section) === 'active'"
              name="material-symbols:radio-button-checked"
              class="w-5 h-5 text-green-600"
            />
            <Icon
              v-else
              name="material-symbols:circle"
              class="w-4 h-4 text-gray-300 dark:text-gray-600"
            />
          </span>
          <span class="truncate font-medium">{{ index + 1 }}. {{ section.title }}</span>
          <Icon
            v-if="bookmarkedSet.has(section.id)"
            name="material-symbols:star-rounded"
            class="ml-auto w-4 h-4 shrink-0 text-amber-400"
          />
        </button>
      </li>
    </ul>

    <div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
      <MaterialProgress :percentage="percentage" size="sm" />
      <p class="text-[11px] text-gray-400 mt-1">{{ sections.length }} bagian · {{ percentage }}% selesai</p>
    </div>
  </div>
</template>