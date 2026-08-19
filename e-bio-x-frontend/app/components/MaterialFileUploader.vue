<script setup>
import { ref, onMounted } from "vue";
import { uploadFile, fileSize, allowedFileTypes } from "~/utils/upload";
import { useSwal } from "~/utils/swal";

const props = defineProps({
  materialId: { type: [String, Number], required: true },
});

const emit = defineEmits(["updated"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();

const files = ref([]);
const loading = ref(false);
const uploading = ref(false);
const progress = ref(0);
const fileInput = ref(null);

const fetchFiles = async () => {
  loading.value = true;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/materials/${props.materialId}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    files.value = res.files || [];
  } catch (e) {
    toast.add({ title: "Gagal memuat file.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const pickFile = () => fileInput.value && fileInput.value.click();

const onFileChange = async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;

  const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
  if (!allowedFileTypes.includes(ext)) {
    swal.fire({
      icon: "error",
      title: "Tipe file tidak diizinkan",
      text: "Gunakan PDF, JPG, JPEG, PNG, WEBP, atau MP4.",
    });
    return;
  }

  uploading.value = true;
  progress.value = 0;
  try {
    await uploadFile({
      url: `${config.public.backend}/api/materials/${props.materialId}/files`,
      token,
      file,
      onProgress: (p) => (progress.value = p),
    });
    toast.add({ title: "File berhasil diunggah.", color: "green" });
    await fetchFiles();
    emit("updated", files.value);
  } catch (err) {
    const msg = err && err.error ? err.error : "Gagal mengunggah file.";
    swal.fire({ icon: "error", title: "Gagal", text: msg });
  } finally {
    uploading.value = false;
    progress.value = 0;
  }
};

const removeFile = async (f) => {
  const result = await swal.fire({
    title: "Hapus file ini?",
    text: f.original_name,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;

  try {
    await $fetch(
      `${config.public.backend}/api/materials/${props.materialId}/files/${f.id}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    toast.add({ title: "File dihapus.", color: "green" });
    await fetchFiles();
    emit("updated", files.value);
  } catch (e) {
    toast.add({ title: "Gagal menghapus file.", color: "red" });
  }
};

const isImage = (f) => ["jpg", "jpeg", "png", "webp"].includes((f.file_type || "").toLowerCase());

onMounted(fetchFiles);
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-3">
      <h4 class="font-semibold text-gray-800 dark:text-gray-100 text-sm flex items-center gap-1">
        <Icon name="material-symbols:folder-open" class="w-4 h-4 text-green-500" />
        File Materi
      </h4>
      <button
        @click="pickFile"
        class="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded font-semibold"
      >
        + Upload File
      </button>
      <input ref="fileInput" type="file" class="hidden" :accept="allowedFileTypes.join(',')" @change="onFileChange" />
    </div>

    <div v-if="uploading" class="mb-3">
      <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div class="h-full bg-green-500 transition-all" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="text-xs text-gray-500 mt-1">Mengunggah... {{ progress }}%</p>
    </div>

    <div v-if="!loading && files.length === 0" class="text-sm text-gray-400">
      Belum ada file diunggah.
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="f in files"
        :key="f.id"
        class="flex items-center gap-3 p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800"
      >
        <img
          v-if="isImage(f)"
          :src="f.file_url"
          alt=""
          class="w-10 h-10 object-cover rounded border border-gray-200 dark:border-gray-700"
        />
        <span
          v-else-if="(f.file_type || '').toLowerCase() === 'pdf'"
          class="w-10 h-10 rounded bg-red-100 dark:bg-red-900/40 text-red-600 flex items-center justify-center"
        >
          <Icon name="mdi:file-pdf-box" class="w-6 h-6" />
        </span>
        <span
          v-else
          class="w-10 h-10 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-600 flex items-center justify-center"
        >
          <Icon name="material-symbols:play-circle-outline" class="w-6 h-6" />
        </span>

        <div class="flex-1 min-w-0">
          <a
            :href="f.file_url"
            target="_blank"
            class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate block hover:text-green-600"
          >
            {{ f.original_name }}
          </a>
          <p class="text-xs text-gray-400">{{ fileSize(f.file_size) }}</p>
        </div>

        <a
          :href="f.file_url"
          target="_blank"
          class="text-green-600 hover:text-green-800 p-1"
          title="Buka"
        >
          <Icon name="material-symbols:open-in-new" class="w-4 h-4" />
        </a>
        <button @click="removeFile(f)" class="text-red-500 hover:text-red-700 p-1" title="Hapus">
          <Icon name="material-symbols:delete-rounded" class="w-4 h-4" />
        </button>
      </li>
    </ul>
  </div>
</template>