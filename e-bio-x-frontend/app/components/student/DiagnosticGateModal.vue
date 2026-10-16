<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto"
      @click.self="dismiss"
    >
      <div class="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-md my-4">
        <!-- header -->
        <div class="flex items-start justify-between gap-3 px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div class="min-w-0">
            <h3 class="font-semibold text-gray-800 dark:text-gray-100">Asesmen Diagnostik belum selesai</h3>
            <p class="text-xs text-gray-500 mt-0.5 truncate">{{ sectionTitle }}</p>
          </div>
          <button
            class="text-gray-400 hover:text-gray-600 shrink-0"
            @click="dismiss"
            aria-label="Tutup"
          >
            <Icon name="material-symbols:close" class="w-5 h-5" />
          </button>
        </div>

        <div class="px-5 py-4">
          <div class="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-3 flex gap-2">
            <Icon name="material-symbols:lock" class="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <p class="text-sm text-amber-800 dark:text-amber-200">
              Bagian ini punya asesmen diagnostik. Selesaikan dulu sebelum pindah
              ke bagian lain — asesmen ini tidak bisa dilewati.
            </p>
          </div>
          <p class="text-xs text-gray-600 dark:text-gray-300 mt-3">
            Progres bagian ini:
            <b>{{ answered }}</b> dari <b>{{ required }}</b> soal terjawab.
          </p>
          <p class="text-[11px] text-gray-400 mt-1">
            Soal tetap dan tidak menilai kamu; jawabanmu hanya dipakai guru untuk
            mengukur tingkat materi.
          </p>
        </div>

        <!-- footer: hanya aksi mengerjakan. "Tutup" membatalkan perpindahan,
             bukan melewati asesmen (murid tetap di bagian ini). -->
        <div class="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-200 dark:border-gray-700">
          <button
            class="border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 px-4 py-2 rounded-lg text-sm"
            @click="dismiss"
          >
            Tutup
          </button>
          <button
            class="bg-cyan-600 hover:bg-cyan-700 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-1"
            @click="start"
          >
            <Icon name="material-symbols:fact-check" class="w-4 h-4" />
            Kerjakan Asesmen Diagnostik
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  open: { type: Boolean, default: false },
  sectionTitle: { type: String, default: "" },
  answered: { type: Number, default: 0 },
  required: { type: Number, default: 0 },
});
const emit = defineEmits(["start", "dismiss"]);

const start = () => emit("start");
const dismiss = () => emit("dismiss");
</script>
