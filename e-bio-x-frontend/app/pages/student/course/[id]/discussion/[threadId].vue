<template>
  <DiscussionThread :courseId="courseId" :threadId="threadId" />
</template>

<script setup>
definePageMeta({
  middleware: "auth",
  role: "student",
});

const route = useRoute();
const courseId = route.params.id;
const threadId = route.params.threadId;
</script>