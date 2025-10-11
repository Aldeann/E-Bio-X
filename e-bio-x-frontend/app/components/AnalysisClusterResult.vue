<template>
  <div>
    <div class="flex flex-wrap items-center gap-4 mb-4">
      <div>
        <label class="text-sm font-semibold text-green-700 dark:text-green-500 mr-2">Filter Cluster:</label>
        <select v-model="selectedCluster" class="border rounded dark:bg-gray-700 px-2 py-1 text-sm">
          <option value="Semua">Semua</option>
          <option v-for="c in clusterOptions" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>

      <div>
        <label class="text-sm font-semibold text-green-700 dark:text-green-500 mr-2">Urutkan:</label>
        <select v-model="sortBy" class="border rounded dark:bg-gray-700 px-2 py-1 text-sm">
          <option value="cluster">Cluster</option>
          <option value="score">Nilai</option>
          <option value="work_time">Waktu Pengerjaan</option>
        </select>
        <button @click="toggleDirection" class="ml-2">
          <Icon :name="sortDirection === 'asc' ? 'ph:arrow-up' : 'ph:arrow-down'" />
        </button>
      </div>
    </div>
    <ul class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <li v-for="(item, index) in filteredClusters" :key="index">
        <AnalysisStudentCard
          :nama="item.nama"
          :cluster="item.cluster"
          :score="item.score"
          :work_time="item.work_time" />
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const props = defineProps({
  clusters: Array,
});

const selectedCluster = ref("Semua");
const sortBy = ref("cluster");
const sortDirection = ref("asc");

const filteredClusters = computed(() => {
  let data = props.clusters;

  if (selectedCluster.value !== "Semua") {
    data = data.filter((item) => item.cluster === selectedCluster.value);
  }

  const direction = sortDirection.value === "asc" ? 1 : -1;

  if (sortBy.value === "score") {
    data = data.slice().sort((a, b) => (b.score - a.score) * direction);
  } else if (sortBy.value === "work_time") {
    data = data.slice().sort((a, b) => a.work_time.localeCompare(b.work_time) * direction);
  } else {
    data = data.slice().sort((a, b) => a.cluster.localeCompare(b.cluster) * direction);
  }

  return data;
});

const clusterOptions = computed(() => {
  const clusters = [...new Set(props.clusters.map((item) => item.cluster))];
  return clusters.sort((a, b) => a.localeCompare(b));
});

const toggleDirection = () => {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
}
</script>
