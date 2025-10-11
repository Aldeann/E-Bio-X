<script setup>
import { Pie } from "vue-chartjs";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

const props = defineProps({
  labels: Array,
  datasets: Array,
});

const options = {
  responsive: true,
  maintainAspectRatio: false
}
</script>

<template>
  <div class="w-full flex justify-center items-center">
    <div class="w-60 h-60">
      <Pie :data="{ labels, datasets }" :options="options" />
    </div>
  </div>
</template>
