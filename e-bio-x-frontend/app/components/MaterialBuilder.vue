<script setup>
import { ref, computed, onMounted } from "vue";
import { useSwal } from "~/utils/swal";
import {
  builtinTemplates,
  loadSavedTemplates,
  saveBlockTemplate,
  removeSavedTemplate,
} from "~/utils/blockTemplates";

const props = defineProps({
  materialId: { type: [String, Number], required: true },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();

const material = ref(null);
const loading = ref(true);
const activeSectionId = ref(null);
const editingContentId = ref(null);
const showPicker = ref(false);
const pickerSectionId = ref(null);
const showFiles = ref(false);
const savingTitle = ref(false);
const savedTemplates = ref([]);

const componentTypes = [
  { type: "text", label: "Text", icon: "material-symbols:notes-rounded" },
  { type: "heading", label: "Heading", icon: "material-symbols:title" },
  { type: "image", label: "Gambar", icon: "material-symbols:image-outline" },
  { type: "video", label: "Video", icon: "material-symbols:smart-display-outline" },
  { type: "pdf", label: "PDF", icon: "material-symbols:picture-as-pdf" },
  { type: "link", label: "Tautan", icon: "material-symbols:link-rounded" },
  { type: "box", label: "Info Box", icon: "material-symbols:info-outline" },
  { type: "question", label: "Pertanyaan", icon: "material-symbols:quiz-outline" },
  { type: "quiz", label: "Quiz", icon: "hugeicons:quiz-04" },
  { type: "diagram", label: "Diagram Interaktif", icon: "material-symbols:schema" },
];

const sections = computed(() => material.value?.sections || []);
const activeSection = computed(
  () => sections.value.find((s) => s.id === activeSectionId.value) || null
);

const blockTemplate = (type) => {
  const templates = {
    text: { content: "" },
    heading: { content: "", level: 2 },
    image: { url: "", caption: "" },
    video: { url: "", title: "" },
    pdf: { url: "", title: "" },
    link: { url: "", label: "" },
    box: { content: "", variant: "info" },
    question: {
      qtype: "multiple_choice",
      question: "",
      options: ["", ""],
      correct_answer: 0,
      explanation: "",
    },
    quiz: {
      title: "Latihan Soal",
      questions: [
        {
          qtype: "multiple_choice",
          question: "",
          options: ["", ""],
          correct_answer: 0,
          explanation: "",
        },
      ],
    },
    diagram: { url: "", title: "", points: [], explanation: "" },
  };
  return templates[type] || {};
};

const typeLabel = (type) => {
  const found = componentTypes.find((c) => c.type === type);
  return found ? found.label : type;
};

const fetchDetail = async () => {
  loading.value = true;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/materials/${props.materialId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    material.value = res;
    if (!activeSectionId.value && res.sections.length > 0) {
      activeSectionId.value = res.sections[0].id;
    }
  } catch (e) {
    toast.add({ title: "Gagal memuat materi.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const selectSection = (id) => {
  activeSectionId.value = id;
  editingContentId.value = null;
};

// ---------- SECTIONS ----------
const addSection = async () => {
  const { value } = await swal.fire({
    title: "Tambah Section",
    input: "text",
    inputPlaceholder: "Contoh: 01 Pengertian Virus",
    showCancelButton: true,
    confirmButtonText: "Tambah",
    cancelButtonText: "Batal",
    inputValidator: (v) => (!v || !v.trim() ? "Nama section wajib diisi" : null),
  });
  if (!value) return;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/materials/${props.materialId}/sections`,
      { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: { title: value } }
    );
    await fetchDetail();
    activeSectionId.value = res.section.id;
    toast.add({ title: "Section ditambahkan.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal menambah section.", color: "red" });
  }
};

const renameSection = async (section) => {
  const { value } = await swal.fire({
    title: "Edit Nama Section",
    input: "text",
    inputValue: section.title,
    showCancelButton: true,
    confirmButtonText: "Simpan",
    cancelButtonText: "Batal",
    inputValidator: (v) => (!v || !v.trim() ? "Nama section wajib diisi" : null),
  });
  if (!value) return;
  try {
    await $fetch(`${config.public.backend}/api/sections/${section.id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: { title: value },
    });
    await fetchDetail();
    toast.add({ title: "Section diperbarui.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal memperbarui section.", color: "red" });
  }
};

const deleteSection = async (section) => {
  const result = await swal.fire({
    title: "Hapus section ini?",
    text: `"${section.title}" beserta semua isinya akan dihapus.`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/sections/${section.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (activeSectionId.value === section.id) activeSectionId.value = null;
    await fetchDetail();
    toast.add({ title: "Section dihapus.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal menghapus section.", color: "red" });
  }
};

const moveSection = async (index, dir) => {
  const ids = sections.value.map((s) => s.id);
  const target = index + dir;
  if (target < 0 || target >= ids.length) return;
  const [removed] = ids.splice(index, 1);
  ids.splice(target, 0, removed);
  try {
    await $fetch(`${config.public.backend}/api/materials/${props.materialId}/sections/reorder`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { section_ids: ids },
    });
    await fetchDetail();
  } catch (e) {
    toast.add({ title: "Gagal mengubah urutan.", color: "red" });
  }
};

// ---------- BLOCKS ----------
const openPicker = (sectionId) => {
  pickerSectionId.value = sectionId;
  showPicker.value = true;
};

const addBlock = async (type, data = null) => {
  const sectionId = pickerSectionId.value;
  showPicker.value = false;
  if (!sectionId) return;
  try {
    const res = await $fetch(`${config.public.backend}/api/sections/${sectionId}/contents`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { type, data: data || blockTemplate(type) },
    });
    await fetchDetail();
    editingContentId.value = res.content.id;
    toast.add({ title: "Komponen ditambahkan.", color: "green" });
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Gagal menambah komponen.";
    toast.add({ title: msg, color: "red" });
  }
};

const saveBlock = async (content, payload) => {
  try {
    const res = await $fetch(`${config.public.backend}/api/contents/${content.id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: payload,
    });
    await fetchDetail();
    editingContentId.value = null;
    toast.add({ title: "Komponen disimpan.", color: "green" });
    return res;
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Gagal menyimpan komponen.";
    toast.add({ title: msg, color: "red" });
  }
};

const deleteBlock = async (content) => {
  const result = await swal.fire({
    title: "Hapus komponen ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/contents/${content.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (editingContentId.value === content.id) editingContentId.value = null;
    await fetchDetail();
    toast.add({ title: "Komponen dihapus.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal menghapus komponen.", color: "red" });
  }
};

const moveBlock = async (section, index, dir) => {
  const ids = section.contents.map((c) => c.id);
  const target = index + dir;
  if (target < 0 || target >= ids.length) return;
  const [removed] = ids.splice(index, 1);
  ids.splice(target, 0, removed);
  try {
    await $fetch(`${config.public.backend}/api/sections/${section.id}/contents/reorder`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { content_ids: ids },
    });
    await fetchDetail();
  } catch (e) {
    toast.add({ title: "Gagal mengubah urutan.", color: "red" });
  }
};

// ---------- DUPLICATE & TEMPLATE ----------
const duplicateSection = async (section) => {
  try {
    await $fetch(`${config.public.backend}/api/sections/${section.id}/duplicate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    await fetchDetail();
    toast.add({ title: "Section diduplikasi.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal menduplikasi section.", color: "red" });
  }
};

const duplicateBlock = async (content) => {
  try {
    const res = await $fetch(`${config.public.backend}/api/contents/${content.id}/duplicate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    await fetchDetail();
    editingContentId.value = res.content.id;
    toast.add({ title: "Komponen diduplikasi.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal menduplikasi komponen.", color: "red" });
  }
};

const saveAsTemplate = async (content) => {
  const { value } = await swal.fire({
    title: "Simpan sebagai Template",
    input: "text",
    inputValue: `${typeLabel(content.type)} Template`,
    showCancelButton: true,
    confirmButtonText: "Simpan",
    cancelButtonText: "Batal",
    inputValidator: (v) => (!v || !v.trim() ? "Nama template wajib diisi" : null),
  });
  if (!value) return;
  savedTemplates.value = saveBlockTemplate({
    name: value.trim(),
    type: content.type,
    data: content.data,
  });
  toast.add({ title: "Template disimpan ke peramban ini.", color: "green" });
};

const deleteSavedTemplate = async (t) => {
  const result = await swal.fire({
    title: "Hapus template ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  savedTemplates.value = removeSavedTemplate(t.key);
  toast.add({ title: "Template dihapus.", color: "green" });
};

// ---------- DRAG & DROP ----------
const dragSectionIndex = ref(null);
const overSectionIndex = ref(null);
const dragBlockIndex = ref(null);
const overBlockIndex = ref(null);

const dragStartSection = (index, e) => {
  dragSectionIndex.value = index;
  if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
};

const dragOverSection = (index, e) => {
  e.preventDefault();
  overSectionIndex.value = index;
  if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
};

const dropSection = async (index, e) => {
  e.preventDefault();
  overSectionIndex.value = null;
  const from = dragSectionIndex.value;
  dragSectionIndex.value = null;
  if (from === null || from === index) return;
  const ids = sections.value.map((s) => s.id);
  const [removed] = ids.splice(from, 1);
  ids.splice(index, 0, removed);
  try {
    await $fetch(`${config.public.backend}/api/materials/${props.materialId}/sections/reorder`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { section_ids: ids },
    });
    await fetchDetail();
  } catch (err) {
    toast.add({ title: "Gagal mengubah urutan.", color: "red" });
  }
};

const dragStartBlock = (index, e) => {
  dragBlockIndex.value = index;
  if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
};

const dragOverBlock = (index, e) => {
  e.preventDefault();
  overBlockIndex.value = index;
  if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
};

const dropBlock = async (index, e) => {
  e.preventDefault();
  overBlockIndex.value = null;
  const from = dragBlockIndex.value;
  dragBlockIndex.value = null;
  if (from === null || from === index) return;
  const ids = activeSection.value.contents.map((c) => c.id);
  const [removed] = ids.splice(from, 1);
  ids.splice(index, 0, removed);
  try {
    await $fetch(
      `${config.public.backend}/api/sections/${activeSection.value.id}/contents/reorder`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: { content_ids: ids },
      }
    );
    await fetchDetail();
  } catch (err) {
    toast.add({ title: "Gagal mengubah urutan.", color: "red" });
  }
};

// ---------- HEADER ACTIONS ----------
const saveTitle = async () => {
  savingTitle.value = true;
  try {
    await $fetch(`${config.public.backend}/api/materials/${props.materialId}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: { title: material.value.title },
    });
    toast.add({ title: "Judul disimpan.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal menyimpan judul.", color: "red" });
  } finally {
    savingTitle.value = false;
  }
};

const togglePublish = async () => {
  const next = material.value.status === "published" ? "draft" : "published";
  const action = next === "published" ? "mempublikasikan" : "menyimpan sebagai draft";
  const result = await swal.fire({
    title: next === "published" ? "Publikasikan materi ini?" : "Batalkan publikasi?",
    text: `Materi akan ${action}${next === "published" ? " dan dapat diakses siswa" : " dan disembunyikan dari siswa"}.`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: next === "published" ? "Ya, Publikasikan" : "Ya, Arsipkan",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    const res = await $fetch(`${config.public.backend}/api/materials/${props.materialId}/publish`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
      body: { status: next },
    });
    await fetchDetail();
    toast.add({ title: res.message, color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal mengubah status.", color: "red" });
  }
};

onMounted(() => {
  savedTemplates.value = loadSavedTemplates();
  fetchDetail();
});
</script>

<template>
  <div v-if="loading" class="flex justify-center py-20 text-green-600">
    <Icon name="mdi:loading" class="w-10 h-10 animate-spin" />
  </div>

  <template v-else-if="material">
    <!-- Header -->
    <div class="mb-6">
      <NuxtLink
        to="/teacher/materials"
        class="text-sm text-green-600 hover:underline flex items-center gap-1 mb-2"
      >
        <Icon name="material-symbols:arrow-back" class="w-4 h-4" />
        Kembali ke Materi
      </NuxtLink>

      <div class="flex flex-col md:flex-row md:items-center gap-3">
        <div class="flex-1 flex items-center gap-2">
          <input
            v-model="material.title"
            type="text"
            class="text-2xl font-bold text-gray-800 dark:text-gray-100 flex-1 bg-transparent border-b-2 border-transparent focus:border-green-400 focus:outline-none"
          />
          <button
            @click="saveTitle"
            :disabled="savingTitle"
            class="text-green-600 hover:text-green-700"
            title="Simpan judul"
          >
            <Icon name="material-symbols:save" class="w-5 h-5" />
          </button>
        </div>

        <div class="flex flex-wrap gap-2">
          <span
            class="px-3 py-1.5 rounded-full text-xs font-semibold"
            :class="
              material.status === 'published'
                ? 'bg-green-100 text-green-700'
                : 'bg-amber-100 text-amber-700'
            "
          >
            {{ material.status === "published" ? "Published" : "Draft" }}
          </span>
          <button
            @click="togglePublish"
            class="px-3 py-1.5 rounded-lg text-sm font-semibold text-white"
            :class="
              material.status === 'published'
                ? 'bg-amber-500 hover:bg-amber-600'
                : 'bg-green-600 hover:bg-green-700'
            "
          >
            {{ material.status === "published" ? "Unpublish" : "Publish" }}
          </button>
          <NuxtLink
            :to="`/teacher/materials/preview/${material.id}`"
            target="_blank"
            class="px-3 py-1.5 rounded-lg text-sm font-semibold bg-blue-500 hover:bg-blue-600 text-white"
          >
            <span class="inline-flex items-center gap-1">
              <Icon name="material-symbols:visibility" class="w-4 h-4" />
              Preview sebagai Siswa
            </span>
          </NuxtLink>
          <NuxtLink
            :to="`/teacher/materials/edit/${material.id}`"
            class="px-3 py-1.5 rounded-lg text-sm font-semibold bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-100"
          >
            Metadata
          </NuxtLink>
          <button
            @click="showFiles = !showFiles"
            class="px-3 py-1.5 rounded-lg text-sm font-semibold bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-100"
          >
            File
          </button>
        </div>
      </div>

      <p v-if="material.description" class="text-sm text-gray-500 mt-2">
        {{ material.description }}
      </p>
    </div>

    <div v-if="showFiles" class="mb-6 p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <MaterialFileUploader :material-id="material.id" />
    </div>

    <!-- Body -->
    <div class="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6 items-start">
      <!-- Sections sidebar -->
      <aside class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold text-gray-800 dark:text-gray-100 flex items-center gap-1">
            <Icon name="material-symbols:format-list-numbered" class="w-5 h-5 text-green-500" />
            Section Materi
          </h3>
          <button
            @click="addSection"
            class="text-green-600 hover:text-green-700 text-sm font-semibold"
            title="Tambah section"
          >
            <Icon name="material-symbols:add-circle" class="w-6 h-6" />
          </button>
        </div>

        <div v-if="sections.length === 0" class="text-sm text-gray-400">
          Belum ada section. Klik + untuk menambahkan.
        </div>

        <ul v-else class="space-y-2">
          <li
            v-for="(section, index) in sections"
            :key="section.id"
            draggable="true"
            class="group rounded-lg border transition cursor-grab"
            :class="[
              activeSectionId === section.id
                ? 'border-green-300 bg-green-50 dark:bg-green-900/30'
                : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800',
              overSectionIndex === index ? 'ring-2 ring-green-300 dark:ring-green-600 opacity-80' : '',
            ]"
            @dragstart="dragStartSection(index, $event)"
            @dragover="dragOverSection(index, $event)"
            @drop="dropSection(index, $event)"
          >
            <button
              @click="selectSection(section.id)"
              class="w-full flex items-center gap-2 px-3 py-2 text-left"
            >
              <span
                class="w-7 h-7 shrink-0 rounded-full bg-green-600 text-white text-xs font-bold flex items-center justify-center"
              >
                {{ index + 1 }}
              </span>
              <span
                class="flex-1 text-sm text-gray-700 dark:text-gray-200 truncate"
                :title="section.title"
              >
                {{ section.title }}
              </span>
            </button>
            <div
              class="flex items-center justify-between px-3 pb-2"
              :class="activeSectionId === section.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'"
            >
              <div class="flex items-center gap-1">
                <button
                  @click="moveSection(index, -1)"
                  :disabled="index === 0"
                  class="text-gray-400 hover:text-green-600 disabled:opacity-30"
                  title="Naik"
                >
                  <Icon name="material-symbols:arrow-upward" class="w-4 h-4" />
                </button>
                <button
                  @click="moveSection(index, 1)"
                  :disabled="index === sections.length - 1"
                  class="text-gray-400 hover:text-green-600 disabled:opacity-30"
                  title="Turun"
                >
                  <Icon name="material-symbols:arrow-downward" class="w-4 h-4" />
                </button>
              </div>
              <div class="flex items-center gap-1">
                <button @click="duplicateSection(section)" class="text-violet-500 hover:text-violet-700" title="Duplikasi section">
                  <Icon name="material-symbols:content-copy" class="w-4 h-4" />
                </button>
                <button @click="renameSection(section)" class="text-blue-500 hover:text-blue-700" title="Edit nama">
                  <Icon name="material-symbols:edit-square" class="w-4 h-4" />
                </button>
                <button @click="deleteSection(section)" class="text-red-500 hover:text-red-700" title="Hapus">
                  <Icon name="material-symbols:delete-rounded" class="w-4 h-4" />
                </button>
              </div>
            </div>
          </li>
        </ul>
      </aside>

      <!-- Blocks area -->
      <section class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
        <template v-if="!activeSection">
          <div class="text-center py-16 text-gray-400">
            <Icon name="material-symbols:data-object" class="w-12 h-12 mx-auto mb-2" />
            <p>Pilih sebuah section untuk mulai menyusun konten.</p>
          </div>
        </template>

        <template v-else>
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-bold text-green-700 dark:text-green-400">
              {{ activeSection.title }}
            </h2>
            <span class="text-xs text-gray-400">{{ activeSection.contents.length }} komponen</span>
          </div>

          <div v-if="activeSection.contents.length === 0" class="text-center py-10 text-gray-400 mb-4">
            <Icon name="material-symbols:library-add" class="w-10 h-10 mx-auto mb-2" />
            <p>Section ini masih kosong.</p>
          </div>

          <div class="space-y-3">
            <div
              v-for="(content, index) in activeSection.contents"
              :key="content.id"
              draggable="true"
              class="group relative rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4 cursor-grab"
              :class="overBlockIndex === index ? 'ring-2 ring-green-300 dark:ring-green-600 opacity-80' : ''"
              @dragstart="dragStartBlock(index, $event)"
              @dragover="dragOverBlock(index, $event)"
              @drop="dropBlock(index, $event)"
            >
              <!-- block toolbar -->
              <div
                class="absolute -top-3 right-3 flex items-center gap-1 bg-white dark:bg-gray-700 rounded-full border border-gray-200 dark:border-gray-600 px-1 py-0.5 shadow opacity-100 md:opacity-0 md:group-hover:opacity-100 transition"
              >
                <button
                  @click="moveBlock(activeSection, index, -1)"
                  :disabled="index === 0"
                  class="text-gray-500 hover:text-green-600 disabled:opacity-30 p-0.5"
                  title="Pindah ke atas"
                >
                  <Icon name="material-symbols:arrow-upward" class="w-4 h-4" />
                </button>
                <button
                  @click="moveBlock(activeSection, index, 1)"
                  :disabled="index === activeSection.contents.length - 1"
                  class="text-gray-500 hover:text-green-600 disabled:opacity-30 p-0.5"
                  title="Pindah ke bawah"
                >
                  <Icon name="material-symbols:arrow-downward" class="w-4 h-4" />
                </button>
                <button
                  @click="editingContentId = editingContentId === content.id ? null : content.id"
                  class="text-blue-500 hover:text-blue-700 p-0.5"
                  :title="editingContentId === content.id ? 'Tutup editor' : 'Edit'"
                >
                  <Icon name="material-symbols:edit-square" class="w-4 h-4" />
                </button>
                <button
                  @click="duplicateBlock(content)"
                  class="text-violet-500 hover:text-violet-700 p-0.5"
                  title="Duplikasi komponen"
                >
                  <Icon name="material-symbols:content-copy" class="w-4 h-4" />
                </button>
                <button
                  @click="saveAsTemplate(content)"
                  class="text-amber-500 hover:text-amber-700 p-0.5"
                  title="Simpan sebagai template"
                >
                  <Icon name="material-symbols:bookmark-add" class="w-4 h-4" />
                </button>
                <button
                  @click="deleteBlock(content)"
                  class="text-red-500 hover:text-red-700 p-0.5"
                  title="Hapus"
                >
                  <Icon name="material-symbols:delete-rounded" class="w-4 h-4" />
                </button>
              </div>

              <div class="flex items-center gap-2 mb-2">
                <span
                  class="text-[10px] uppercase tracking-wide font-bold px-2 py-0.5 rounded bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300"
                >
                  {{ typeLabel(content.type) }}
                </span>
              </div>

              <MaterialBlockForm
                v-if="editingContentId === content.id"
                :block="content"
                :material-id="material.id"
                @save="saveBlock(content, $event)"
                @cancel="editingContentId = null"
              />
              <MaterialContentViewer
                v-else
                :block="content"
                :interactive="false"
              />
            </div>
          </div>

          <button
            @click="openPicker(activeSection.id)"
            class="mt-4 w-full border-2 border-dashed border-green-300 dark:border-green-700 rounded-xl py-4 text-green-600 dark:text-green-400 font-semibold hover:bg-green-50 dark:hover:bg-green-900/20 transition flex items-center justify-center gap-2"
          >
            <Icon name="material-symbols:add-circle" class="w-6 h-6" />
            Tambahkan Komponen
          </button>
        </template>
      </section>
    </div>

    <!-- Component picker modal -->
    <div
      v-if="showPicker"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      @click.self="showPicker = false"
    >
      <div class="w-full max-w-lg bg-white dark:bg-gray-900 rounded-2xl p-6 shadow-xl max-h-[85vh] overflow-y-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-gray-800 dark:text-gray-100">
            Pilih Komponen
          </h3>
          <button @click="showPicker = false" class="text-gray-400 hover:text-gray-600">
            <Icon name="material-symbols:close" class="w-6 h-6" />
          </button>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <button
            v-for="c in componentTypes"
            :key="c.type"
            @click="addBlock(c.type)"
            class="flex flex-col items-center gap-2 p-4 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition"
          >
            <Icon :name="c.icon" class="w-8 h-8 text-green-600 dark:text-green-400" />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-200">{{ c.label }}</span>
          </button>
        </div>

        <div class="mt-6">
          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1 mb-3">
            <Icon name="material-symbols:template" class="w-5 h-5 text-amber-500" />
            Template
          </h4>

          <div v-if="savedTemplates.length" class="mb-3">
            <p class="text-xs text-gray-400 mb-1">Disimpan di peramban ini</p>
            <div class="space-y-1.5">
              <div
                v-for="t in savedTemplates"
                :key="t.key"
                class="flex items-center gap-2 p-2 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <Icon name="material-symbols:template" class="w-5 h-5 text-amber-500 shrink-0" />
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{{ t.name }}</p>
                  <p class="text-xs text-gray-400">{{ typeLabel(t.type) }}</p>
                </div>
                <button
                  @click="addBlock(t.type, t.data)"
                  class="text-green-600 hover:text-green-700 text-sm font-semibold shrink-0"
                >
                  Pakai
                </button>
                <button
                  @click="deleteSavedTemplate(t)"
                  class="text-red-500 hover:text-red-700 shrink-0"
                  title="Hapus template"
                >
                  <Icon name="material-symbols:delete-rounded" class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <button
              v-for="t in builtinTemplates"
              :key="t.key"
              @click="addBlock(t.type, t.data)"
              class="flex flex-col items-center gap-1 p-3 rounded-xl border border-dashed border-amber-300 dark:border-amber-700 hover:border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition"
            >
              <Icon :name="t.icon" class="w-6 h-6 text-amber-500" />
              <span class="text-xs font-medium text-gray-700 dark:text-gray-200 text-center">{{ t.label }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </template>
</template>