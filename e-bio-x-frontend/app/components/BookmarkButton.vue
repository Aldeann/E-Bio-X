<script setup>
defineProps({
  active: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
});

const emit = defineEmits(["toggle"]);
</script>

<template>
  <button
    @click="emit('toggle')"
    :disabled="loading"
    class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border text-sm font-medium transition disabled:opacity-60"
    :class="
      active
        ? 'bg-amber-50 dark:bg-amber-900/40 border-amber-400 text-amber-600 dark:text-amber-300'
        : 'bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-amber-400 hover:text-amber-500'
    "
  >
    <Icon
      :name="active ? 'material-symbols:star-rounded' : 'material-symbols:star-outline-rounded'"
      class="w-4 h-4"
    />
    {{ active ? "Tersimpan" : "Simpan" }}
  </button>
</template>