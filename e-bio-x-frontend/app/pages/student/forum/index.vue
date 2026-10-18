<template>
  <ForumIndex role="student" />
</template>

<script setup>
definePageMeta({ layout: "student", middleware: "auth", role: "student" });
</script>