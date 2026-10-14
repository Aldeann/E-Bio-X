<template>
  <MaterialForm />
</template>

<script setup>
definePageMeta({
  layout: "teacher",

  middleware: "auth",
  role: "teacher",
});
</script>