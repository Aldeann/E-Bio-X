<template>
  <div class="flex min-h-screen dark:bg-gray-800 dark:text-white bg-gray-50 transition-colors duration-300">
    <StudentSidebar />
    <div class="flex-1 flex flex-col sm:ml-64">
      <main class="flex-1 px-4 py-6 max-w-7xl mx-auto w-full">
        <slot />
      </main>
      <FooterComponet />
    </div>
  </div>
</template>

<style scoped>
html, body {
  min-height: 100vh;
}
</style>
