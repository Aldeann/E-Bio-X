<script setup>
import { ref, computed } from "vue";

// Diagram interaktif berlabel.
// - Guru: points = [{ id, x, y, label }] → menampilkan titik beserta labelnya.
// - Siswa: points = [{ id, x, y }] + labels (acak) → klik titik lalu pilih label,
//   lalu kirim pemetaan ke server untuk dinilai.
const props = defineProps({
  diagram: { type: Object, required: true },
  interactive: { type: Boolean, default: false },
  externalResult: { type: Object, default: null }, // { correct, explanation } dari backend
});

const emit = defineEmits(["submit"]);

const points = computed(() => props.diagram?.points || []);
const labels = computed(() => props.diagram?.labels || []);
// Mode guru/preview: data berisi kunci jawaban (label ada di tiap titik).
const hasKey = computed(() => points.value.length > 0 && !!points.value[0].label);

const assignments = ref({});
const activePointId = ref(null);

const resultShown = computed(() => !!props.externalResult);
const isCorrect = computed(() => !!props.externalResult?.correct);
const explanation = computed(() => props.externalResult?.explanation || "");

const allAssigned = computed(
  () => points.value.length > 0 && points.value.every((p) => assignments.value[p.id] !== undefined)
);

const pointStyle = (p) => ({ left: `${p.x || 0}%`, top: `${p.y || 0}%` });

const selectPoint = (pid) => {
  if (!props.interactive || resultShown.value) return;
  activePointId.value = pid;
};

const clearAssignment = (pid) => {
  if (!props.interactive || resultShown.value) return;
  delete assignments.value[pid];
  activePointId.value = pid;
};

const assignLabel = (label) => {
  if (!props.interactive || !activePointId.value || resultShown.value) return;
  assignments.value[activePointId.value] = label;
  const next = points.value.find((p) => assignments.value[p.id] === undefined);
  activePointId.value = next ? next.id : null;
};

const labelClass = (l) => {
  const base =
    "px-3 py-1.5 rounded-lg border text-sm font-medium transition shrink-0";
  if (!props.interactive || resultShown.value)
    return `${base} bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400 cursor-default`;
  const used = Object.values(assignments.value);
  const isActiveLabel = assignments.value[activePointId.value] === l;
  if (used.includes(l) && !isActiveLabel)
    return `${base} bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-300 cursor-not-allowed`;
  return `${base} bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-600 hover:border-green-400 cursor-pointer text-gray-800 dark:text-gray-100`;
};

const pointClass = (p, idx) => {
  const base =
    "absolute -translate-x-1/2 -translate-y-1/2 w-7 h-7 rounded-full border-2 flex items-center justify-center text-xs font-bold z-10 transition";
  if (resultShown.value) {
    // Server hanya menilai keseluruhan diagram (per-point benar/salah tidak
    // diekspos), jadi semua penanda mengikuti status akhir.
    return `${base} ${
      isCorrect.value
        ? "bg-green-500 border-white text-white shadow"
        : "bg-red-500 border-white text-white shadow"
    }`;
  }
  if (hasKey.value) {
    return `${base} bg-green-600 border-white text-white`;
  }
  if (assignments.value[p.id] !== undefined) {
    return `${base} bg-green-500 border-white text-white cursor-pointer`;
  }
  if (activePointId.value === p.id) {
    return `${base} bg-white border-green-500 text-green-600 ring-2 ring-green-300 cursor-pointer`;
  }
  return `${base} bg-gray-200 dark:bg-gray-700 border-gray-400 dark:border-gray-500 text-gray-700 dark:text-gray-200 cursor-pointer`;
};

const submitDiagram = () => {
  if (!props.interactive || resultShown.value || !allAssigned.value) return;
  emit("submit", { ...assignments.value });
};
</script>

<template>
  <div class="space-y-3">
    <p v-if="diagram.title" class="font-semibold text-gray-800 dark:text-gray-100">
      {{ diagram.title }}
    </p>

    <p
      v-if="!diagram.url"
      class="text-sm text-gray-400 italic"
    >
      (Gambar diagram belum diunggah)
    </p>

    <div v-else class="space-y-3">
      <div
        class="relative rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 inline-block max-w-full"
      >
        <img
          :src="diagram.url"
          :alt="diagram.title || 'Diagram'"
          class="max-w-full h-auto block"
          draggable="false"
        />
        <button
          v-for="(p, idx) in points"
          :key="p.id"
          type="button"
          :class="pointClass(p, idx)"
          :style="pointStyle(p)"
          :title="hasKey && p.label ? `${idx + 1}. ${p.label}` : `Titik ${idx + 1}`"
          @click="selectPoint(p.id)"
        >
          <template v-if="resultShown">
            <Icon
              v-if="isCorrect"
              name="material-symbols:check"
              class="w-4 h-4"
            />
            <Icon v-else name="material-symbols:close" class="w-4 h-4" />
          </template>
          <template v-else>{{ idx + 1 }}</template>
        </button>
      </div>

      <!-- Mode siswa: pemilihan label per titik -->
      <template v-if="interactive && !hasKey">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          <template v-if="activePointId">
            Klik label yang sesuai untuk titik
            <span class="font-semibold text-green-600">
              {{
                points.findIndex((p) => p.id === activePointId) + 1
              }}
            </span>
            .
          </template>
          <template v-else>Klik sebuah titik pada gambar untuk mulai menjawab.</template>
        </p>
        <div v-if="assignments && points.some((p) => assignments[p.id] !== undefined)" class="flex flex-wrap gap-2">
          <span
            v-for="p in points.filter((p) => assignments[p.id] !== undefined)"
            :key="p.id"
            class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-50 dark:bg-green-900/40 text-xs font-semibold text-green-700 dark:text-green-300"
          >
            {{ points.findIndex((x) => x.id === p.id) + 1 }}: {{ assignments[p.id] }}
            <button
              v-if="!resultShown"
              @click="clearAssignment(p.id)"
              class="text-red-500 hover:text-red-700"
              title="Hapus jawaban titik ini"
            >
              <Icon name="material-symbols:close" class="w-3.5 h-3.5" />
            </button>
          </span>
        </div>

        <div v-if="!resultShown" class="flex flex-wrap gap-2">
          <button
            v-for="l in labels"
            :key="l"
            :class="labelClass(l)"
            @click="assignLabel(l)"
          >
            {{ l }}
          </button>
        </div>

        <div v-if="!resultShown && allAssigned" class="pt-1">
          <button
            @click="submitDiagram"
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-semibold"
          >
            Cek Jawaban
          </button>
        </div>
      </template>

      <!-- Mode guru / preview: daftar titik beserta label -->
      <template v-else-if="hasKey">
        <ul class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-sm">
          <li
            v-for="(p, idx) in points"
            :key="p.id"
            class="flex items-center gap-2 text-gray-700 dark:text-gray-200"
          >
            <span
              class="w-6 h-6 shrink-0 rounded-full bg-green-600 text-white text-xs font-bold flex items-center justify-center"
            >
              {{ idx + 1 }}
            </span>
            <span>{{ p.label }}</span>
          </li>
        </ul>
      </template>

      <p v-else class="text-sm text-gray-400 italic">
        Diagram ini belum memiliki titik label.
      </p>

      <!-- Hasil penilaian -->
      <div
        v-if="resultShown"
        class="rounded-lg p-4 text-sm border"
        :class="
          isCorrect
            ? 'bg-green-50 dark:bg-green-900/40 border-green-300 text-green-800 dark:text-green-100'
            : 'bg-red-50 dark:bg-red-900/40 border-red-300 text-red-800 dark:text-red-100'
        "
      >
        <p class="font-semibold flex items-center gap-1">
          <Icon
            :name="isCorrect ? 'material-symbols:check-circle' : 'material-symbols:error'"
            class="w-5 h-5"
          />
          {{ isCorrect ? "Semua label benar!" : "Masih ada label yang belum tepat." }}
        </p>
        <p v-if="explanation" class="mt-1">{{ explanation }}</p>
      </div>
    </div>
  </div>
</template>