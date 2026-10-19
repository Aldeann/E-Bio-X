<template>
  <div>
    <PageHeader
      title="Analisis Tingkat Soal Otomatis"
      subtitle="Tingkat soal diukur dari performa siswa yang benar-benar mengerjakan (bukan ditebak dari teks soal). Label guru tetap ditampilkan berdampingan dan tidak pernah ditimpa."
    />

    <div v-if="loading" class="text-center py-16 text-green-600">
      <Icon name="mdi:loading" class="w-10 h-10 animate-spin mx-auto" />
    </div>

    <template v-else-if="data">
      <!-- aturan hitung, ikut ditampilkan supaya angka bisa ditelusuri -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <p class="text-xs text-gray-500">Sampel minimum</p>
          <p class="text-lg font-semibold">{{ rules.min_sample }} siswa</p>
          <p class="text-[11px] text-gray-400">di bawah ini: belum cukup data</p>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <p class="text-xs text-gray-500">Batas tingkat</p>
          <p class="text-sm font-medium mt-1">
            ≥ {{ rules.p_easy }} mudah · &lt; {{ rules.p_hard }} sulit
          </p>
          <p class="text-[11px] text-gray-400">sisanya sedang</p>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <p class="text-xs text-gray-500">Selang kepercayaan</p>
          <p class="text-lg font-semibold">{{ rules.margin_z }}σ (95%)</p>
          <p class="text-[11px] text-gray-400">ditandai "dekat batas" bila memotong garis</p>
        </div>
        <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
          <p class="text-xs text-gray-500">Saat menilai satu siswa</p>
          <p class="text-sm font-medium mt-1">Leave-one-out</p>
          <p class="text-[11px] text-gray-400">jawabannya sendiri dikeluarkan</p>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3 mb-4 text-sm">
        <span class="text-gray-600 dark:text-gray-300">
          {{ data.counts.total }} soal dianalisis
        </span>
        <span class="px-2 py-0.5 rounded bg-green-100 text-green-700 text-xs">
          {{ data.counts.observed_ready }} siap diukur
        </span>
        <span class="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 text-xs">
          {{ data.counts.observed_insufficient }} belum cukup data
        </span>
        <div class="ml-auto flex gap-1 text-xs">
          <button
            v-for="f in filters"
            :key="f.key"
            class="px-2.5 py-1 rounded border"
            :class="filter === f.key
              ? 'bg-green-600 border-green-600 text-white'
              : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300'"
            @click="filter = f.key"
          >
            {{ f.label }}
          </button>
        </div>
      </div>

      <div v-if="!data.items.length" class="text-center py-12 text-gray-500 text-sm">
        Belum ada soal latihan pada materi Anda.
      </div>

      <div v-else-if="!filtered.length" class="text-center py-12 text-gray-500 text-sm">
        Tidak ada soal pada filter ini.
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="(it, idx) in filtered"
          :key="it.question_id + '-' + idx"
          class="rounded-lg border border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-900"
        >
          <div class="flex flex-wrap items-center gap-2 mb-2 text-xs">
            <span class="px-1.5 py-0.5 rounded font-medium bg-indigo-100 text-indigo-700">
              Soal bank
            </span>
            <span class="text-gray-500">{{ it.material_title }} · {{ it.section_title }}</span>
            <span
              class="px-1.5 py-0.5 rounded"
              :class="it.status === 'APPROVED'
                ? 'bg-green-50 text-green-700'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-500'"
            >{{ it.status }}</span>
          </div>

          <!-- Tanpa fallback "(soal interaktif)": kanal itu sudah dihapus, jadi
               teks soal selalu ada dan fallback hanya menutupi kesalahan data. -->
          <p class="text-sm text-gray-800 dark:text-gray-100 mb-3">
            {{ it.question_text }}
          </p>

          <div class="grid sm:grid-cols-2 gap-2 text-xs">
            <!-- label guru / deklarasi -->
            <div class="rounded border border-gray-200 dark:border-gray-700 p-2">
              <p class="text-gray-500 mb-0.5">Label guru (deklarasi)</p>
              <p class="font-medium text-gray-800 dark:text-gray-100">
                {{ it.declared_label || 'tidak ditulis' }}
              </p>
            </div>

            <!-- label terukur -->
            <div
              class="rounded border p-2"
              :class="ready(it)
                ? 'border-green-200 bg-green-50 dark:bg-green-900/20'
                : 'border-gray-200 dark:border-gray-700'"
            >
              <p class="text-gray-500 mb-0.5">Terukur dari performa</p>
              <template v-if="ready(it)">
                <p class="font-medium text-green-700 dark:text-green-400">
                  {{ labelId(it.observed.label) }}
                  <span class="font-normal text-gray-500">
                    · p={{ Math.round(it.observed.p * 100) }}% · n={{ it.observed.n }}
                  </span>
                </p>
                <p class="text-gray-500 mt-0.5">
                  ±{{ Math.round(it.observed.margin * 100) }} poin
                  <span v-if="it.observed.near_boundary" class="text-amber-600"> · dekat batas</span>
                </p>
              </template>
              <p v-else class="font-medium text-gray-500">
                belum cukup data
                <span v-if="it.observed.n" class="font-normal">(n={{ it.observed.n }})</span>
              </p>
              <p v-if="it.observed_note" class="text-[11px] text-gray-400 mt-1">
                {{ it.observed_note }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <p class="text-[11px] text-gray-400 mt-6">
        {{ rules.method }}
      </p>
    </template>

    <div v-else class="text-center py-12 text-gray-500 text-sm">
      Data tidak tersedia.
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const data = ref(null);
const loading = ref(true);
const filter = ref("all");
const filters = [
  { key: "all", label: "Semua" },
  { key: "ready", label: "Siap diukur" },
  { key: "insufficient", label: "Belum cukup data" },
];

const LABEL_ID = { easy: "mudah", medium: "sedang", hard: "sulit" };
const labelId = (v) => LABEL_ID[v] || v || "";

const rules = computed(() => data.value?.rules || {
  min_sample: 20, p_easy: 0.7, p_hard: 0.4, margin_z: 1.96, method: "",
});

const ready = (it) => it?.observed?.status === "READY";

const filtered = computed(() => {
  const items = data.value?.items || [];
  if (filter.value === "ready") return items.filter(ready);
  if (filter.value === "insufficient") return items.filter((it) => !ready(it));
  return items;
});

const load = async () => {
  loading.value = true;
  try {
    data.value = await $fetch(`${config.public.backend}/api/teacher/practice/difficulty`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal memuat analisis tingkat", color: "red" });
  } finally {
    loading.value = false;
  }
};

load();

definePageMeta({
  layout: "teacher",

  middleware: "auth",
  role: "teacher",
});
</script>
