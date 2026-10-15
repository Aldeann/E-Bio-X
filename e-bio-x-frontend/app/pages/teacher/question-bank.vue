<template>
  <div>
    <PageHeader
      title="Bank Soal"
      subtitle="Kumpulan soal yang bisa digunakan kembali di kuis mana pun."
    >
      <button
        class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition flex items-center gap-1 shadow-md shadow-green-300/50"
        @click="openForm()"
      >
        <Icon name="material-symbols:add" class="w-5 h-5" /> Tambah Soal
      </button>
    </PageHeader>

    <!-- Filter -->
    <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-2xl shadow-md p-4 mb-4">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-3">
        <div class="relative">
          <Icon
            name="material-symbols:search"
            class="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
          />
          <input
            v-model="filters.q"
            type="text"
            placeholder="Cari pertanyaan..."
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg pl-10 pr-3 py-2 text-sm focus:ring-2 focus:ring-green-500"
          />
        </div>
        <select v-model="filters.type" class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500">
          <option value="">Semua tipe</option>
          <option value="multiple_choice">Pilihan Ganda</option>
          <option value="true_false">Benar/Salah</option>
        </select>
        <select v-model="filters.difficulty" class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500">
          <option value="">Semua kesulitan</option>
          <option value="easy">Mudah</option>
          <option value="medium">Sedang</option>
          <option value="hard">Sulit</option>
          <option value="unclassified">Belum ditentukan</option>
        </select>
        <select v-model="filters.status" class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500">
          <option value="">Semua status</option>
          <option value="APPROVED">Disetujui</option>
          <option value="DRAFT">Menunggu review</option>
          <option value="REJECTED">Ditolak</option>
        </select>
        <select v-model="filters.purpose" class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500">
          <option value="">Semua jenis</option>
          <option value="practice">Latihan (adaptif)</option>
          <option value="diagnostic">Diagnostik (level materi)</option>
        </select>
      </div>
      <div
        v-if="hasActiveFilter && !loading && items.length > 0"
        class="mt-3 flex items-center justify-between border-t border-gray-100 dark:border-gray-800 pt-3"
      >
        <span class="text-xs text-gray-500">{{ items.length }} soal ditemukan</span>
        <button
          class="text-xs text-green-600 hover:text-green-700 font-medium underline underline-offset-2"
          @click="resetFilters"
        >
          Reset filter
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat bank soal...</div>

    <div v-else-if="items.length === 0 && hasActiveFilter" class="text-center py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-600 rounded-2xl">
      <Icon name="material-symbols:search-off" class="w-14 h-14 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500 mb-3">Tidak ada soal yang cocok dengan filter.</p>
      <button
        class="text-sm text-green-600 hover:text-green-700 font-medium underline underline-offset-2"
        @click="resetFilters"
      >
        Reset filter
      </button>
    </div>

    <div v-else-if="items.length === 0" class="text-center py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-600 rounded-2xl">
      <Icon name="material-symbols:database" class="w-14 h-14 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">Belum ada soal bank.</p>
      <button
        class="mt-3 bg-green-600 hover:bg-green-700 text-white px-4 py-1.5 rounded-lg text-sm transition"
        @click="openForm()"
      >
        Tambah soal pertama
      </button>
    </div>

    <template v-else>
      <!-- Toolbar: info jumlah + pilihan soal per slide -->
      <div class="flex flex-wrap items-center justify-between gap-3 mb-2 px-1">
        <p class="text-xs text-gray-500">
          Menampilkan
          <span class="font-semibold text-gray-700 dark:text-gray-200">{{ rangeStart }}–{{ rangeEnd }}</span>
          dari <span class="font-semibold text-gray-700 dark:text-gray-200">{{ items.length }}</span> soal
        </p>
        <label class="flex items-center gap-2 text-xs text-gray-500">
          Soal per slide
          <select
            v-model.number="pageSize"
            class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 text-xs focus:ring-2 focus:ring-green-500"
          >
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </label>
      </div>

      <!-- Progress slide -->
      <div class="flex items-center gap-3 mb-4 px-1">
        <span class="text-xs font-semibold text-green-700 dark:text-green-400 whitespace-nowrap">
          Slide {{ page }} / {{ totalPages }}
        </span>
        <div class="flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
          <div
            class="h-full rounded-full bg-gradient-to-r from-emerald-400 to-green-600 transition-all duration-300"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <span class="hidden sm:flex items-center gap-1 text-xs text-gray-400 whitespace-nowrap">
          <Icon name="material-symbols:keyboard-arrow-left" class="w-4 h-4" />
          <Icon name="material-symbols:keyboard-arrow-right" class="w-4 h-4" /> untuk pindah slide
        </span>
      </div>

      <!-- Isi slide -->
      <div ref="slideTop" aria-live="polite">
        <Transition :name="'slide-' + direction" mode="out-in">
          <div
            :key="page"
            class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start"
            @touchstart.passive="onTouchStart"
            @touchend.passive="onTouchEnd"
          >
            <article
              v-for="(b, i) in pagedItems"
              :key="b.id"
              class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-sm overflow-hidden flex flex-col"
            >
              <div class="h-1" :class="accentClass(b.status)"></div>
              <div class="p-4 flex-1 flex flex-col">
                <div class="flex items-start justify-between gap-2">
                  <div class="flex items-start gap-2 min-w-0">
                    <span class="shrink-0 w-7 h-7 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 text-xs font-bold flex items-center justify-center">
                      {{ (page - 1) * pageSize + i + 1 }}
                    </span>
                    <div class="flex flex-wrap items-center gap-1.5 pt-0.5">
                      <span class="text-[11px] px-2 py-0.5 rounded-full" :class="statusClass(b.status)">
                        {{ statusLabel(b.status) }}
                      </span>
                      <span
                        v-if="b.source === 'ai'"
                        class="text-[11px] px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-400"
                      >
                        Draf AI
                      </span>
                      <span class="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400">
                        {{ typeLabel(b.question_type) }}
                      </span>
                      <span class="text-[11px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400">
                        {{ difficultyLabel(b.difficulty) }}
                      </span>
                      <span
                        v-if="b.purpose === 'diagnostic'"
                        class="text-[11px] px-2 py-0.5 rounded-full bg-cyan-100 dark:bg-cyan-900 text-cyan-700 dark:text-cyan-300"
                        title="Soal diagnostik: urutan tetap, dipakai mengukur tingkat materi"
                      >
                        Diagnostik
                      </span>
                      <span v-if="b.topic" class="text-[11px] px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-400">
                        {{ b.topic }}
                      </span>
                      <span
                        v-if="(b.times_used || 0) > 0"
                        class="text-[11px] px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400"
                        :title="'Soal ini sudah dipakai di ' + b.times_used + ' tempat'"
                      >
                        Dipakai {{ b.times_used }}×
                      </span>
                      <span class="text-[11px] text-gray-500">{{ b.points }} poin</span>
                    </div>
                  </div>
                  <div class="flex gap-0.5 shrink-0">
                    <button
                      class="p-1.5 rounded-lg text-amber-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
                      title="Generate Pembahasan AI"
                      aria-label="Generate pembahasan AI"
                      :disabled="generatingId === b.id"
                      @click="generateExplanation(b)"
                    >
                      <Icon
                        :name="generatingId === b.id ? 'mdi:loading' : 'material-symbols:auto-awesome'"
                        class="w-4 h-4"
                        :class="generatingId === b.id ? 'animate-spin' : ''"
                      />
                    </button>
                    <button
                      class="p-1.5 rounded-lg text-blue-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-gray-800 transition"
                      title="Edit"
                      aria-label="Edit soal"
                      @click="openForm(b)"
                    >
                      <Icon name="material-symbols:edit" class="w-4 h-4" />
                    </button>
                    <button
                      class="p-1.5 rounded-lg text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-gray-800 transition"
                      title="Hapus"
                      aria-label="Hapus soal"
                      @click="remove(b)"
                    >
                      <Icon name="material-symbols:delete" class="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <p class="mt-3 font-semibold leading-snug">{{ b.question_text }}</p>

                <img
                  v-if="b.image_url"
                  :src="b.image_url"
                  alt="Gambar soal"
                  class="mt-2 max-h-40 rounded-xl border border-gray-200 dark:border-gray-700 self-start"
                />

                <ul class="mt-3 space-y-1.5 text-sm">
                  <li
                    v-for="(o, oi) in b.options"
                    :key="o.option_id ?? oi"
                    class="flex items-start gap-2 rounded-lg px-2.5 py-1.5 border"
                    :class="
                      o.is_correct
                        ? 'border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 font-medium'
                        : 'border-gray-100 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-800/40 text-gray-600 dark:text-gray-300'
                    "
                  >
                    <Icon
                      :name="o.is_correct ? 'material-symbols:check-circle' : 'material-symbols:radio-button-unchecked'"
                      class="w-4 h-4 mt-0.5 shrink-0"
                    />
                    <span>{{ o.option_text }}</span>
                  </li>
                </ul>

                <button
                  v-if="b.explanation || b.misconception"
                  type="button"
                  class="mt-3 self-start inline-flex items-center gap-1 text-xs font-medium text-green-600 hover:text-green-700 transition"
                  @click="toggleExpanded(b.id)"
                >
                  <Icon
                    :name="isExpanded(b.id) ? 'material-symbols:expand-less' : 'material-symbols:expand-more'"
                    class="w-4 h-4"
                  />
                  {{ isExpanded(b.id) ? 'Sembunyikan pembahasan' : 'Lihat pembahasan' }}
                </button>

                <div v-if="isExpanded(b.id)" class="mt-2 space-y-2 text-sm">
                  <p v-if="b.explanation" class="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 px-3 py-2 text-green-800 dark:text-green-300">
                    <span class="font-semibold">Pembahasan: </span>{{ b.explanation }}
                  </p>
                  <p v-if="b.misconception" class="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-amber-800 dark:text-amber-300">
                    <span class="font-semibold">Miskonsepsi: </span>{{ b.misconception }}
                  </p>
                </div>

                <p v-if="b.section_title" class="mt-3 text-xs text-blue-600 dark:text-blue-400">
                  {{ b.purpose === "diagnostic" ? "Asesmen diagnostik untuk bagian: " : "Latihan untuk bagian: " }}{{ b.section_title }}
                </p>
              </div>
            </article>
          </div>
        </Transition>
      </div>

      <!-- Navigasi slide -->
      <div class="flex items-center justify-between gap-3 mt-5">
        <button
          class="flex items-center gap-1 px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 text-sm font-medium hover:bg-green-50 hover:border-green-400 dark:hover:bg-gray-800 transition disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="atFirstPage"
          @click="prevSlide"
        >
          <Icon name="material-symbols:chevron-left" class="w-5 h-5" />
          <span class="hidden sm:inline">Slide Sebelumnya</span>
        </button>
        <span class="text-sm text-gray-500">
          Slide <span class="font-semibold text-green-700 dark:text-green-400">{{ page }}</span> dari {{ totalPages }}
        </span>
        <button
          class="flex items-center gap-1 px-4 py-2 rounded-xl bg-green-600 hover:bg-green-700 text-white text-sm font-medium shadow-md shadow-green-300/50 transition disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="atLastPage"
          @click="nextSlide"
        >
          <span class="hidden sm:inline">Slide Berikutnya</span>
          <Icon name="material-symbols:chevron-right" class="w-5 h-5" />
        </button>
      </div>

      <!-- Peta slide -->
      <div v-if="totalPages > 1" class="mt-3 flex gap-2 overflow-x-auto pb-1 sm:justify-center">
        <button
          v-for="p in totalPages"
          :key="'page-' + p"
          :ref="(el) => setPageRef(el, p)"
          class="w-9 h-9 shrink-0 rounded-xl text-xs font-bold border transition flex items-center justify-center"
          :class="
            p === page
              ? 'bg-green-600 border-green-600 text-white shadow-lg shadow-green-300/50 scale-105'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-green-400 hover:text-green-600'
          "
          :aria-label="'Buka slide ' + p"
          @click="goToPage(p)"
        >
          {{ p }}
        </button>
      </div>
    </template>

    <QuizQuestionBankForm
      :open="formOpen"
      :question="editing"
      @close="formOpen = false; editing = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const items = ref([]);
const loading = ref(true);
const formOpen = ref(false);
const editing = ref(null);
const generatingId = ref(null);
const filters = reactive({ q: "", type: "", difficulty: "", status: "", purpose: "" });

const pageSize = ref(10);
const page = ref(1);
const direction = ref("next");
const slideTop = ref(null);

const hasActiveFilter = computed(() => !!(filters.q || filters.type || filters.difficulty || filters.status || filters.purpose));

const totalPages = computed(() => Math.max(1, Math.ceil(items.value.length / pageSize.value)));
const pagedItems = computed(() =>
  items.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value)
);
const rangeStart = computed(() => (items.value.length ? (page.value - 1) * pageSize.value + 1 : 0));
const rangeEnd = computed(() => Math.min(page.value * pageSize.value, items.value.length));
const progress = computed(() => (totalPages.value ? (page.value / totalPages.value) * 100 : 0));
const atFirstPage = computed(() => page.value <= 1);
const atLastPage = computed(() => page.value >= totalPages.value);

const typeLabel = (t) => (t === "true_false" ? "Benar/Salah" : "Pilihan Ganda");
const difficultyLabel = (d) =>
  d === "easy" ? "Mudah" : d === "hard" ? "Sulit" : d === "medium" ? "Sedang" : "Belum ditentukan";
const statusLabel = (s) =>
  s === "DRAFT" ? "Menunggu review" : s === "REJECTED" ? "Ditolak" : "Disetujui";
const statusClass = (s) =>
  s === "DRAFT"
    ? "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300"
    : s === "REJECTED"
      ? "bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
      : "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400";
const accentClass = (s) =>
  s === "DRAFT" ? "bg-amber-400" : s === "REJECTED" ? "bg-gray-300 dark:bg-gray-600" : "bg-green-500";

// Pembahasan yang dibuka (per id soal)
const expanded = ref(new Set());
const isExpanded = (id) => expanded.value.has(id);
const toggleExpanded = (id) => {
  const s = new Set(expanded.value);
  s.has(id) ? s.delete(id) : s.add(id);
  expanded.value = s;
};

const resetFilters = () => {
  filters.q = "";
  filters.type = "";
  filters.difficulty = "";
  filters.status = "";
  filters.purpose = "";
};

// Navigasi slide
const goToPage = (p, scroll = false) => {
  const target = Math.min(Math.max(1, p), totalPages.value);
  if (target === page.value) return;
  direction.value = target > page.value ? "next" : "prev";
  page.value = target;
  if (scroll) nextTick(() => slideTop.value?.scrollIntoView({ behavior: "smooth", block: "start" }));
};
const nextSlide = () => goToPage(page.value + 1, true);
const prevSlide = () => goToPage(page.value - 1, true);

const pageRefs = [];
const setPageRef = (el, p) => (pageRefs[p] = el);
watch(page, (p) => {
  nextTick(() => {
    pageRefs[p]?.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  });
});

watch(pageSize, () => {
  page.value = 1;
});

const onKeydown = (e) => {
  if (formOpen.value) return;
  const tag = (e.target?.tagName || "").toLowerCase();
  if (["input", "textarea", "select"].includes(tag)) return;
  if (e.key === "ArrowRight") {
    e.preventDefault();
    nextSlide();
  } else if (e.key === "ArrowLeft") {
    e.preventDefault();
    prevSlide();
  }
};

let touchStartX = null;
const onTouchStart = (e) => {
  touchStartX = e.changedTouches[0].clientX;
};
const onTouchEnd = (e) => {
  if (touchStartX === null) return;
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) > 50) {
    if (dx < 0) nextSlide();
    else prevSlide();
  }
  touchStartX = null;
};

const generateExplanation = async (b) => {
  if (generatingId.value) return;
  generatingId.value = b.id;
  try {
    const payload = await $fetch(`${config.public.backend}/api/teacher/question-bank/${b.id}/explanation/generate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    toast.add({ title: payload.message || "Pembahasan AI dibuat. Setujui di halaman Pembahasan AI.", color: "green" });
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal membuat pembahasan", color: "red" });
  } finally {
    generatingId.value = null;
  }
};

const load = async () => {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    if (filters.type) params.set("type", filters.type);
    if (filters.difficulty) params.set("difficulty", filters.difficulty);
    if (filters.status) params.set("status", filters.status);
    if (filters.purpose) params.set("purpose", filters.purpose);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const data = await $fetch(`${config.public.backend}/api/teacher/question-bank${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    items.value = data?.data || [];
    if (page.value > totalPages.value) page.value = totalPages.value;
  } catch (e) {
    toast.add({ title: "Gagal memuat bank soal", color: "red" });
  } finally {
    loading.value = false;
  }
};

const openForm = (b = null) => {
  editing.value = b;
  formOpen.value = true;
};

const onSaved = () => {
  formOpen.value = false;
  editing.value = null;
  load();
};

const remove = async (b) => {
  const result = await swal.fire({
    title: "Hapus soal bank ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/teacher/question-bank/${b.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Soal bank dihapus", color: "green" });
    load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal menghapus soal", color: "red" });
  }
};

let debounceTimer = null;
watch(filters, () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    page.value = 1;
    load();
  }, 300);
});

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));

load();

definePageMeta({
  layout: "teacher",

  middleware: "auth",
  role: "teacher",
});
</script>

<style scoped>
.slide-next-enter-active,
.slide-next-leave-active,
.slide-prev-enter-active,
.slide-prev-leave-active {
  transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-next-enter-from {
  opacity: 0;
  transform: translateX(48px);
}
.slide-next-leave-to {
  opacity: 0;
  transform: translateX(-48px);
}
.slide-prev-enter-from {
  opacity: 0;
  transform: translateX(-48px);
}
.slide-prev-leave-to {
  opacity: 0;
  transform: translateX(48px);
}
</style>
