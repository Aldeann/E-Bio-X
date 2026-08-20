<template>
  <div class="container mx-auto px-4 py-6">
    <ForumCreate role="teacher" />
  </div>
</template>

<script setup>
definePageMeta({ middleware: "auth", role: "teacher" });
</script>