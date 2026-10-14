<template>
  <div class="rounded-xl border bg-white dark:bg-gray-900 transition"
       :class="[
         withShadow ? 'shadow-md shadow-green-300/20 hover:shadow-green-300/40' : 'shadow-sm',
         borderClass || 'border-gray-200 dark:border-gray-700'
       ]">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  withShadow: { type: Boolean, default: false },
  borderClass: { type: String, default: '' },
});
</script>
