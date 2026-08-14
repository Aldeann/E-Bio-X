<template>
  <div class="max-w-3xl mx-auto">
    <button
      @click="router.back()"
      class="flex items-center gap-1 text-green-600 dark:text-green-400 hover:underline text-sm mb-4">
      <Icon name="material-symbols:arrow-back-ios-new" class="w-4 h-4" /> Kembali
    </button>

    <div v-if="loading" class="animate-pulse space-y-4">
      <div class="h-8 bg-green-200 dark:bg-gray-700 rounded w-2/3"></div>
      <div class="h-4 bg-green-200 dark:bg-gray-700 rounded w-1/3"></div>
      <div class="h-32 bg-green-200 dark:bg-gray-700 rounded"></div>
    </div>

    <div v-else-if="thread">
      <!-- Thread -->
      <div class="bg-white dark:bg-gray-900 border dark:border-gray-700 rounded-xl p-6 shadow-md dark:shadow-green-200">
        <div class="flex items-center gap-2 mb-2">
          <Icon v-if="thread.is_pinned" name="mdi:pin" class="text-red-500" title="Disematkan" />
          <h1 class="text-2xl font-bold text-gray-800 dark:text-white">{{ thread.title }}</h1>
        </div>
        <div class="flex items-center gap-3 text-sm text-gray-500 mb-4">
          <div class="flex items-center gap-2">
            <UAvatar :alt="thread.author" size="sm" />
            <span class="font-medium text-green-600 dark:text-green-400">{{ thread.author }}</span>
          </div>
          <span>•</span>
          <span>{{ formatDate(thread.created_at) }}</span>
        </div>
        <p class="text-gray-700 dark:text-gray-300 whitespace-pre-line border-t border-gray-100 dark:border-gray-700 pt-4">
          {{ thread.content || "Tanpa deskripsi." }}
        </p>
      </div>

      <!-- Reply Form -->
      <div class="mt-6 bg-white dark:bg-gray-900 border dark:border-gray-700 rounded-xl p-6 shadow-md dark:shadow-green-200">
        <h3 class="font-semibold text-gray-800 dark:text-white mb-3">Balas diskusi ini</h3>
        <textarea
          v-model="replyContent"
          rows="3"
          placeholder="Tulis tanggapanmu..."
          class="w-full dark:bg-gray-600 p-2 border rounded-lg border-gray-300 focus:outline-green-500 mb-3"></textarea>
        <button
          @click="createReply"
          :disabled="!replyContent.trim()"
          class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50">
          Kirim Balasan
        </button>
      </div>

      <!-- Replies -->
      <div class="mt-6 space-y-4">
        <h3 class="font-semibold text-gray-800 dark:text-white">
          {{ thread.replies.length }} Balasan
        </h3>

        <div v-if="thread.replies.length === 0" class="text-gray-500">
          Belum ada balasan.
        </div>

        <div
          v-for="reply in thread.replies"
          :key="reply.id"
          class="bg-white dark:bg-gray-900 border dark:border-gray-700 rounded-xl p-4 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2 text-sm">
              <UAvatar :alt="reply.author" size="sm" />
              <span class="font-medium text-green-600 dark:text-green-400">{{ reply.author }}</span>
              <span class="text-gray-400">•</span>
              <span class="text-gray-400">{{ formatDate(reply.created_at) }}</span>
            </div>
            <button
              v-if="reply.can_delete"
              @click="deleteReply(reply)"
              class="p-1 rounded hover:bg-red-100 dark:hover:bg-gray-700"
              title="Hapus balasan">
              <Icon name="material-symbols:delete-rounded" class="w-5 h-5 text-red-500" />
            </button>
          </div>
          <p class="text-gray-700 dark:text-gray-300 whitespace-pre-line text-sm">{{ reply.content }}</p>
        </div>
      </div>
    </div>

    <div v-else class="text-red-500">Diskusi tidak ditemukan.</div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const props = defineProps({
  courseId: {
    type: [String, Number],
    required: true,
  },
  threadId: {
    type: [String, Number],
    required: true,
  },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();
const router = useRouter();

const thread = ref(null);
const loading = ref(true);
const replyContent = ref("");

const fetchThread = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/discussions/thread/${props.threadId}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    thread.value = res;
  } catch (err) {
    console.error(err);
    toast.add({ title: "Gagal memuat diskusi.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const createReply = async () => {
  try {
    await $fetch(`${config.public.backend}/api/discussions/thread/${props.threadId}/reply`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content: replyContent.value }),
    });
    toast.add({ title: "Balasan terkirim.", color: "green" });
    replyContent.value = "";
    fetchThread();
  } catch (err) {
    toast.add({ title: "Gagal mengirim balasan.", color: "red" });
  }
};

const deleteReply = async (reply) => {
  const result = await swal.fire({
    title: "Hapus balasan ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Ya, hapus!",
    cancelButtonText: "Batal",
  });

  if (!result.isConfirmed) return;

  try {
    await $fetch(`${config.public.backend}/api/discussions/reply/${reply.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Balasan dihapus.", color: "green" });
    fetchThread();
  } catch (err) {
    toast.add({ title: "Gagal menghapus balasan.", color: "red" });
  }
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleString("id-ID");
};

fetchThread();
</script>