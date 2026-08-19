<script setup>
import { ref } from "vue";
import { uploadFile } from "~/utils/upload";
import { useSwal } from "~/utils/swal";

const props = defineProps({
  materialId: { type: [String, Number], required: true },
  modelValue: { type: String, default: "" },
  accept: { type: String, default: ".pdf,.jpg,.jpeg,.png,.webp,.mp4" },
  previewType: {
    type: String,
    default: "image", // image | video | pdf | auto
  },
});

const emit = defineEmits(["update:modelValue"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();

const fileInput = ref(null);
const uploading = ref(false);
const progress = ref(0);

const isImageUrl = () => /\.(png|jpe?g|webp|gif)(\?|$)/i.test(props.modelValue);
const isPdfUrl = () => /\.pdf(\?|$)/i.test(props.modelValue);
const isVideoUrl = () => /\.mp4|\.webm|\.ogg(\?|$)/i.test(props.modelValue);

const pickFile = () => fileInput.value && fileInput.value.click();

const onFileChange = async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;

  uploading.value = true;
  progress.value = 0;
  try {
    const res = await uploadFile({
      url: `${config.public.backend}/api/materials/${props.materialId}/files`,
      token,
      file,
      onProgress: (p) => (progress.value = p),
    });
    emit("update:modelValue", res.file.file_url);
    toast.add({ title: "File berhasil diunggah.", color: "green" });
  } catch (err) {
    const msg = err && err.error ? err.error : "Gagal mengunggah file.";
    swal.fire({ icon: "error", title: "Gagal", text: msg });
  } finally {
    uploading.value = false;
    progress.value = 0;
  }
};

const clearUrl = () => emit("update:modelValue", "");
</script>

<template>
  <div class="space-y-2">
    <div
      v-if="!modelValue && !uploading"
      @click="pickFile"
      class="border-2 border-dashed border-green-300 dark:border-green-700 rounded-lg p-6 text-center cursor-pointer hover:bg-green-50 dark:hover:bg-green-900/20 transition"
    >
      <Icon name="material-symbols:upload-rounded" class="w-8 h-8 mx-auto text-green-500" />
      <p class="text-sm text-gray-600 dark:text-gray-300 mt-1">
        Klik untuk pilih file
      </p>
      <p class="text-xs text-gray-400">PDF, JPG, PNG, WEBP, MP4 (maks 40MB)</p>
      <input ref="fileInput" type="file" class="hidden" :accept="accept" @change="onFileChange" />
    </div>

    <div v-if="uploading">
      <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div class="h-full bg-green-500 transition-all" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="text-xs text-gray-500 mt-1">Mengunggah... {{ progress }}%</p>
    </div>

    <div v-if="modelValue" class="flex items-center gap-3 p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
      <img
        v-if="previewType === 'image' && isImageUrl()"
        :src="modelValue"
        class="w-16 h-16 object-cover rounded border border-gray-200 dark:border-gray-700"
      />
      <video
        v-else-if="previewType === 'video' && isVideoUrl()"
        :src="modelValue"
        class="w-24 h-16 object-cover rounded bg-black"
        muted
      ></video>
      <span
        v-else
        class="w-12 h-12 rounded flex items-center justify-center text-white text-2xl"
        :class="isPdfUrl() ? 'bg-red-500' : 'bg-green-500'"
      >
        <Icon :name="isPdfUrl() ? 'mdi:file-pdf-box' : 'mdi:file-outline'" class="w-7 h-7" />
      </span>

      <input
        :value="modelValue"
        type="text"
        readonly
        class="flex-1 text-sm bg-transparent text-gray-600 dark:text-gray-300 truncate"
      />

      <div class="flex items-center gap-1">
        <button
          @click="pickFile"
          class="text-xs bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded"
          title="Ganti file"
        >
          Ganti
        </button>
        <button
          @click="clearUrl"
          class="text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 p-1.5 rounded"
          title="Hapus file"
        >
          <Icon name="material-symbols:delete-rounded" class="w-4 h-4" />
        </button>
      </div>
      <input ref="fileInput" type="file" class="hidden" :accept="accept" @change="onFileChange" />
    </div>

    <input
      :value="modelValue"
      @input="emit('update:modelValue', $event.target.value)"
      type="text"
      placeholder="...atau tempel URL manual di sini"
      class="w-full text-sm p-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 focus:outline-green-500"
    />
  </div>
</template>