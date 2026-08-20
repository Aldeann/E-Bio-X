<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useSwal } from "~/utils/swal";
import { uploadFile } from "~/utils/upload";

const props = defineProps({
  materialId: { type: [String, Number], default: null },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();

const isEdit = computed(() => !!props.materialId);
const saving = ref(false);
const thumbnailFile = ref(null);
const courseOptions = ref([]);

const form = reactive({
  title: "",
  description: "",
  subject: "Biologi",
  phase: "",
  class_level: "",
  topic: "",
  learning_objectives: "",
  estimated_time: "",
  difficulty: "sedang",
  status: "draft",
  thumbnail_url: "",
  course_ids: [],
});

const phases = ["A", "B", "C", "D", "E", "F"];
const classes = ["X", "XI", "XII"];
const difficulties = [
  { value: "mudah", label: "Mudah" },
  { value: "sedang", label: "Sedang" },
  { value: "sulit", label: "Sulit" },
];

const inputClass =
  "w-full p-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-sm focus:outline-green-500";
const labelClass = "block mb-1 text-sm font-medium text-green-700 dark:text-green-400";

const loadDetail = async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/materials/${props.materialId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    Object.assign(form, {
      title: res.title || "",
      description: res.description || "",
      subject: res.subject || "Biologi",
      phase: res.phase || "",
      class_level: res.class_level || "",
      topic: res.topic || "",
      learning_objectives: res.learning_objectives || "",
      estimated_time: res.estimated_time || "",
      difficulty: res.difficulty || "sedang",
      status: res.status || "draft",
      thumbnail_url: res.thumbnail_url || "",
      course_ids: res.course_ids || [],
    });
  } catch (e) {
    toast.add({ title: "Gagal memuat data materi.", color: "red" });
  }
};

const loadCourses = async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/courses/teacher`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    courseOptions.value = res || [];
  } catch (e) {
    courseOptions.value = [];
  }
  const preselectId = Number(useRoute().query.course_id);
  if (preselectId && courseOptions.value.some((c) => c.id === preselectId) && !form.course_ids.includes(preselectId)) {
    form.course_ids.push(preselectId);
  }
};

const toggleCourse = (id) => {
  const idx = form.course_ids.indexOf(id);
  if (idx >= 0) form.course_ids.splice(idx, 1);
  else form.course_ids.push(id);
};

const onThumbnailChange = (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
  if (![".jpg", ".jpeg", ".png", ".webp"].includes(ext)) {
    swal.fire({ icon: "error", title: "Gunakan gambar (JPG/PNG/WEBP)" });
    return;
  }
  thumbnailFile.value = file;
};

const validate = () => {
  const fail = (msg) => swal.fire({ icon: "warning", title: "Periksa kembali", text: msg });
  if (!form.title.trim()) return fail("Judul materi wajib diisi.");
  if (!form.description.trim()) return fail("Deskripsi wajib diisi.");
  if (!form.phase) return fail("Fase wajib dipilih.");
  if (!form.topic.trim()) return fail("Bab/Topik wajib diisi.");
  if (!form.learning_objectives.trim()) return fail("Tujuan pembelajaran wajib diisi.");
  return true;
};

const uploadThumbnail = async (materialId) => {
  if (!thumbnailFile.value) return;
  try {
    const res = await uploadFile({
      url: `${config.public.backend}/api/materials/${materialId}/files`,
      token,
      file: thumbnailFile.value,
    });
    await $fetch(`${config.public.backend}/api/materials/${materialId}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: { thumbnail_url: res.file.file_url },
    });
  } catch (e) {
    swal.fire({ icon: "error", title: "Gagal mengunggah thumbnail" });
  }
};

const setStatus = async (status) => {
  if (!validate()) return;
  saving.value = true;
  try {
    let materialId = props.materialId;
    const body = { ...form };

    if (!isEdit.value) {
      delete body.status;
      const res = await $fetch(`${config.public.backend}/api/materials`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: { ...body, status },
      });
      materialId = res.material.id;
      await uploadThumbnail(materialId);
      toast.add({
        title: status === "published" ? "Materi dibuat & dipublikasikan." : "Materi dibuat sebagai draft.",
        color: "green",
      });
    } else {
      await $fetch(`${config.public.backend}/api/materials/${materialId}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
        body,
      });
      await uploadThumbnail(materialId);
      if (status && status !== form.status) {
        await $fetch(`${config.public.backend}/api/materials/${materialId}/publish`, {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
          body: { status },
        });
      }
      toast.add({ title: "Materi berhasil diperbarui.", color: "green" });
    }

    navigateTo(`/teacher/materials/builder/${materialId}`);
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Gagal menyimpan materi.";
    toast.add({ title: msg, color: "red" });
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  loadCourses();
  if (isEdit.value) loadDetail();
});
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold text-green-700 dark:text-green-400 mb-6">
      {{ isEdit ? "Edit Materi" : "Buat Materi" }}
    </h1>

    <div class="p-6 bg-white dark:bg-gray-900 rounded-xl shadow border border-green-200 dark:border-green-800 space-y-4">
      <div>
        <label class="labelClass">Judul Materi <span class="text-red-500">*</span></label>
        <input v-model="form.title" type="text" class="inputClass" placeholder="Contoh: Keanekaragaman Hayati" />
      </div>

      <div>
        <label class="labelClass">Deskripsi <span class="text-red-500">*</span></label>
        <textarea v-model="form.description" rows="2" class="inputClass" placeholder="Deskripsi singkat materi..."></textarea>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label class="labelClass">Mata Pelajaran</label>
          <input v-model="form.subject" type="text" class="inputClass" />
        </div>
        <div>
          <label class="labelClass">Fase <span class="text-red-500">*</span></label>
          <select v-model="form.phase" class="inputClass">
            <option value="" disabled>Pilih fase</option>
            <option v-for="p in phases" :key="p" :value="p">Fase {{ p }}</option>
          </select>
        </div>
        <div>
          <label class="labelClass">Kelas</label>
          <select v-model="form.class_level" class="inputClass">
            <option value="">-</option>
            <option v-for="c in classes" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="labelClass">Bab / Topik <span class="text-red-500">*</span></label>
          <input v-model="form.topic" type="text" class="inputClass" placeholder="Contoh: Virus" />
        </div>
        <div>
          <label class="labelClass">Estimasi Waktu Belajar</label>
          <input v-model="form.estimated_time" type="text" class="inputClass" placeholder="Contoh: 3 JP / 45 menit" />
        </div>
      </div>

      <div>
        <label class="labelClass">Tujuan Pembelajaran <span class="text-red-500">*</span></label>
        <textarea
          v-model="form.learning_objectives"
          rows="3"
          class="inputClass"
          placeholder="Tulis tujuan pembelajaran, pisahkan dengan baris baru..."
        ></textarea>
      </div>

      <div>
        <label class="labelClass">Kelas Tujuan</label>
        <p class="text-xs text-gray-400 mb-2">
          Pilih kelas yang dapat mengakses materi ini. Kosongkan jika materi bersifat umum.
        </p>
        <div
          class="border border-gray-300 dark:border-gray-700 rounded p-3 bg-white dark:bg-gray-900 flex flex-wrap gap-2"
        >
          <label
            v-for="c in courseOptions"
            :key="c.id"
            class="cursor-pointer flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm transition"
            :class="
              form.course_ids.includes(c.id)
                ? 'bg-green-100 dark:bg-green-900/40 border-green-500 text-green-700 dark:text-green-300'
                : 'border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
            "
          >
            <input
              type="checkbox"
              :value="c.id"
              :checked="form.course_ids.includes(c.id)"
              @change="toggleCourse(c.id)"
              class="accent-green-600"
            />
            {{ c.name }}
            <span class="text-[10px] text-gray-400">{{ c.students }} siswa</span>
          </label>
          <p v-if="courseOptions.length === 0" class="text-sm text-gray-400">
            Belum ada kelas. Buat kelas terlebih dahulu di menu Kelas.
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label class="labelClass">Tingkat Kesulitan</label>
          <select v-model="form.difficulty" class="inputClass">
            <option v-for="d in difficulties" :key="d.value" :value="d.value">{{ d.label }}</option>
          </select>
        </div>
        <div>
          <label class="labelClass">Thumbnail</label>
          <div class="flex items-center gap-3">
            <img
              v-if="form.thumbnail_url"
              :src="form.thumbnail_url"
              class="w-20 h-14 object-cover rounded border border-gray-200 dark:border-gray-700"
            />
            <label
              class="flex-1 cursor-pointer border border-gray-300 dark:border-gray-700 rounded p-2 text-center text-sm text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
            >
              {{
                thumbnailFile
                  ? thumbnailFile.name
                  : form.thumbnail_url
                    ? "Ganti thumbnail"
                    : "Pilih gambar"
              }}
              <input type="file" accept=".jpg,.jpeg,.png,.webp" class="hidden" @change="onThumbnailChange" />
            </label>
          </div>
        </div>
      </div>

      <div class="flex flex-col sm:flex-row gap-3 pt-2">
        <button
          @click="setStatus('draft')"
          :disabled="saving"
          class="flex-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-100 px-4 py-2 rounded-lg font-semibold disabled:opacity-50"
        >
          Simpan Sebagai Draft
        </button>
        <button
          @click="setStatus('published')"
          :disabled="saving"
          class="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-semibold disabled:opacity-50"
        >
          Simpan &amp; Publish
        </button>
      </div>
    </div>
  </div>
</template>