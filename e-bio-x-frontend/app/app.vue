<template>
  <UApp>
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>

<script setup>
useHead({
  htmlAttrs: { lang: "id" },
  titleTemplate: (title) => (title ? `${title} · E-Bio X` : "E-Bio X"),
  meta: [
    { name: "author", content: "Muhammad Ghazali Alhakim" },
    {
      name: "description",
      content:
        "E-Bio X — website pembelajaran biologi terintegrasi machine learning untuk peserta didik Fase E SMA. Dikembangkan di Universitas Negeri Padang.",
    },
  ],
});
</script>
