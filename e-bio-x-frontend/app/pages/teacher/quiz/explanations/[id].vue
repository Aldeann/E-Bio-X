<template>
  <div class="container mx-auto px-4 py-6" v-if="expl">
    <div class="flex items-center gap-2 mb-6">
      <button class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300" @click="$router.back()">
        <Icon name="material-symbols:arrow-back" class="w-6 h-6" />
      </button>
      <div>
        <h2 class="text-2xl font-semibold">Detail Pembahasan AI</h2>
        <div class="flex flex-wrap items-center gap-2 mt-1">
          <span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadge(expl.status)">{{ statusLabel(expl.status) }}</span>
          <span v-if="expl.edited_by_teacher" class="text-xs px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-400">Disunting guru</span>
          <span v-if="expl.generated_by" class="text-xs text-gray-500">Sumber: {{ expl.generated_by }}</span>
        </div>
      </div>
    </div>

    <div class="max-w-4xl mx-auto space-y-4">
      <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-5">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="space-y-1">
            <h3 class="font-semibold">Status: {{ statusLabel(expl.status) }}</h3>
            <p class="text-xs text-gray-500">
              Created {{ expl.created_at }} · Updated {{ expl.updated_at }}
              <span v-if="expl.approved_at"> · Disetujui {{ expl.approved_at }}</span>
            </p>
          </div>
          <button
            class="py-2 px-4 rounded-lg text-sm text-white transition"
            :class="expl.status === 'TEACHER_APPROVED' ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'"
            :disabled="expl.status === 'TEACHER_APPROVED'"
            @click="regenerate"
          >
            <Icon name="material-symbols:refresh" class="w-4 h-4 inline" /> Ulangi Generate AI
          </button>
        </div>
      </div>

      <div class="space-y-4">
        <EditorField v-model="form.summary" label="Ringkasan" />
        <EditorField v-model="form.correct_answer_explanation" label="Penjelasan Jawaban Benar" />
        <EditorField v-model="form.student_answer_analysis" label="Analisis Jawaban Siswa" />
        <EditorField v-model="form.key_concept" label="Konsep Kunci" />
        <EditorField v-model="form.misconception" label="Kesalahpahaman Umum" />
        <EditorField v-model="form.recommended_material" label="Materi Rekomendasi" />
      </div>

      <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-5">
        <h3 class="font-semibold mb-3">Penjelasan Tiap Pilihan</h3>
        <div v-if="form.option_explanations?.length" class="space-y-2">
          <div
            v-for="(o, i) in form.option_explanations"
            :key="o.option"
            class="flex items-center gap-3 p-3 rounded-lg border"
            :class="o.is_correct ? 'border-green-400 bg-green-50 dark:bg-green-900/30' : 'border-gray-200 dark:border-gray-700'"
          >
            <span class="text-sm font-semibold w-5">{{ o.option }}</span>
            <input
              class="flex-1 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm"
              v-model="o.explanation"
            />
            <label class="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
              <input type="checkbox" v-model="o.is_correct" class="accent-green-600 scale-110" />
              Benar
            </label>
          </div>
        </div>
        <p v-else class="text-sm text-gray-500">Tidak ada penjelasan pilihan.</p>
      </div>

      <div class="flex flex-wrap justify-end gap-2">
        <button class="px-4 py-2 rounded-lg text-sm bg-gray-600 hover:bg-gray-700 text-white transition" @click="save">
          <Icon name="material-symbols:save" class="w-4 h-4 inline" /> Simpan Perubahan
        </button>
        <button
          v-if="expl.status !== 'TEACHER_APPROVED'"
          class="px-4 py-2 rounded-lg text-sm bg-green-600 hover:bg-green-700 text-white transition"
          @click="approve"
        >
          <Icon name="material-symbols:check" class="w-4 h-4 inline" /> Setujui Publikasi
        </button>
        <button @click="openManual" class="px-4 py-2 rounded-lg text-sm bg-purple-600 hover:bg-purple-700 text-white transition">
          <Icon name="material-symbols:edit" class="w-4 h-4 inline" /> Simpan sebagai Pembahasan Guru
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const route = useRoute();
const id = Number(route.params.id);

const expl = ref(null);
const form = reactive({});

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

const syncForm = (e) => {
  Object.assign(form, {
    summary: e.summary || "",
    correct_answer_explanation: e.correct_answer_explanation || "",
    student_answer_analysis: e.student_answer_analysis || "",
    key_concept: e.key_concept || "",
    misconception: e.misconception || "",
    recommended_material: e.recommended_material || "",
    option_explanations: (e.option_explanations || []).map((o) => ({ ...o })),
  });
};

const load = async () => {
  try {
    expl.value = await $fetch(`${config.public.backend}/api/teacher/quiz/explanations/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    syncForm(expl.value.explanation);
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal memuat detail pembahasan", color: "red" });
  }
};

const save = async (asTeacher = false) => {
  const body = {
    summary: form.summary,
    correct_answer_explanation: form.correct_answer_explanation,
    student_answer_analysis: form.student_answer_analysis,
    option_explanations: form.option_explanations,
    key_concept: form.key_concept,
    misconception: form.misconception,
    recommended_material: form.recommended_material,
    recommended_material_id: expl.value.explanation.recommended_material_id,
  };
  try {
    const payload = await $fetch(`${config.public.backend}/api/quiz/explanations/${id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    toast.add({ title: payload.message || "Perubahan disimpan", color: "green" });
    load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal menyimpan", color: "red" });
  }
};

const approve = async () => {
  const res = await swal.fire({
    title: "Setujui dan publikasikan?",
    text: "Siswa akan dapat melihat pembahasan ini.",
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Setujui",
    cancelButtonText: "Batal",
  });
  if (!res.isConfirmed) return;
  try {
    const payload = await $fetch(`${config.public.backend}/api/quiz/explanations/${id}/approve`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    toast.add({ title: payload.message || "Disetujui", color: "green" });
    load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal menyetujui", color: "red" });
  }
};

const regenerate = async () => {
  const msg = expl.value.explanation.status === "TEACHER_APPROVED"
    ? "Pembahasan guru tidak dapat ditimpa oleh AI."
    : "Generate ulang dengan AI? Versi sebelumnya akan tersimpan di riwayat versi.";
  const res = await swal.fire({
    title: "Generate ulang?",
    text: msg,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Generate",
    cancelButtonText: "Batal",
  });
  if (!res.isConfirmed) return;
  try {
    const payload = await $fetch(`${config.public.backend}/api/quiz/explanations/${id}/regenerate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    toast.add({ title: payload.message || "Selesai", color: "green" });
    load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal", color: "red" });
  }
};

const openManual = async () => {
  if (!confirm("Konversi menjadi pembahasan guru? Pembahasan ini tidak akan bisa ditimpa AI lagi.")) return;
  try {
    const payload = await $fetch(`${config.public.backend}/api/quiz/explanations/${id}/manual`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        summary: form.summary,
        correct_answer_explanation: form.correct_answer_explanation,
        student_answer_analysis: form.student_answer_analysis,
        option_explanations: form.option_explanations,
        key_concept: form.key_concept,
        misconception: form.misconception,
        recommended_material: form.recommended_material,
      }),
    });
    toast.add({ title: payload.message || "Pembahasan guru disimpan", color: "green" });
    load();
  } catch (e) {
    toast.add({ title: e?.data?.error || "Gagal", color: "red" });
  }
};

load();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>