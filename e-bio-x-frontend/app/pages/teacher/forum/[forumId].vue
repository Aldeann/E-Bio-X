<template>
  <div>
    <ForumThread :forum-id="forumId" />
  </div>
</template>

<script setup>
definePageMeta({
  layout: "teacher",
 middleware: "auth", role: "teacher" });
const route = useRoute();
const forumId = route.params.forumId;
</script>