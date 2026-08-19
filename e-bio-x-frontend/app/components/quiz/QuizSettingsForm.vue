<template>
  <div class="bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-6">
    <h3 class="text-lg font-semibold text-green-700 dark:text-green-500 mb-4 flex items-center gap-2">
      <Icon name="material-symbols:settings" class="w-5 h-5" />
      Pengaturan Kuis
    </h3>

    <form @submit.prevent="save" class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Judul Kuis *</label>
        <input
          v-model="form.title"
          type="text"
          placeholder="Contoh: Kuis Virus & Bakteri"
          class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
          required
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Deskripsi</label>
        <textarea
          v-model="form.description"
          rows="2"
          placeholder="Deskripsi singkat kuis..."
          class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
        ></textarea>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Materi (wajib untuk siswa) *
          </label>
          <select
            v-model="form.material_id"
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            required
            @change="onMaterialChange"
          >
            <option value=""></option>
            <option v-for="m in materials" :key="m.id" :value="m.id">
              {{ m.title }} <template v-if="m.topic">({{ m.topic }})</template>
            </option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Bagian Materi (opsional)</label>
          <select
            v-model="form.section_id"
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            <option :value="null">Semua bagian</option>
            <option v-for="s in sections" :key="s.id" :value="s.id">{{ s.title }}</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Durasi (menit) *</label>
          <input
            v-model.number="form.duration"
            type="number"
            min="1"
            max="600"
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            required
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nilai Lulus (%) *</label>
          <input
            v-model.number="form.passing_grade"
            type="number"
            min="0"
            max="100"
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            required
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Maks. Percobaan *</label>
          <input
            v-model.number="form.max_attempts"
            type="number"
            min="1"
            max="10"
            class="w-full dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
            required
          />
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
          <input v-model="form.shuffle_questions" type="checkbox" class="accent-green-600" />
          Acak urutan soal
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
          <input v-model="form.shuffle_options" type="checkbox" class="accent-green-600" />
          Acak pilihan jawaban
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
          <input v-model="form.show_explanation" type="checkbox" class="accent-green-600" />
          Tampilkan pembahasan
        </label>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
        <select
          v-model="form.status"
          class="w-full md:w-64 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
        >
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
        <p v-if="form.status === 'published'" class="text-xs text-blue-600 dark:text-blue-400 mt-1">
          Kuis akan tampil di siswa yang terdaftar pada kelas materi.
        </p>
      </div>

      <div class="flex gap-2 pt-2">
        <button
          type="submit"
          class="bg-green-600 hover:bg-green-700 text-white px-5 py-2 rounded-lg transition flex items-center gap-1"
        >
          <Icon name="material-symbols:save" class="w-5 h-5" />
          {{ isEdit ? "Simpan Perubahan" : "Buat Kuis" }}
        </button>
        <button
          v-if="isEdit"
          type="button"
          class="border border-gray-300 dark:border-gray-600 px-5 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          @click="$emit('cancel')"
        >
          Batal
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
const props = defineProps({
  initial: { type: Object, default: null },
  isEdit: { type: Boolean, default: false },
});
const emit = defineEmits(["saved", "cancel"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const materials = ref([]);
const sections = ref([]);
const saving = ref(false);

const form = ref({
  title: "",
  description: "",
  material_id: "",
  section_id: null,
  duration: 15,
  passing_grade: 75,
  max_attempts: 1,
  shuffle_questions: false,
  shuffle_options: false,
  show_explanation: true,
  status: "draft",
});

const loadMaterials = async () => {
  try {
    const data = await $fetch(`${config.public.backend}/api/materials`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    materials.value = data || [];
  } catch (e) {
    toast.add({ title: "Gagal memuat daftar materi", color: "red" });
  }
};

const onMaterialChange = async () => {
  sections.value = [];
  form.value.section_id = null;
  if (!form.value.material_id) return;
  try {
    const m = await $fetch(`${config.public.backend}/api/materials/${form.value.material_id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    sections.value = m?.sections || [];
  } catch (e) {
    sections.value = [];
  }
};

const applyInitial = () => {
  if (props.initial) {
    form.value = {
      title: props.initial.title || "",
      description: props.initial.description || "",
      material_id: props.initial.material_id || "",
      section_id: props.initial.section_id || null,
      duration: props.initial.duration || 15,
      passing_grade: props.initial.passing_grade || 75,
      max_attempts: props.initial.max_attempts || 1,
      shuffle_questions: !!props.initial.shuffle_questions,
      shuffle_options: !!props.initial.shuffle_options,
      show_explanation: props.initial.show_explanation !== false,
      status: props.initial.status || "draft",
    };
    onMaterialChange().then(() => {
      form.value.section_id = props.initial.section_id || null;
    });
  }
};

const save = async () => {
  if (!form.value.title.trim()) {
    toast.add({ title: "Judul kuis wajib diisi", color: "red" });
    return;
  }
  if (!form.value.material_id) {
    toast.add({ title: "Pilih materi untuk kuis", color: "red" });
    return;
  }
  saving.value = true;
  try {
    const body = {
      title: form.value.title,
      description: form.value.description,
      material_id: Number(form.value.material_id) || null,
      section_id: form.value.section_id ? Number(form.value.section_id) : null,
      duration: Number(form.value.duration) || 15,
      passing_grade: Number(form.value.passing_grade) || 0,
      max_attempts: Number(form.value.max_attempts) || 1,
      shuffle_questions: form.value.shuffle_questions,
      shuffle_options: form.value.shuffle_options,
      show_explanation: form.value.show_explanation,
      status: form.value.status,
    };
    let result;
    if (props.isEdit) {
      result = await $fetch(`${config.public.backend}/api/teacher/quizzes/${props.initial.id}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } else {
      result = await $fetch(`${config.public.backend}/api/teacher/quizzes`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    }
    toast.add({ title: "Kuis berhasil disimpan", color: "green" });
    emit("saved", result.quiz);
  } catch (err) {
    const msg = err?.data?.error || "Gagal menyimpan kuis";
    toast.add({ title: msg, color: "red" });
  } finally {
    saving.value = false;
  }
};

loadMaterials();
applyInitial();
</script>