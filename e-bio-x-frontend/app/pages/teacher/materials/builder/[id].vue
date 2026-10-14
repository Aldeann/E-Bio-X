<template>
  <div>
    <MaterialBuilder :material-id="route.params.id" />
  </div>
</template>

<script setup>
const route = useRoute();

definePageMeta({
  layout: "teacher",

  middleware: "auth",
  role: "teacher",
});
</script>