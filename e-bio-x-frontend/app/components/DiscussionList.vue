<template>
  <div class="p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
        <Icon name="mdi:forum-outline" class="text-green-500" /> Forum Diskusi
      </h2>
      <button
        @click="showCreate = !showCreate"
        class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center gap-1 text-sm">
        <Icon name="mdi:message-plus" /> Diskusi Baru
      </button>
    </div>

    <!-- Create Thread Form -->
    <div v-if="showCreate" class="mb-6 p-4 border border-green-200 dark:border-green-800 rounded-lg bg-green-50 dark:bg-gray-800">
      <input
        v-model="newThread.title"
        type="text"
        placeholder="Judul diskusi..."
        class="w-full dark:bg-gray-600 p-2 border rounded-lg border-gray-300 focus:outline-green-500 mb-3" />
      <textarea
        v-model="newThread.content"
        rows="4"
        placeholder="Tulis pertanyaan atau topik diskusi..."
        class="w-full dark:bg-gray-600 p-2 border rounded-lg border-gray-300 focus:outline-green-500 mb-3"></textarea>
      <div class="flex gap-2">
        <button
          @click="createThread"
          :disabled="!newThread.title.trim()"
          class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50">
          Kirim
        </button>
        <button @click="showCreate = false" class="px-4 py-2 rounded-lg bg-gray-300 dark:bg-gray-600 hover:bg-gray-400">
          Batal
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="border rounded-xl p-4 animate-pulse">
        <div class="h-5 bg-green-200 dark:bg-gray-700 rounded w-2/3 mb-2"></div>
        <div class="h-3 bg-green-200 dark:bg-gray-700 rounded w-1/2"></div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <!-- Thread List -->
    <div v-else>
      <div v-if="threads.length === 0" class="text-gray-500">Belum ada diskusi. Mulai diskusi pertama kamu!</div>

      <div v-else class="space-y-3">
        <div
          v-for="thread in threads"
          :key="thread.id"
          class="rounded-xl p-4 shadow-md dark:shadow-green-200 bg-white dark:bg-gray-900 border dark:border-gray-700 hover:shadow-lg transition cursor-pointer"
          @click="openThread(thread.id)">
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <Icon
                  v-if="thread.is_pinned"
                  name="mdi:pin"
                  class="text-red-500 shrink-0" title="Disematkan" />
                <h3 class="font-semibold text-gray-800 dark:text-white truncate">{{ thread.title }}</h3>
              </div>
              <div class="flex items-center gap-1 text-xs text-gray-500">
                <span class="font-medium text-green-600 dark:text-green-400">{{ thread.author }}</span>
                <span>•</span>
                <span>{{ formatDate(thread.created_at) }}</span>
              </div>
              <p v-if="thread.content" class="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">{{ thread.content }}</p>
            </div>

            <div class="flex items-center gap-3 shrink-0">
              <span class="text-sm text-gray-500 flex items-center gap-1">
                <Icon name="mdi:comment-outline" class="text-green-500" />
                {{ thread.replies_count }}
              </span>

              <button
                v-if="role === 'teacher'"
                @click.stop="togglePin(thread)"
                class="p-1 rounded hover:bg-green-100 dark:hover:bg-gray-700"
                :title="thread.is_pinned ? 'Lepas semat' : 'Sematkan'">
                <Icon
                  name="mdi:pin"
                  class="w-5 h-5"
                  :class="thread.is_pinned ? 'text-red-500' : 'text-gray-400'" />
              </button>

              <button
                v-if="thread.can_delete"
                @click.stop="deleteThread(thread)"
                class="p-1 rounded hover:bg-red-100 dark:hover:bg-gray-700"
                title="Hapus diskusi">
                <Icon name="material-symbols:delete-rounded" class="w-5 h-5 text-red-500" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const props = defineProps({
  courseId: {
    type: [String, Number],
    required: true,
  },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const role = useCookie("role").value;
const swal = useSwal();
const toast = useToast();
const router = useRouter();

const threads = ref([]);
const loading = ref(true);
const error = ref(null);
const showCreate = ref(false);
const newThread = ref({ title: "", content: "" });

const fetchThreads = async () => {
  loading.value = true;
  error.value = null;
  try {
    const res = await $fetch(`${config.public.backend}/api/discussions/${props.courseId}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    threads.value = res.data;
  } catch (err) {
    console.error(err);
    error.value = "Gagal memuat forum diskusi.";
  } finally {
    loading.value = false;
  }
};

const createThread = async () => {
  try {
    await $fetch(`${config.public.backend}/api/discussions/${props.courseId}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(newThread.value),
    });
    toast.add({ title: "Diskusi berhasil dibuat.", color: "green" });
    newThread.value = { title: "", content: "" };
    showCreate.value = false;
    fetchThreads();
  } catch (err) {
    toast.add({ title: "Gagal membuat diskusi.", color: "red" });
  }
};

const openThread = (threadId) => {
  router.push(`/${role}/course/${props.courseId}/discussion/${threadId}`);
};

const deleteThread = async (thread) => {
  const result = await swal.fire({
    title: "Hapus diskusi ini?",
    text: `"${thread.title}" beserta seluruh balasannya akan dihapus.`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Ya, hapus!",
    cancelButtonText: "Batal",
  });

  if (!result.isConfirmed) return;

  try {
    await $fetch(`${config.public.backend}/api/discussions/thread/${thread.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Diskusi dihapus.", color: "green" });
    fetchThreads();
  } catch (err) {
    toast.add({ title: "Gagal menghapus diskusi.", color: "red" });
  }
};

const togglePin = async (thread) => {
  try {
    await $fetch(`${config.public.backend}/api/discussions/thread/${thread.id}/pin`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({
      title: thread.is_pinned ? "Semat dilepas." : "Diskusi disematkan.",
      color: "green",
    });
    fetchThreads();
  } catch (err) {
    toast.add({ title: "Gagal mengubah semat.", color: "red" });
  }
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleString("id-ID");
};

fetchThreads();
</script>