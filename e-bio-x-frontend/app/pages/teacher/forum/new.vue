<template>
  <div>
    <ForumCreate role="teacher" />
  </div>
</template>

<script setup>
definePageMeta({
  layout: "teacher",
 middleware: "auth", role: "teacher" });
</script>