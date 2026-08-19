<script setup>
import { computed } from "vue";

const props = defineProps({
  percentage: { type: Number, default: 0 },
  size: { type: String, default: "md" }, // sm | md
  showLabel: { type: Boolean, default: true },
});

const clamped = computed(() =>
  Math.max(0, Math.min(100, Number(props.percentage) || 0))
);

const barHeight = computed(() =>
  props.size === "sm" ? "h-1.5" : "h-2.5"
);

const labelClass = computed(() =>
  props.size === "sm" ? "text-[10px]" : "text-xs"
);
</script>

<template>
  <div class="w-full">
    <div class="flex items-center justify-between mb-1">
      <span v-if="showLabel" class="text-xs text-gray-500 dark:text-gray-400">Progress</span>
      <span
        v-if="showLabel"
        class="font-semibold"
        :class="[labelClass, clamped === 100 ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-300']"
      >
        {{ clamped }}%
      </span>
    </div>
    <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden" :class="barHeight">
      <div
        class="h-full bg-green-500 rounded-full transition-all duration-300"
        :style="{ width: clamped + '%' }"
      ></div>
    </div>
  </div>
</template>