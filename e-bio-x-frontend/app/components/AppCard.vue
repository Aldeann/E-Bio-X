<template>
  <div class="rounded-xl border bg-surface transition"
       :class="[
         withShadow ? 'shadow-md shadow-slate-900/5 hover:shadow-slate-900/10' : 'shadow-sm',
         borderClass || 'border-line'
       ]">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  withShadow: { type: Boolean, default: false },
  borderClass: { type: String, default: '' },
});
</script>
