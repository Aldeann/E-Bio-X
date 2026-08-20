<template>
  <ForumIndex role="teacher" />
</template>

<script setup>
definePageMeta({ middleware: "auth", role: "teacher" });
</script>