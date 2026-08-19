<template>
  <div class="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-white font-mono text-sm tabular-nums"
    :class="timeLeft <= 60 ? 'bg-red-500 animate-pulse' : 'bg-gray-700'"
  >
    <Icon name="material-symbols:timer" class="w-4 h-4" />
    <span v-if="timeLeft === null">Tanpa batas</span>
    <span v-else>{{ displayTime }}</span>
  </div>
</template>

<script setup>
const props = defineProps({
  seconds: { type: Number, default: null },
});
const emit = defineEmits(["timeout"]);

const timeLeft = ref(props.seconds);
let timer = null;

const displayTime = computed(() => {
  const s = Math.max(0, timeLeft.value);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = m < 10 ? "0" + m : String(m);
  const ss = sec < 10 ? "0" + sec : String(sec);
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
});

const clear = () => {
  if (timer) clearInterval(timer);
  timer = null;
};

watch(
  () => props.seconds,
  (val) => {
    timeLeft.value = val;
    if (val === null) clear();
    else start();
  }
);

const start = () => {
  clear();
  timer = setInterval(() => {
    if (timeLeft.value === null) return;
    timeLeft.value = Math.max(0, timeLeft.value - 1);
    if (timeLeft.value === 0) {
      clear();
      emit("timeout");
    }
  }, 1000);
};

onMounted(() => {
  if (props.seconds !== null) start();
});

onBeforeUnmount(clear);
</script>