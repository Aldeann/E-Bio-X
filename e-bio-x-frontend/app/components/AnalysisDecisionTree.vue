<template>
  <div class="bg-gray-50 dark:bg-gray-900 p-4 border rounded-xl">
    <h3 class="text-green-800 dark:text-green-500 text-lg font-semibold mb-2">Decision Tree Rules</h3>
    <pre class="text-sm text-gray-700 dark:text-gray-50 whitespace-pre-wrap">{{ props.rules }}</pre>
  </div>
</template>

<script setup>
const props = defineProps({
  rules: String,
});
</script>
