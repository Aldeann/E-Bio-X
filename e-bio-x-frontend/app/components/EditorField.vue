<template>
  <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-5">
    <label class="block text-sm font-semibold mb-2">{{ label }}</label>
    <textarea
      v-model="model"
      class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm min-h-[72px]"
      :placeholder="placeholder"
    ></textarea>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: "" },
  label: { type: String, default: "" },
  placeholder: { type: String, default: "Tulis pembahasan..." },
  rows: { type: Number, default: 4 },
});
const emit = defineEmits(["update:modelValue"]);
const model = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});
</script>