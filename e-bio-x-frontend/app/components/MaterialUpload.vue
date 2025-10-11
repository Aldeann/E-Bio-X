<template>
  <div class="p-6 bg-white dark:bg-gray-900 rounded-xl shadow-lg dark:shadow-green-400 dark:border-none border border-green-200">
    <h2 class="text-xl font-semibold text-green-700 dark:text-green-400 flex items-center gap-2">
      <Icon name="material-symbols:upload-rounded" class="text-green-500" /> Upload Materi
    </h2>

    <div class="p-4">
      <form @submit.prevent="handleUpload" class="space-y-4">
        <div>
          <label class="block mb-1 text-green-700 dark:text-green-400 font-medium">Judul Materi</label>
          <input
            v-model="title"
            type="text"
            class="w-full dark:bg-gray-600 p-2 border-gray-300 dark:border-gray-700 border rounded-lg focus:outline-green-500"
            required />
        </div>

        <div>
          <label class="block mb-1 text-green-700 dark:text-green-400 font-medium">Deskripsi (opsional)</label>
          <textarea
            v-model="content"
            class="w-full dark:bg-gray-600 p-2 border-gray-300 dark:border-gray-700 border rounded-lg focus:outline-green-500"></textarea>
        </div>

        <div>
          <label class="block mb-1 text-green-700 dark:text-green-400 font-medium">File (PDF / PPT)</label>
          <input
            @change="handleFileChange"
            type="file"
            accept=".pdf,.ppt,.pptx"
            class="w-full dark:bg-gray-600 p-2 border-gray-300 dark:border-gray-700 border rounded-lg file:mr-4 file:bg-green-600 file:text-white file:border-none file:px-4 file:py-2 file:rounded-full file:cursor-pointer"
            required />
        </div>

        <button
          type="submit"
          class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-semibold w-full">
          <Icon name="material-symbols:upload-rounded" /> Upload
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useSwal } from "~/utils/swal";

const swal = useSwal();
const token = useCookie("access_token").value;
const props = defineProps({
  courseId: {
    type: String,
    required: true,
  },
});
const title = ref("");
const content = ref("");
const file = ref(null);

const handleFileChange = (e) => {
  const selectedFile = e.target.files[0];
  if (selectedFile) {
    file.value = selectedFile;
  }
};

const handleUpload = async () => {
  if (!file.value) return swal.fire({ icon: "error", title: "File belum dipilih" });

  const formData = new FormData();
  formData.append("title", title.value);
  formData.append("content", content.value);
  formData.append("course_id", Number(props.courseId));
  formData.append("file", file.value);

  swal.fire({
    title: "Mengupload...",
    text: "Mohon tunggu",
    allowOutsideClick: false,
    didOpen: () => {
      swal.showLoading();
    },
  });

  try {
    await $fetch(`${useRuntimeConfig().public.backend}/api/materials`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    title.value = "";
    content.value = "";
    file.value = null;
    document.querySelector('input[type="file"]').value = "";

    swal.fire({
      icon: "success",
      title: "Berhasil",
      text: "Materi berhasil diunggah",
    });
  } catch (err) {
    // console.error("Gagal upload materi:", err);
    swal.fire({
      icon: "error",
      title: "Gagal",
      text: "Terjadi kesalahan saat upload materi",
    });
  }
};
</script>
