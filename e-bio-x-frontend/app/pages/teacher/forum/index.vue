<template>
  <ForumIndex role="teacher" />
</template>

<script setup>
definePageMeta({
  layout: "teacher",
 middleware: "auth", role: "teacher" });
</script>