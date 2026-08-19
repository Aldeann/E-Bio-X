<script setup>
import { ref, computed, watch } from "vue";

const props = defineProps({
  materialId: { type: [Number, String], required: true },
  sectionId: { type: [Number, String], required: true },
  contentId: { type: [Number, String], required: true },
  note: { type: Object, default: null },
});

const emit = defineEmits(["saved"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const open = ref(false);
const draft = ref("");
const saving = ref(false);
const deleting = ref(false);

const noteId = computed(() => (props.note ? props.note.id : null));

watch(
  () => props.note,
  (n) => {
    if (n) draft.value = n.note;
  },
  { immediate: true }
);

const save = async () => {
  const text = draft.value.trim();
  if (!text) {
    toast.add({ title: "Isi catatan terlebih dahulu.", color: "amber" });
    return;
  }
  saving.value = true;
  try {
    if (noteId.value) {
      await $fetch(`${config.public.backend}/api/notes/${noteId.value}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
        body: { note: text },
      });
    } else {
      await $fetch(`${config.public.backend}/api/materials/${props.materialId}/notes`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: { section_id: props.sectionId, content_id: props.contentId, note: text },
      });
    }
    toast.add({ title: "Catatan tersimpan.", color: "green" });
    emit("saved");
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Gagal menyimpan catatan.";
    toast.add({ title: msg, color: "red" });
  } finally {
    saving.value = false;
  }
};

const remove = async () => {
  if (!noteId.value) return;
  deleting.value = true;
  try {
    await $fetch(`${config.public.backend}/api/notes/${noteId.value}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    draft.value = "";
    toast.add({ title: "Catatan dihapus.", color: "green" });
    emit("saved");
  } catch (e) {
    toast.add({ title: "Gagal menghapus catatan.", color: "red" });
  } finally {
    deleting.value = false;
  }
};
</script>

<template>
  <div class="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/20 overflow-hidden">
    <button
      @click="open = !open"
      class="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100/60 dark:hover:bg-blue-900/30 transition"
    >
      <span class="flex items-center gap-2">
        <Icon name="material-symbols:note-add-rounded" class="w-4 h-4" />
        {{ note ? "Catatan Saya" : "Tambah Catatan" }}
      </span>
      <Icon
        :name="open ? 'material-symbols:expand-less' : 'material-symbols:expand-more'"
        class="w-5 h-5"
      />
    </button>

    <div v-if="open" class="px-4 pb-4">
      <textarea
        v-model="draft"
        rows="3"
        class="w-full p-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-sm focus:outline-blue-500 resize-y"
        placeholder="Tulis catatan pribadimu tentang bagian ini..."
      ></textarea>
      <div class="flex items-center gap-2 mt-2">
        <button
          @click="save"
          :disabled="saving"
          class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-xs font-semibold disabled:opacity-50"
        >
          {{ saving ? "Menyimpan..." : "Simpan" }}
        </button>
        <button
          v-if="note"
          @click="remove"
          :disabled="deleting"
          class="bg-red-100 hover:bg-red-200 text-red-600 px-3 py-1.5 rounded text-xs font-semibold disabled:opacity-50"
        >
          {{ deleting ? "Menghapus..." : "Hapus" }}
        </button>
        <span v-if="note" class="text-[11px] text-gray-400 ml-auto">
          Diperbarui {{ new Date(note.updated_at).toLocaleDateString("id-ID") }}
        </span>
      </div>
    </div>
  </div>
</template>