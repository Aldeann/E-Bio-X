<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-6">
      <div>
        <h2 class="text-2xl font-semibold">Bank Soal</h2>
        <p class="text-sm text-gray-500">Kumpulan soal yang bisa digunakan kembali di kuis mana pun.</p>
      </div>
      <button
        class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition flex items-center gap-1 shadow-md shadow-green-300/50"
        @click="openForm()"
      >
        <Icon name="material-symbols:add" class="w-5 h-5" /> Tambah Soal
      </button>
    </div>

    <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-4 mb-5">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
        <input
          v-model="filters.q"
          type="text"
          placeholder="Cari pertanyaan..."
          class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm"
        />
        <select v-model="filters.type" class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm">
          <option value="">Semua tipe</option>
          <option value="multiple_choice">Pilihan Ganda</option>
          <option value="true_false">Benar/Salah</option>
        </select>
        <select v-model="filters.difficulty" class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm">
          <option value="">Semua kesulitan</option>
          <option value="easy">Mudah</option>
          <option value="medium">Sedang</option>
          <option value="hard">Sulit</option>
        </select>
        <button class="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm" @click="load">
          Terapkan
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500 text-center py-10">Memuat bank soal...</div>

    <div v-else-if="items.length === 0" class="text-center py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-600 rounded-xl">
      <Icon name="material-symbols:database" class="w-14 h-14 text-gray-300 mx-auto mb-3" />
      <p class="text-gray-500">Belum ada soal bank.</p>
    </div>

    <div v-else class="space-y-3">
      <div
        v-for="b in items"
        :key="b.id"
        class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-sm p-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400">
                {{ typeLabel(b.question_type) }}
              </span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400">
                {{ difficultyLabel(b.difficulty) }}
              </span>
              <span v-if="b.topic" class="text-xs px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-400">
                {{ b.topic }}
              </span>
              <span class="text-xs text-gray-500">{{ b.points }} poin</span>
            </div>
            <p class="mt-2 font-medium">{{ b.question_text }}</p>
            <ul class="mt-2 space-y-1 text-sm">
              <li
                v-for="o in b.options"
                :key="o.option_id"
                class="flex items-center gap-1.5"
                :class="o.is_correct ? 'text-green-600 dark:text-green-400 font-medium' : ''"
              >
                <Icon
                  :name="o.is_correct ? 'material-symbols:check-circle' : 'material-symbols:radio-button-unchecked'"
                  class="w-4 h-4 shrink-0"
                />
                <span>{{ o.option_text }}</span>
              </li>
              <li v-if="b.explanation" class="pt-1 text-gray-500 italic">Pembahasan: {{ b.explanation }}</li>
            </ul>
          </div>
          <div class="flex gap-1 shrink-0">
            <button class="text-amber-500 hover:text-amber-600" title="Generate Pembahasan AI" @click="generateExplanation(b)">
              <Icon name="material-symbols:auto-awesome" class="w-5 h-5" />
            </button>
            <button class="text-blue-500 hover:text-blue-600" title="Edit" @click="openForm(b)">
              <Icon name="material-symbols:edit" class="w-5 h-5" />
            </button>
            <button class="text-red-500 hover:text-red-600" title="Hapus" @click="remove(b)">
              <Icon name="material-symbols:delete" class="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <QuestionBankForm
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
const filters = reactive({ q: "", type: "", difficulty: "" });

const typeLabel = (t) => (t === "true_false" ? "Benar/Salah" : "Pilihan Ganda");
const difficultyLabel = (d) => (d === "easy" ? "Mudah" : d === "hard" ? "Sulit" : "Sedang");

const generateExplanation = async (b) => {
  try {
    const payload = await $fetch(`${config.public.backend}/api/teacher/question-bank/${b.id}/explanation/generate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    toast.add({ title: payload.message || "Pembahasan AI dibuat. Setujui di halaman Pembahasan AI.", color: "green" });
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal membuat pembahasan", color: "red" });
  }
};

const load = async () => {
  loading.value = true;
  try {
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    if (filters.type) params.set("type", filters.type);
    if (filters.difficulty) params.set("difficulty", filters.difficulty);
    const qs = params.toString() ? `?${params.toString()}` : "";
    const data = await $fetch(`${config.public.backend}/api/teacher/question-bank${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    items.value = data?.data || [];
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

load();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>