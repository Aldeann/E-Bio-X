<template>
  <div>
    <MaterialBuilder :material-id="route.params.id" />
  </div>
</template>

<script setup>
const route = useRoute();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>