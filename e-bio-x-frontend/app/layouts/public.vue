<template>
  <div class="flex min-h-screen flex-col bg-canvas text-body transition-colors duration-300">
    <header class="bg-gradient-to-br from-brand-700 to-brand-900 text-white shadow">
      <div class="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
        <NuxtLink to="/" class="flex items-center gap-2 font-semibold">
          <Icon name="mdi:leaf" class="h-5 w-5" />
          E-Bio X
        </NuxtLink>

        <div class="flex items-center gap-2">
          <NuxtLink
            v-if="role"
            :to="`/${role}`"
            class="rounded-lg px-3 py-1.5 text-sm font-medium transition hover:bg-white/15">
            Dasbor
          </NuxtLink>
          <NuxtLink
            v-else
            to="/login"
            class="rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-brand-800 transition hover:bg-brand-50">
            Masuk
          </NuxtLink>
          <ToggleDark />
        </div>
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
      <slot />
    </main>

    <FooterComponet />
  </div>
</template>

<script setup>
const role = useCookie("role");
</script>
