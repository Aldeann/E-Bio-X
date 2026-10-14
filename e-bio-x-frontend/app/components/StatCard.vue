<template>
  <AppCard :withShadow="withShadow">
    <div class="p-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span v-if="icon" class="w-8 h-8 rounded-lg flex items-center justify-center"
                :class="iconWrapClass || 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'">
            <Icon :name="icon" class="w-5 h-5" />
          </span>
          <div>
            <p class="text-xs text-gray-500">{{ label }}</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-gray-100 mt-0.5">{{ value }}</p>
          </div>
        </div>
        <span v-if="sub" class="text-xs text-gray-400">{{ sub }}</span>
      </div>
      <slot />
    </div>
  </AppCard>
</template>

<script setup>
defineProps({
  icon: { type: String, default: '' },
  label: { type: String, default: '' },
  value: { type: [String, Number], default: '' },
  sub: { type: String, default: '' },
  iconWrapClass: { type: String, default: '' },
  withShadow: { type: Boolean, default: false },
});
</script>
