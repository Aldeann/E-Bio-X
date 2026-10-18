<template>
  <div class="container mx-auto px-4 py-6">
    <ForumCreate role="student" />
  </div>
</template>

<script setup>
definePageMeta({ layout: "student", middleware: "auth", role: "student" });
</script>