<template>
  <div class="container mx-auto px-4 py-6">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
      <div>
        <h2 class="text-2xl font-semibold">Latihan per Bagian</h2>
        <p class="text-sm text-gray-500">
          Soal latihan untuk tiap bagian materi. Draf AI hanya tersimpan sebagai draf &mdash; guru yang
          menyetujuinya sebelum bisa dipakai siswa.
        </p>
      </div>
      <button
        class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
        @click="loadAll"
      >
        <Icon :name="loading ? 'mdi:loading' : 'material-symbols:refresh'" class="w-4 h-4" :class="loading ? 'animate-spin' : ''" />
        Muat ulang
      </button>
    </div>

    <div
      v-if="!aiAvailable"
      class="mb-4 p-3 rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-900/30 text-sm text-amber-800 dark:text-amber-200"
    >
      {{ aiReason || "AI belum dikonfigurasi, jadi draf tidak bisa dibuat." }}
      Soal latihan tetap bisa ditulis sendiri di <NuxtLink to="/teacher/question-bank" class="underline">Bank Soal</NuxtLink>
      lalu ditautkan ke bagian di bawah.
    </div>

    <div class="flex gap-2 mb-4 border-b border-gray-200 dark:border-gray-700">
      <button
        v-for="t in tabs"
        :key="t.id"
        class="px-3 py-2 text-sm font-medium border-b-2 -mb-px transition"
        :class="tab === t.id
          ? 'border-green-600 text-green-700 dark:text-green-400'
          : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'"
        @click="tab = t.id"
      >
        {{ t.label }}
        <span
          v-if="t.id === 'review' && drafts.length"
          class="ml-1 px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 text-xs"
        >
          {{ drafts.length }}
        </span>
      </button>
    </div>

    <!-- ============================ BAGIAN ============================ -->
    <div v-if="tab === 'sections'">
      <div v-if="loading" class="text-center py-10 text-gray-500">Memuat bagian materi...</div>

      <div v-else-if="groups.length === 0" class="text-center py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-700 rounded-xl">
        <Icon name="material-symbols:view_quilt" class="w-14 h-14 text-gray-300 mx-auto mb-3" />
        <p class="text-gray-500">
          Belum ada bagian materi pada materi Anda. Tambahkan bagian dulu di halaman penyusun materi.
        </p>
      </div>

      <div v-else class="space-y-6">
        <div v-for="g in groups" :key="g.material_id">
          <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            {{ g.material_title }}
          </h3>
          <div class="space-y-2">
            <div
              v-for="row in g.rows"
              :key="row.section_id"
              class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4"
            >
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <p class="font-medium">
                    <span class="text-gray-400 mr-1">{{ row.position + 1 }}.</span>{{ row.title }}
                  </p>
                  <div class="flex flex-wrap items-center gap-1.5 mt-1.5">
                    <span
                      class="text-xs px-2 py-0.5 rounded-full"
                      :class="row.approved_count > 0
                        ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-500'"
                    >
                      {{ row.approved_count }} soal disetujui
                    </span>
                    <span
                      v-if="row.draft_count"
                      class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300"
                    >
                      {{ row.draft_count }} menunggu review
                    </span>
                    <span
                      v-if="row.rejected_count"
                      class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500"
                    >
                      {{ row.rejected_count }} ditolak
                    </span>
                  </div>
                  <p v-if="row.approved_count === 0" class="text-xs text-gray-500 mt-1.5">
                    Bagian ini belum punya soal latihan yang disetujui.
                  </p>
                </div>

                <div class="flex flex-wrap items-center gap-2">
                  <select
                    v-model="counts[row.section_id]"
                    class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 text-sm"
                    :title="'Jumlah draf'"
                  >
                    <option v-for="n in 5" :key="n" :value="n">{{ n }} soal</option>
                  </select>
                  <select
                    v-model="difficulties[row.section_id]"
                    class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 text-sm"
                    title="Tingkat kesulitan"
                  >
                    <option value="easy">Mudah</option>
                    <option value="medium">Sedang</option>
                    <option value="hard">Sulit</option>
                  </select>
                  <button
                    class="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-green-600 hover:bg-green-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition"
                    :disabled="!aiAvailable || busySection === row.section_id"
                    :title="aiAvailable ? 'Minta AI membuat draf untuk bagian ini' : 'AI belum dikonfigurasi'"
                    @click="generate(row)"
                  >
                    <Icon
                      :name="busySection === row.section_id ? 'mdi:loading' : 'material-symbols:auto-awesome'"
                      class="w-4 h-4"
                      :class="busySection === row.section_id ? 'animate-spin' : ''"
                    />
                    Buat draf
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ========================== ANTREAN REVIEW ========================== -->
    <div v-else>
      <div class="mb-3 flex items-center gap-2">
        <select
          v-model="draftStatus"
          class="dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1.5 text-sm"
          @change="loadDrafts"
        >
          <option value="DRAFT">Menunggu review</option>
          <option value="APPROVED">Sudah disetujui</option>
          <option value="REJECTED">Ditolak</option>
        </select>
        <span class="text-xs text-gray-500">{{ drafts.length }} soal</span>
      </div>

      <div v-if="loadingDrafts" class="text-center py-10 text-gray-500">Memuat antrean...</div>

      <div v-else-if="drafts.length === 0" class="text-center py-16 bg-white dark:bg-gray-900 border border-dashed border-gray-300 dark:border-gray-700 rounded-xl">
        <Icon name="material-symbols:fact-check" class="w-14 h-14 text-gray-300 mx-auto mb-3" />
        <p class="text-gray-500">Tidak ada soal dengan status ini.</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="d in drafts"
          :key="d.id"
          class="bg-white dark:bg-gray-900 border rounded-xl shadow-sm p-4"
          :class="d.status === 'DRAFT' ? 'border-amber-300 dark:border-amber-700' : 'border-gray-200 dark:border-gray-700'"
        >
          <div class="flex flex-wrap items-center gap-1.5 mb-2">
            <span
              class="text-xs px-2 py-0.5 rounded-full"
              :class="statusClass(d.status)"
            >{{ statusLabel(d.status) }}</span>
            <span class="text-xs px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-400">
              {{ d.source === 'ai' ? 'Draf AI' : 'Tulis guru' }}
            </span>
            <span v-if="d.section_title" class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400">
              {{ d.section_title }}
            </span>
            <span v-if="d.model_name" class="text-xs text-gray-400">{{ d.model_name }}</span>
          </div>

          <p class="font-medium">{{ d.question_text }}</p>
          <ul class="mt-2 space-y-1 text-sm">
            <li
              v-for="o in d.options"
              :key="o.option_id"
              class="flex flex-col"
            >
              <span class="flex items-center gap-1.5" :class="o.is_correct ? 'text-green-600 dark:text-green-400 font-medium' : ''">
                <Icon
                  :name="o.is_correct ? 'material-symbols:check-circle' : 'material-symbols:radio-button-unchecked'"
                  class="w-4 h-4 shrink-0"
                />
                {{ o.option_text }}
              </span>
              <span v-if="o.feedback" class="ml-5 text-xs text-gray-500 italic">{{ o.feedback }}</span>
            </li>
          </ul>
          <p v-if="d.explanation" class="mt-2 text-sm text-gray-500">Pembahasan: {{ d.explanation }}</p>
          <p v-if="d.misconception" class="mt-1 text-sm text-gray-500">
            Miskonsepsi yang diuji: {{ d.misconception }}
          </p>

          <div class="mt-3 flex flex-wrap gap-2">
            <button
              class="px-3 py-1.5 rounded-lg text-sm border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
              @click="openForm(d)"
            >
              <Icon name="material-symbols:edit" class="w-4 h-4 inline" /> Sunting
            </button>
            <button
              v-if="d.status !== 'APPROVED'"
              class="px-3 py-1.5 rounded-lg text-sm bg-green-600 hover:bg-green-700 text-white transition"
              :disabled="busyDraft === d.id"
              @click="decide(d, 'approve')"
            >
              <Icon name="material-symbols:check" class="w-4 h-4 inline" /> Setujui
            </button>
            <button
              v-if="d.status !== 'REJECTED'"
              class="px-3 py-1.5 rounded-lg text-sm border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition"
              :disabled="busyDraft === d.id"
              @click="decide(d, 'reject')"
            >
              <Icon name="material-symbols:close" class="w-4 h-4 inline" /> Tolak
            </button>
          </div>
        </div>
      </div>
    </div>

    <QuizQuestionBankForm
      :open="formOpen"
      :question="editing"
      @close="formOpen = false; editing = null"
      @saved="onSaved"
    />
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const tabs = [
  { id: "sections", label: "Bagian Materi" },
  { id: "review", label: "Antrean Review" },
];
const tab = ref("sections");

const sections = ref([]);
const drafts = ref([]);
const aiAvailable = ref(true);
const aiReason = ref("");
const loading = ref(true);
const loadingDrafts = ref(false);
const busySection = ref(null);
const busyDraft = ref(null);
const formOpen = ref(false);
const editing = ref(null);
const draftStatus = ref("DRAFT");
const counts = reactive({});
const difficulties = reactive({});

const groups = computed(() => {
  const map = new Map();
  for (const row of sections.value) {
    if (!map.has(row.material_id)) {
      map.set(row.material_id, { material_id: row.material_id, material_title: row.material_title, rows: [] });
    }
    map.get(row.material_id).rows.push(row);
  }
  return Array.from(map.values());
});

const statusLabel = (s) =>
  s === "APPROVED" ? "Disetujui" : s === "REJECTED" ? "Ditolak" : "Menunggu review";
const statusClass = (s) =>
  s === "APPROVED"
    ? "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400"
    : s === "REJECTED"
      ? "bg-gray-200 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
      : "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300";

const loadSections = async () => {
  loading.value = true;
  try {
    const data = await $fetch(`${config.public.backend}/api/teacher/practice/sections`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    sections.value = data?.sections || [];
    aiAvailable.value = !!data?.ai_available;
    aiReason.value = data?.ai_unavailable_reason || "";
    for (const row of sections.value) {
      if (counts[row.section_id] === undefined) counts[row.section_id] = 3;
      if (difficulties[row.section_id] === undefined) difficulties[row.section_id] = "medium";
    }
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal memuat bagian", color: "red" });
  } finally {
    loading.value = false;
  }
};

const loadDrafts = async () => {
  loadingDrafts.value = true;
  try {
    const data = await $fetch(`${config.public.backend}/api/teacher/practice/drafts?status=${draftStatus.value}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    drafts.value = data?.data || [];
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal memuat antrean", color: "red" });
  } finally {
    loadingDrafts.value = false;
  }
};

const loadAll = async () => {
  await loadSections();
  if (tab.value === "review") await loadDrafts();
};

watch(tab, (val) => {
  if (val === "review") loadDrafts();
});

const generate = async (row) => {
  busySection.value = row.section_id;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/teacher/practice/sections/${row.section_id}/drafts`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          count: counts[row.section_id] || 3,
          difficulty: difficulties[row.section_id] || "medium",
        }),
      }
    );
    toast.add({
      title: res?.message || `Draf dibuat untuk "${row.title}"`,
      color: res?.skipped_count ? "orange" : "green",
    });
    await loadSections();
    await loadDrafts();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal membuat draf", color: "red" });
  } finally {
    busySection.value = null;
  }
};

const decide = async (d, action) => {
  busyDraft.value = d.id;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/teacher/practice/drafts/${d.id}/${action}`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({}),
      }
    );
    toast.add({ title: res?.message || "Status draf diperbarui", color: "green" });
    await loadDrafts();
    await loadSections();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal mengubah status draf", color: "red" });
  } finally {
    busyDraft.value = null;
  }
};

const openForm = (d) => {
  editing.value = d;
  formOpen.value = true;
};

const onSaved = () => {
  formOpen.value = false;
  editing.value = null;
  loadDrafts();
  loadSections();
};

loadSections();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>