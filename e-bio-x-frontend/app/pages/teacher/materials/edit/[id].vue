<template>
  <MaterialForm :material-id="route.params.id" />
</template>

<script setup>
const route = useRoute();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>