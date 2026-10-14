<template>
  <div>
    <ForumCreate role="teacher" />
  </div>
</template>

<script setup>
definePageMeta({ middleware: "auth", role: "teacher" });
</script>