<template>
  <MaterialForm :material-id="route.params.id" />
</template>

<script setup>
const route = useRoute();

definePageMeta({
  layout: "teacher",

  middleware: "auth",
  role: "teacher",
});
</script>