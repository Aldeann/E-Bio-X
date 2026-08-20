<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-semibold">Pembahasan AI</h2>
        <p class="text-sm text-gray-500">Kelola pembahasan soal yang dihasilkan AI. Siswa hanya bisa melihat pembahasan berstatus disetujui.</p>
      </div>
      <div class="flex items-center gap-2">
        <input
          v-model="questionIdForGen"
          type="number"
          placeholder="ID Soal"
          class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm w-28"
        />
        <button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition" :disabled="busy" @click="generateForQuestion">
          <Icon name="material-symbols:auto-awesome" class="w-4 h-4 inline" /> Generate
        </button>
      </div>
    </div>

    <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-4 mb-5">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
        <div>
          <label class="text-xs text-gray-500">Status</label>
          <select v-model="filters.status" class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm">
            <option value="ALL">Semua status</option>
            <option v-for="(c, s) in summary.by_status || {}" :key="s" :value="s">
              {{ statusLabel(s) }} ({{ c }})
            </option>
            <option value="MISSING">Belum ada (MISSING)</option>
          </select>
        </div>
        <input
          v-model="filters.q"
          type="text"
          placeholder="Cari soal..."
          class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm"
        />
        <button class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm" @click="load">Terapkan</button>
      </div>
      <div v-if="summary.total !== undefined" class="mt-3 text-sm text-gray-500">
        Total pembahasan: <b>{{ summary.total }}</b>
        <span class="mx-1">·</span>
        Disetujui: <b class="text-green-600">{{ (summary.by_status || {}).APPROVED || 0 }}</b>
        <span class="mx-1">·</span>
        Menunggu: <b class="text-amber-600">{{ (summary.by_status || {}).AI_GENERATED || 0 }}</b>
        <span class="mx-1">·</span>
        Gagal: <b class="text-red-600">{{ (summary.by_status || {}).FAILED || 0 }}</b>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat pembahasan...</div>

    <div v-else-if="!items.length" class="text-center py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-600 rounded-xl">
      <Icon name="material-symbols:lightbulb-outline" class="w-14 h-14 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">Belum ada pembahasan. Generate pembahasan dari soal di atas.</p>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="item in filtered"
        :key="item.id"
        class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-sm p-4"
      >
        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadge(item.status)">
                {{ statusLabel(item.status) }}
              </span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400">
                {{ item.question_type || "multiple_choice" }}
              </span>
              <span v-if="item.edited_by_teacher" class="text-xs px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-400">
                Disunting guru
              </span>
            </div>
            <p class="mt-2 font-medium">{{ item.question_text || `Soal #${item.question_id || item.bank_question_id}` }}</p>
            <div class="mt-1 text-xs text-gray-500 flex flex-wrap gap-3">
              <span>ID {{ item.question_id || item.bank_question_id }}</span>
              <span v-if="item.generated_by">Sumber: {{ item.generated_by }}</span>
              <span v-if="item.model_name">Model: {{ item.model_name }}</span>
              <span v-if="item.feedback_summary">
                Umpan balik: {{ item.feedback_summary.helpful || 0 }} 👍 / {{ item.feedback_summary.not_helpful || 0 }} 👎
              </span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 flex-wrap shrink-0">
            <NuxtLink
              :to="`/teacher/quiz/explanations/${item.id}`"
              class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
            >
              <Icon name="material-symbols:visibility" class="w-4 h-4" /> Lihat
            </NuxtLink>
            <button
              v-if="item.status !== 'TEACHER_APPROVED'"
              class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-green-600 hover:bg-green-700 text-white transition"
              @click="approve(item)"
            >
              <Icon name="material-symbols:check" class="w-4 h-4" /> Setujui
            </button>
            <button
              v-if="item.status === 'AI_GENERATED'"
              class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-red-500 hover:bg-red-600 text-white transition"
              @click="reject(item)"
            >
              <Icon name="material-symbols:close" class="w-4 h-4" /> Tolak
            </button>
            <button
              v-if="item.status !== 'TEACHER_APPROVED'"
              class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs bg-blue-600 hover:bg-blue-700 text-white transition"
              @click="regenerate(item)"
            >
              <Icon name="material-symbols:refresh" class="w-4 h-4" /> Ulangi
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const items = ref([]);
const summary = ref({ by_status: {} });
const loading = ref(true);
const busy = ref(false);
const questionIdForGen = ref("");
const filters = reactive({ status: "ALL", q: "" });

const statusLabel = (s) =>
  ({ MISSING: "Belum Ada", AI_GENERATED: "Draft AI", REVIEW_REQUIRED: "Perlu Review", APPROVED: "Disetujui", REJECTED: "Ditolak", TEACHER_APPROVED: "Guru", FAILED: "Gagal", STALE: "Usang" })[s] || s;

const statusBadge = (s) =>
  ({
    MISSING: "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400",
    AI_GENERATED: "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400",
    APPROVED: "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400",
    TEACHER_APPROVED: "bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-400",
    REJECTED: "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-400",
    FAILED: "bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-400",
    STALE: "bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-400",
  })[s] || "bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400";

const filtered = computed(() => {
  let list = items.value;
  if (filters.status && filters.status !== "ALL") {
    list = list.filter((i) => i.status === filters.status);
  }
  if (filters.q) {
    const q = filters.q.toLowerCase();
    list = list.filter((i) => ((i.question_text || "").toLowerCase().includes(q)) || String(i.question_id || i.bank_question_id) === q);
  }
  return list;
});

const load = async () => {
  loading.value = true;
  try {
    const payload = await $fetch(`${config.public.backend}/api/teacher/quiz/explanations`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    summary.value = payload.summary || { by_status: {} };
    items.value = payload.items || [];
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal memuat pembahasan", color: "red" });
  } finally {
    loading.value = false;
  }
};

const generateForQuestion = async () => {
  if (!questionIdForGen.value) {
    toast.add({ title: "Masukkan ID soal", color: "amber" });
    return;
  }
  busy.value = true;
  try {
    const payload = await $fetch(`${config.public.backend}/api/questions/${questionIdForGen.value}/explanation/generate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    toast.add({ title: payload.message || "Pembahasan berhasil dibuat", color: "green" });
    questionIdForGen.value = "";
    load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal membuat pembahasan", color: "red" });
  } finally {
    busy.value = false;
  }
};

const mutate = async (id, action, method = "POST") => {
  try {
    const payload = await $fetch(`${config.public.backend}/api/quiz/explanations/${id}/${action}`, {
      method,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    toast.add({ title: payload.message || "Berhasil", color: "green" });
    load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal", color: "red" });
  }
};

const approve = async (item) => {
  const res = await swal.fire({
    title: "Setujui pembahasan?",
    text: "Siswa akan dapat melihat pembahasan ini.",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Setujui",
    cancelButtonText: "Batal",
  });
  if (res.isConfirmed) mutate(item.id, "approve");
};

const reject = (item) => mutate(item.id, "reject");
const regenerate = (item) => mutate(item.id, "regenerate");

load();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>