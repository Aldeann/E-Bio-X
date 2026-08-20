<template>
  <ForumIndex role="student" />
</template>

<script setup>
definePageMeta({ middleware: "auth", role: "student" });
</script>