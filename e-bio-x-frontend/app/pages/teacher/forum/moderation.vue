<template>
  <div class="container mx-auto px-4 py-6">
    <h1 class="text-3xl font-bold text-green-500 mb-4 flex items-center gap-2">
      <Icon name="mdi:shield-alert-outline" /> Moderasi Forum
    </h1>

    <div class="grid grid-cols-3 gap-3 mb-6">
      <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 text-center shadow-sm">
        <p class="text-2xl font-bold text-amber-500">{{ data.reported_posts?.length || 0 }}</p>
        <p class="text-xs text-gray-500">Postingan Dilaporkan</p>
      </div>
      <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 text-center shadow-sm">
        <p class="text-2xl font-bold text-sky-500">{{ data.unanswered_questions?.length || 0 }}</p>
        <p class="text-xs text-gray-500">Pertanyaan Belum Terjawab</p>
      </div>
      <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 text-center shadow-sm">
        <p class="text-2xl font-bold text-green-500">{{ (data.active_forums || 0) + (data.closed_forums || 0) }}</p>
        <p class="text-xs text-gray-500">Total Forum ({{ data.active_forums }} aktif)</p>
      </div>
    </div>

    <div v-if="loading" class="animate-pulse space-y-3">
      <div v-for="i in 3" :key="i" class="h-24 bg-green-200 dark:bg-gray-700 rounded-xl"></div>
    </div>

    <div v-else class="space-y-6">
      <!-- Reported posts -->
      <section>
        <h2 class="font-semibold text-amber-700 dark:text-amber-300 mb-3 flex items-center gap-2">
          <Icon name="mdi:flag-outline" /> Laporan Postingan
        </h2>
        <div v-if="!data.reported_posts?.length" class="text-gray-500 text-sm">Tidak ada laporan menunggu.</div>
        <div v-else class="space-y-3">
          <div v-for="r in data.reported_posts" :key="r.id" class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
            <div class="flex items-center justify-between gap-3 flex-wrap">
              <div class="min-w-0">
                <p class="text-xs text-gray-500">{{ r.forum_title }} • oleh {{ r.author_name }}</p>
                <p class="text-sm text-gray-800 dark:text-gray-200 mt-1 line-clamp-3">{{ r.post_content }}</p>
                <p class="text-xs mt-2">
                  <span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 font-semibold uppercase">{{ r.reason }}</span>
                  <span class="text-gray-400 ml-2">dilaporkan {{ r.reported_by }} • {{ formatDate(r.created_at) }}</span>
                </p>
                <p v-if="r.description" class="text-xs text-gray-500 mt-1 italic">"{{ r.description }}"</p>
              </div>
              <div class="flex gap-2 shrink-0">
                <button @click="moderate(r.post_id, 'HIDE')" class="px-3 py-1.5 rounded-lg text-xs bg-amber-600 text-white hover:bg-amber-700">Sembunyikan</button>
                <button @click="moderate(r.post_id, 'DELETE')" class="px-3 py-1.5 rounded-lg text-xs bg-red-600 text-white hover:bg-red-700">Hapus</button>
                <button @click="moderate(r.post_id, 'RESTORE')" class="px-3 py-1.5 rounded-lg text-xs bg-gray-200 dark:bg-gray-700 hover:bg-gray-300">Biarkan</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Unanswered questions -->
      <section>
        <h2 class="font-semibold text-sky-700 dark:text-sky-300 mb-3 flex items-center gap-2">
          <Icon name="mdi:comment-question-outline" /> Pertanyaan Menunggu Jawaban
        </h2>
        <div v-if="!data.unanswered_questions?.length" class="text-gray-500 text-sm">Semua pertanyaan sudah terjawab.</div>
        <div v-else class="space-y-3">
          <div v-for="q in data.unanswered_questions" :key="q.id" class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
            <p class="text-xs text-gray-500">{{ q.forum_title }}</p>
            <p class="text-sm text-gray-800 dark:text-gray-200 mt-1">{{ q.question }}</p>
            <p class="text-xs mt-2 text-gray-400">dari {{ q.questioner }} → presenter: {{ q.presenter_name || "—" }} • {{ formatDate(q.created_at) }}</p>
          </div>
        </div>
      </section>

      <!-- Forums overview -->
      <section>
        <h2 class="font-semibold text-green-700 dark:text-green-300 mb-3 flex items-center gap-2">
          <Icon name="mdi:forum-outline" /> Forum Anda
        </h2>
        <div v-if="!data.forums?.length" class="text-gray-500 text-sm">Belum ada forum.</div>
        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <NuxtLink v-for="f in data.forums" :key="f.id" :to="`/teacher/forum/${f.id}`"
            class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 hover:shadow transition">
            <div class="flex items-center justify-between mb-1">
              <p class="font-medium text-gray-800 dark:text-white truncate">{{ f.title }}</p>
              <span class="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase shrink-0"
                :class="statusClass(f.status)">{{ f.status }}</span>
            </div>
            <p class="text-xs text-gray-500">{{ f.type }} • {{ f.questions }} pertanyaan • {{ f.replies }} balasan</p>
          </NuxtLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

definePageMeta({ middleware: "auth", role: "teacher" });

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();
const swal = useSwal();

const data = ref({});
const loading = ref(true);

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/teacher/forum/moderation`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    data.value = res;
  } catch (err) {
    console.error(err);
    toast.add({ title: "Gagal memuat moderasi.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const moderate = async (postId, action) => {
  const labels = { HIDE: "Sembunyikan", DELETE: "Hapus", RESTORE: "Pulihkan" };
  const result = await swal.fire({
    title: `${labels[action]} postingan ini?`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: `Ya, ${labels[action].toLowerCase()}!`,
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/posts/${postId}/moderation/${action}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: `Postingan ${action.toLowerCase()} dengan sukses.`, color: "green" });
    fetchData();
  } catch (err) {
    toast.add({ title: "Gagal memoderasi.", color: "red" });
  }
};

const statusClass = (s) => ({
  ACTIVE: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200",
  CLOSED: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200",
  DRAFT: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  SCHEDULED: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
  ARCHIVED: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
}[s] || "bg-gray-100 text-gray-600");

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
};

fetchData();
</script>