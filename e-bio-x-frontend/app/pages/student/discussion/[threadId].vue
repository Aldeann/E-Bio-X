<template>
  <DiscussionThread :threadId="threadId" />
</template>

<script setup>
definePageMeta({
  middleware: "auth",
  role: "student",
});

const route = useRoute();
const threadId = route.params.threadId;
</script>