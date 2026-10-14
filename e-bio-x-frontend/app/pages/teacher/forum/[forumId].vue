<template>
  <div>
    <ForumThread :forum-id="forumId" />
  </div>
</template>

<script setup>
definePageMeta({ middleware: "auth", role: "teacher" });
const route = useRoute();
const forumId = route.params.forumId;
</script>