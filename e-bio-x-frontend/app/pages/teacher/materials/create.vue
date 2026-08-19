<template>
  <MaterialForm />
</template>

<script setup>
definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>