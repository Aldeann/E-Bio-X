<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-3xl font-bold text-green-500 mb-6">Buat Forum Baru</h1>

    <div
      v-if="form.material_id"
      class="mb-4 px-4 py-3 rounded-xl border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 text-sm text-green-800 dark:text-green-200 flex items-center gap-2"
    >
      <Icon name="material-symbols:link" class="w-4 h-4 shrink-0" />
      Forum ini akan tertaut ke materi: <span class="font-semibold">{{ form.title }}</span>
    </div>

    <div class="bg-white dark:bg-gray-900 border dark:border-gray-700 rounded-xl p-6 shadow-md space-y-4">
      <div>
        <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Tipe Forum</label>
        <div class="grid grid-cols-2 gap-2">
          <button v-for="t in forumTypes" :key="t.value" @click="form.type = t.value"
            class="p-3 rounded-lg border text-left transition"
            :class="form.type === t.value
              ? 'border-green-500 bg-green-50 dark:bg-green-950/30'
              : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'">
            <Icon :name="t.icon" class="text-green-500 text-xl mb-1" />
            <p class="font-medium text-sm text-gray-800 dark:text-white">{{ t.label }}</p>
            <p class="text-xs text-gray-500">{{ t.desc }}</p>
          </button>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Judul *</label>
        <input v-model="form.title" type="text" placeholder="Judul forum"
          class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500" />
      </div>

      <div>
        <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Deskripsi</label>
        <textarea v-model="form.description" rows="3" placeholder="Jelaskan tujuan dan aturan forum..."
          class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500"></textarea>
      </div>

      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Kelas</label>
          <select v-model="form.course_id" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500">
            <option value="">— Tidak terikat kelas —</option>
            <option v-for="c in courses" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Visibilitas</label>
          <select v-model="form.visibility" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500">
            <option value="COURSE">Kursus (semua anggota kelas)</option>
            <option value="CLASS">Kelas</option>
            <option value="PRIVATE">Pribadi</option>
          </select>
        </div>
      </div>

      <div class="grid sm:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Topik (opsional)</label>
          <input v-model="form.topic" type="text" placeholder="cth: Sel, Genetika"
            class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500" />
        </div>
        <div v-if="role === 'teacher' || role === 'admin'">
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Status</label>
          <select v-model="form.status" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500">
            <option value="ACTIVE">Aktif</option>
            <option value="DRAFT">Draft</option>
            <option value="SCHEDULED">Terjadwal</option>
          </select>
        </div>
      </div>

      <div v-if="form.type === 'PRESENTATION'"
        class="p-4 bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-800 rounded-lg space-y-3">
        <p class="font-semibold text-purple-700 dark:text-purple-300 flex items-center gap-2"><Icon name="mdi:microphone-outline" /> Pengaturan Presentasi</p>
        <div>
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Nama Kelompok</label>
          <input v-model="form.presentation_group_name" type="text" placeholder="cth: Kelompok 1"
            class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500" />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Pertanyaan Inti (pinned)</label>
          <textarea v-model="form.pinned_question" rows="2" placeholder="Pertanyaan inti yang menjadi fokus presentasi"
            class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500"></textarea>
        </div>
        <p class="text-xs text-gray-500">Materi presentasi dapat diunggah setelah forum dibuat, melalui halaman forum.</p>
      </div>

      <div class="flex gap-2 justify-end pt-2">
        <NuxtLink :to="`/${role}/forum`" class="px-4 py-2 rounded-lg bg-gray-300 dark:bg-gray-700 hover:bg-gray-400">Batal</NuxtLink>
        <button @click="submit" :disabled="!form.title.trim() || saving"
          class="bg-green-600 text-white px-5 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50">
          {{ saving ? "Menyimpan..." : "Buat Forum" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  role: { type: String, required: true },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const role = useCookie("role").value;
const toast = useToast();
const router = useRouter();

const courses = ref([]);
const saving = ref(false);
const form = reactive({
  title: "",
  description: "",
  type: "GENERAL_DISCUSSION",
  course_id: "",
  visibility: "COURSE",
  status: "ACTIVE",
  topic: "",
  pinned_question: "",
  presentation_group_name: "",
  presentation_file_url: "",
  presentation_file_name: "",
  material_id: null,
});

const forumTypes = [
  { value: "GENERAL_DISCUSSION", label: "Diskusi", desc: "Diskusi bebas kelas", icon: "mdi:message-text-outline" },
  { value: "PRESENTATION", label: "Presentasi", desc: "Presentasi kelompok dengan tanya jawab", icon: "mdi:microphone-outline" },
  { value: "QUESTION_ANSWER", label: "Tanya Jawab", desc: "Sesi tanya jawab terstruktur", icon: "mdi:comment-question-outline" },
  { value: "CASE_STUDY", label: "Studi Kasus", desc: "Analisis kasus bersama", icon: "mdi:flask-outline" },
];

const fetchCourses = async () => {
  try {
    const endpoint = props.role === "teacher" ? "/api/courses/teacher" : "/api/courses/student";
    const res = await $fetch(`${config.public.backend}${endpoint}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    courses.value = Array.isArray(res) ? res : res.courses || [];

    const q = useRoute().query;
    const materialId = q.material_id;
    if (materialId) {
      form.material_id = Number(materialId);
      if (q.course_id) form.course_id = String(q.course_id);
      if (q.topic) form.title = decodeURIComponent(q.topic);
      if (q.category) form.topic = decodeURIComponent(q.category);
      form.description = form.description || `Diskusi terkait materi ${form.title}.`;
    }
  } catch (err) {
    console.error(err);
  }
};

const submit = async () => {
  saving.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/forums`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...form,
        course_id: form.course_id ? Number(form.course_id) : null,
        material_id: form.material_id ? Number(form.material_id) : null,
      }),
    });
    toast.add({ title: "Forum berhasil dibuat.", color: "green" });
    router.push(`/${props.role}/forum/${res.forum.id}`);
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal membuat forum.", color: "red" });
  } finally {
    saving.value = false;
  }
};

fetchCourses();
</script>