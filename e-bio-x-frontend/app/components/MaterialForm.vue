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

const phases = ["E", "F"];
const classes = ["X", "XI", "XII"];
const difficulties = [
  { value: "mudah", label: "Mudah", color: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300" },
  { value: "sedang", label: "Sedang", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300" },
  { value: "sulit", label: "Sulit", color: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" },
];

const inputClass =
  "w-full px-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition";
const selectClass =
  "w-full px-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition appearance-none cursor-pointer";
const labelClass = "block mb-1.5 text-sm font-semibold text-gray-700 dark:text-gray-200";
const sectionTitle = "text-base font-bold text-green-700 dark:text-green-400 flex items-center gap-2 mb-3 pb-2 border-b border-green-100 dark:border-green-900";

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
  <div class="max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold text-green-700 dark:text-green-400 mb-6 flex items-center gap-2">
      <Icon :name="isEdit ? 'material-symbols:edit-document' : 'material-symbols:note-add'" class="w-7 h-7" />
      {{ isEdit ? "Edit Materi" : "Buat Materi Baru" }}
    </h1>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left: Main Form (2 cols wide) -->
      <div class="lg:col-span-2 space-y-5">
        <!-- Section: Informasi Dasar -->
        <div class="bg-white dark:bg-gray-900 rounded-xl shadow border border-green-200 dark:border-green-800 p-5">
          <h3 :class="sectionTitle">
            <Icon name="material-symbols:info" class="w-5 h-5" /> Informasi Dasar
          </h3>
          <div class="space-y-4">
            <div>
              <label :class="labelClass">Judul Materi <span class="text-red-500">*</span></label>
              <input v-model="form.title" type="text" :class="inputClass" placeholder="Contoh: Keanekaragaman Hayati" />
            </div>
            <div>
              <label :class="labelClass">Deskripsi <span class="text-red-500">*</span></label>
              <textarea v-model="form.description" rows="3" :class="inputClass" placeholder="Deskripsi singkat materi..."></textarea>
            </div>
            <div>
              <label :class="labelClass">Tujuan Pembelajaran <span class="text-red-500">*</span></label>
              <textarea
                v-model="form.learning_objectives"
                rows="4"
                :class="inputClass"
                placeholder="Tulis tujuan pembelajaran, pisahkan dengan baris baru..."
              ></textarea>
            </div>
          </div>
        </div>

        <!-- Section: Kelas Tujuan -->
        <div class="bg-white dark:bg-gray-900 rounded-xl shadow border border-green-200 dark:border-green-800 p-5">
          <h3 :class="sectionTitle">
            <Icon name="material-symbols:school" class="w-5 h-5" /> Kelas Tujuan
          </h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
            Pilih kelas yang dapat mengakses materi ini. Kosongkan jika materi bersifat umum.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <label
              v-for="c in courseOptions"
              :key="c.id"
              class="cursor-pointer flex items-center gap-2.5 px-3 py-2.5 rounded-lg border text-sm transition"
              :class="
                form.course_ids.includes(c.id)
                  ? 'bg-green-50 dark:bg-green-900/30 border-green-500 text-green-700 dark:text-green-300 shadow-sm'
                  : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
              "
            >
              <input
                type="checkbox"
                :value="c.id"
                :checked="form.course_ids.includes(c.id)"
                @change="toggleCourse(c.id)"
                class="accent-green-600 w-4 h-4"
              />
              <div class="flex-1 min-w-0">
                <p class="font-medium truncate">{{ c.name }}</p>
                <p class="text-[10px] text-gray-400 dark:text-gray-500">{{ c.students }} siswa</p>
              </div>
            </label>
            <p v-if="courseOptions.length === 0" class="text-sm text-gray-400 dark:text-gray-500 col-span-full text-center py-4">
              Belum ada kelas. Buat kelas terlebih dahulu di menu Kelas.
            </p>
          </div>
        </div>
      </div>

      <!-- Right: Sidebar (1 col wide) -->
      <div class="space-y-5">
        <!-- Section: Pengaturan -->
        <div class="bg-white dark:bg-gray-900 rounded-xl shadow border border-green-200 dark:border-green-800 p-5">
          <h3 :class="sectionTitle">
            <Icon name="material-symbols:settings" class="w-5 h-5" /> Pengaturan
          </h3>
          <div class="space-y-4">
            <div>
              <label :class="labelClass">Mata Pelajaran</label>
              <input v-model="form.subject" type="text" :class="inputClass" placeholder="Biologi" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label :class="labelClass">Fase <span class="text-red-500">*</span></label>
                <select v-model="form.phase" :class="selectClass">
                  <option value="" disabled>Pilih</option>
                  <option v-for="p in phases" :key="p" :value="p">Fase {{ p }}</option>
                </select>
              </div>
              <div>
                <label :class="labelClass">Kelas</label>
                <select v-model="form.class_level" :class="selectClass">
                  <option value="">-</option>
                  <option v-for="c in classes" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
            </div>
            <div>
              <label :class="labelClass">Bab / Topik <span class="text-red-500">*</span></label>
              <input v-model="form.topic" type="text" :class="inputClass" placeholder="Contoh: Virus" />
            </div>
            <div>
              <label :class="labelClass">Estimasi Waktu</label>
              <input v-model="form.estimated_time" type="text" :class="inputClass" placeholder="Contoh: 3 JP" />
            </div>
            <div>
              <label :class="labelClass">Tingkat Kesulitan</label>
              <div class="flex gap-2">
                <button
                  v-for="d in difficulties"
                  :key="d.value"
                  type="button"
                  @click="form.difficulty = d.value"
                  class="flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition"
                  :class="
                    form.difficulty === d.value
                      ? d.color + ' border-current shadow-sm'
                      : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'
                  "
                >
                  {{ d.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Section: Thumbnail -->
        <div class="bg-white dark:bg-gray-900 rounded-xl shadow border border-green-200 dark:border-green-800 p-5">
          <h3 :class="sectionTitle">
            <Icon name="material-symbols:image" class="w-5 h-5" /> Thumbnail
          </h3>
          <div class="space-y-3">
            <div
              v-if="form.thumbnail_url && !thumbnailFile"
              class="relative rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700"
            >
              <img :src="form.thumbnail_url" class="w-full h-32 object-cover" />
              <button
                @click="form.thumbnail_url = ''"
                class="absolute top-1.5 right-1.5 w-6 h-6 rounded-full bg-red-500 text-white flex items-center justify-center text-xs hover:bg-red-600"
              >
                <Icon name="material-symbols:close" class="w-3.5 h-3.5" />
              </button>
            </div>
            <label
              class="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer transition"
              :class="thumbnailFile
                ? 'border-green-400 bg-green-50 dark:bg-green-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-green-400 hover:bg-green-50 dark:hover:bg-green-900/10'"
            >
              <Icon name="material-symbols:cloud-upload" class="w-6 h-6 text-gray-400 dark:text-gray-500 mb-1" />
              <span class="text-xs text-gray-500 dark:text-gray-400 text-center px-2">
                {{ thumbnailFile ? thumbnailFile.name : "Klik untuk unggah gambar" }}
              </span>
              <span class="text-[10px] text-gray-400 dark:text-gray-500">JPG, PNG, WEBP</span>
              <input type="file" accept=".jpg,.jpeg,.png,.webp" class="hidden" @change="onThumbnailChange" />
            </label>
          </div>
        </div>

        <!-- Section: Aksi -->
        <div class="bg-white dark:bg-gray-900 rounded-xl shadow border border-green-200 dark:border-green-800 p-5">
          <h3 :class="sectionTitle">
            <Icon name="material-symbols:save" class="w-5 h-5" /> Simpan
          </h3>
          <div class="space-y-2">
            <button
              @click="setStatus('draft')"
              :disabled="saving"
              class="w-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 px-4 py-2.5 rounded-lg font-semibold text-sm disabled:opacity-50 transition flex items-center justify-center gap-2"
            >
              <Icon name="material-symbols:draft" class="w-4 h-4" />
              {{ saving ? "Menyimpan..." : "Simpan Draft" }}
            </button>
            <button
              @click="setStatus('published')"
              :disabled="saving"
              class="w-full bg-green-600 hover:bg-green-700 text-white px-4 py-2.5 rounded-lg font-semibold text-sm disabled:opacity-50 transition flex items-center justify-center gap-2 shadow-md shadow-green-300/50"
            >
              <Icon name="material-symbols:publish" class="w-4 h-4" />
              {{ saving ? "Menyimpan..." : "Simpan & Publish" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
