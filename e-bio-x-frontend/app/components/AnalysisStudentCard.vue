<template>
  <div class="flex flex-row items-center justify-between p-3 border border-green-200 rounded shadow-sm bg-white dark:bg-gray-800">
    <div class="w-1/2 flex items-center gap-2">
      <Icon name="material-symbols:account-circle" size="20" class="text-green-600 dark:text-green-500" />
      <span class="font-semibold">{{ props.nama }}</span>
    </div>
    <div class="w-1/2 text-sm mt-1 text-gray-700 dark:text-gray-200 flex flex-col">
      <div class="mb-2">
        <Icon name="material-symbols:label-important" size="16" class="text-green-500 mr-1" />
        <b>{{ props.cluster }}</b>
      </div>
      <div class="mb-2">
        <Icon name="material-symbols:star-rounded" size="16" class="text-yellow-500 mr-1" />
        Nilai: {{ props.score.toFixed(2) }}
      </div>
      <div class="mb-2">
        <Icon name="material-symbols:schedule" size="16" class="text-blue-500 mr-1" />
        {{ props.work_time }}
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  nama: String,
  cluster: String,
  score: Number,
  work_time: String,
});
</script>
