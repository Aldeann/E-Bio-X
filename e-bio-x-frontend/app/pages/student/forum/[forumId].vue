<template>
  <div class="container mx-auto px-4 py-6">
    <ForumThread :forum-id="forumId" />
  </div>
</template>

<script setup>
definePageMeta({ middleware: "auth", role: "student" });
const route = useRoute();
const forumId = route.params.forumId;
</script>