<template>
  <div class="text-center py-10 sm:py-14">
    <Icon v-if="icon" :name="icon" class="w-12 h-12 sm:w-14 sm:h-14 mx-auto mb-3"
          :class="iconClass || 'text-gray-300 dark:text-gray-500'" />
    <h4 v-if="title" class="text-base font-semibold text-gray-800 dark:text-gray-100">{{ title }}</h4>
    <p v-if="description" class="text-sm text-gray-500 mt-1">{{ description }}</p>
    <div v-if="$slots.default" class="mt-4 flex justify-center flex-wrap gap-2">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: '' },
  iconClass: { type: String, default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
});
</script>
