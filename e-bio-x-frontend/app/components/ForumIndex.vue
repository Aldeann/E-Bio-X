<template>
  <div class="container mx-auto px-3 sm:px-4 py-4 sm:py-6">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 flex-wrap gap-2 sm:gap-3">
      <h1 class="text-xl sm:text-3xl font-bold text-green-500">Forum Diskusi</h1>
      <div class="flex gap-1.5 sm:gap-2 flex-wrap">
        <template v-if="role === 'teacher' || role === 'admin'">
          <NuxtLink to="/teacher/forum/moderation" class="px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg border border-amber-300 text-amber-600 hover:bg-amber-50 dark:hover:bg-gray-800 text-xs sm:text-sm flex items-center gap-1">
            <Icon name="mdi:shield-alert-outline" /> Moderasi
          </NuxtLink>
          <NuxtLink to="/teacher/forum/analytics" class="px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg border border-blue-300 text-blue-600 hover:bg-blue-50 dark:hover:bg-gray-800 text-xs sm:text-sm flex items-center gap-1">
            <Icon name="mdi:chart-box-outline" /> Analitik
          </NuxtLink>
        </template>
        <NuxtLink v-if="canCreate" :to="`/${role}/forum/new`" class="px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 text-xs sm:text-sm flex items-center gap-1">
          <Icon name="mdi:message-plus" /> Forum Baru
        </NuxtLink>
      </div>
    </div>

    <div class="space-y-3 sm:space-y-4">
      <!-- filters -->
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 p-3 sm:p-4 bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 shadow-sm">
        <input v-model="query" type="text" placeholder="Cari forum..." class="flex-1 min-w-0 sm:min-w-[180px] bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 px-3 py-2 rounded-lg focus:outline-green-500 text-sm" />
        <div class="flex gap-2">
          <select v-model="typeFilter" class="flex-1 sm:flex-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 px-3 py-2 rounded-lg focus:outline-green-500 text-sm">
            <option value="">Semua tipe</option>
            <option value="GENERAL_DISCUSSION">Diskusi</option>
            <option value="PRESENTATION">Presentasi</option>
            <option value="QUESTION_ANSWER">Tanya Jawab</option>
            <option value="CASE_STUDY">Studi Kasus</option>
          </select>
          <select v-model="sortBy" class="flex-1 sm:flex-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 px-3 py-2 rounded-lg focus:outline-green-500 text-sm">
            <option value="latest">Terbaru</option>
            <option value="replies">Terbanyak balasan</option>
            <option value="reactions">Terbanyak reaksi</option>
            <option value="unanswered">Belum terjawab</option>
          </select>
          <button @click="fetchForums" class="px-3 sm:px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 text-sm hover:bg-green-50 dark:hover:bg-gray-700 shrink-0">
            <Icon name="mdi:magnify" class="w-4 h-4 inline" /> Cari
          </button>
        </div>
      </div>

      <!-- my forums quick toggle -->
      <div class="flex items-center gap-2 text-xs sm:text-sm">
        <label class="flex items-center gap-2 text-gray-600 dark:text-gray-300 cursor-pointer">
          <input v-model="myOnly" type="checkbox" class="accent-green-600" /> Hanya forum saya
        </label>
      </div>

      <!-- loading -->
      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
        <div v-for="i in 4" :key="i" class="border rounded-xl p-2.5 sm:p-4 animate-pulse">
          <div class="h-3.5 sm:h-4 bg-green-200 dark:bg-gray-700 rounded w-2/3 mb-1.5 sm:mb-2"></div>
          <div class="h-2.5 sm:h-3 bg-green-200 dark:bg-gray-700 rounded w-1/2 mb-1.5 sm:mb-2"></div>
          <div class="h-2.5 sm:h-3 bg-green-200 dark:bg-gray-700 rounded w-1/3"></div>
        </div>
      </div>

      <div v-else-if="error" class="text-red-500 text-xs sm:text-sm">{{ error }}</div>

      <!-- recommended -->
      <div v-if="role === 'student' && recommended.length" class="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-xl p-2.5 sm:p-4">
        <h3 class="font-semibold text-green-700 dark:text-green-400 flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-3 text-xs sm:text-base">
          <Icon name="mdi:star-outline" /> Direkomendasikan Untukmu
        </h3>
        <div class="space-y-1.5 sm:space-y-2">
          <button v-for="f in recommended" :key="f.id" @click="openForum(f)"
            class="w-full flex items-center justify-between gap-2 sm:gap-3 p-2 sm:p-3 rounded-lg bg-white dark:bg-gray-900 border border-green-200 dark:border-green-800 hover:shadow transition text-left">
            <div class="min-w-0">
              <p class="font-medium text-gray-800 dark:text-white truncate text-xs sm:text-sm">{{ f.title }}</p>
              <p class="text-[9px] sm:text-xs text-gray-500">{{ f.author_name }} · {{ f.replies_count }} balasan</p>
            </div>
            <span class="text-green-600 shrink-0"><Icon name="mdi:arrow-right" class="w-4 h-4 sm:w-5 sm:h-5" /></span>
          </button>
        </div>
      </div>

      <!-- list -->
      <div v-else-if="forums.length === 0" class="text-center py-6 sm:py-10">
        <Icon name="mdi:forum-outline" class="text-3xl sm:text-5xl mx-auto mb-1.5 sm:mb-3 text-gray-300 dark:text-gray-600" />
        <p class="text-xs sm:text-sm text-gray-500">Tidak ada forum ditemukan.</p>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
        <button v-for="f in forums" :key="f.id" @click="openForum(f)"
          class="w-full text-left rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md hover:border-green-400 transition group">
          <!-- Header stripe -->
          <div class="h-1 sm:h-1.5" :class="statusColor(f.status)" />

          <!-- Body -->
          <div class="p-2 sm:p-4 flex flex-col flex-1 relative">
            <!-- Delete button (teacher only) -->
            <button
              v-if="role === 'teacher'"
              @click.stop="deleteForum($event, f)"
              class="absolute top-1.5 right-1.5 sm:top-2 sm:right-2 w-5 h-5 sm:w-6 sm:h-6 flex items-center justify-center rounded-full text-red-500 hover:bg-red-100 dark:hover:bg-gray-700 transition sm:opacity-0 sm:group-hover:opacity-100"
              title="Hapus forum">
              <Icon name="material-symbols:delete-rounded" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
            </button>

            <!-- Badges -->
            <div class="flex items-center gap-1 sm:gap-1.5 flex-wrap">
              <Icon v-if="f.is_pinned" name="mdi:pin" class="text-red-500 shrink-0 w-2.5 h-2.5 sm:w-3.5 sm:h-3.5" />
              <span class="text-[8px] sm:text-[11px] px-1 sm:px-2 py-px sm:py-0.5 rounded-full font-semibold uppercase shrink-0" :class="typeBadge(f.type).class">{{ typeBadge(f.type).label }}</span>
              <span class="text-[8px] sm:text-[11px] px-1 sm:px-2 py-px sm:py-0.5 rounded-full font-semibold uppercase shrink-0" :class="statusBadge(f.status).class">{{ statusBadge(f.status).label }}</span>
            </div>

            <h3 class="mt-1 sm:mt-2 font-semibold text-[11px] sm:text-base text-gray-800 dark:text-white group-hover:text-green-600 line-clamp-2 leading-snug">
              {{ f.title }}
            </h3>

            <!-- Author + date -->
            <div class="mt-0.5 sm:mt-1 flex items-center gap-0.5 sm:gap-1 text-[9px] sm:text-xs text-gray-500 flex-wrap">
              <span class="font-medium text-green-600 dark:text-green-400">{{ f.author_name }}</span>
              <span>·</span>
              <span>{{ formatDate(f.created_at) }}</span>
              <template v-if="f.course_name"><span>·</span><span class="truncate max-w-[70px] sm:max-w-[80px]">{{ f.course_name }}</span></template>
            </div>

            <!-- Description -->
            <p v-if="f.description" class="text-[10px] sm:text-sm text-gray-600 dark:text-gray-300 mt-0.5 sm:mt-1.5 line-clamp-2 leading-relaxed">{{ f.description }}</p>

            <!-- Spacer -->
            <div class="flex-1" />

            <!-- Stats -->
            <div class="mt-1.5 sm:mt-3 pt-1.5 sm:pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center gap-1.5 sm:gap-3 text-[9px] sm:text-xs text-gray-500">
              <span class="flex items-center gap-0.5 sm:gap-1"><Icon name="mdi:message-text-outline" class="w-2.5 h-2.5 sm:w-3.5 sm:h-3.5 text-green-500" /> {{ f.posts_count }}</span>
              <span class="flex items-center gap-0.5 sm:gap-1"><Icon name="mdi:comment-outline" class="w-2.5 h-2.5 sm:w-3.5 sm:h-3.5 text-green-500" /> {{ f.replies_count }}</span>
              <span class="flex items-center gap-0.5 sm:gap-1"><Icon name="mdi:heart-outline" class="w-2.5 h-2.5 sm:w-3.5 sm:h-3.5 text-green-500" /> {{ f.reactions_count }}</span>
            </div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const props = defineProps({
  role: { type: String, required: true },
});

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const router = useRouter();
const swal = useSwal();
const toast = useToast();

const forums = ref([]);
const recommended = ref([]);
const loading = ref(true);
const error = ref(null);
const query = ref("");
const typeFilter = ref("");
const sortBy = ref("latest");
const myOnly = ref(false);
const tab = ref("all");

const canCreate = computed(() => props.role === "teacher" || (props.role === "student" && studentCanCreate.value));
const studentCanCreate = ref(false);

const typeBadge = (t) => ({
  GENERAL_DISCUSSION: { label: "Diskusi", class: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200" },
  PRESENTATION: { label: "Presentasi", class: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200" },
  QUESTION_ANSWER: { label: "Tanya Jawab", class: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200" },
  CASE_STUDY: { label: "Studi Kasus", class: "bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-200" },
}[t] || { label: t, class: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200" });

const statusBadge = (s) => ({
  ACTIVE: { label: "Aktif", class: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200" },
  DRAFT: { label: "Draft", class: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300" },
  SCHEDULED: { label: "Jadwal", class: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200" },
  CLOSED: { label: "Tutup", class: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200" },
  ARCHIVED: { label: "Arsip", class: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300" },
}[s] || { label: s, class: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200" });

const statusColor = (s) => ({
  ACTIVE: 'bg-green-500',
  DRAFT: 'bg-gray-400',
  SCHEDULED: 'bg-blue-500',
  CLOSED: 'bg-red-400',
  ARCHIVED: 'bg-gray-300',
}[s] || 'bg-gray-300');

const buildQuery = () => {
  const params = new URLSearchParams();
  if (query.value) params.set("q", query.value);
  if (typeFilter.value) params.set("type", typeFilter.value);
  params.set("sort", sortBy.value);
  if (myOnly.value) params.set("scope", "my");
  const qs = params.toString();
  return qs ? `?${qs}` : "";
};

const fetchForums = async () => {
  loading.value = true;
  error.value = null;
  try {
    const res = await $fetch(`${config.public.backend}/api/forums${buildQuery()}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    forums.value = res.forums || [];
    recommended.value = res.recommended || [];
  } catch (err) {
    console.error(err);
    error.value = "Gagal memuat forum.";
  } finally {
    loading.value = false;
  }
};

const fetchSettings = async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/forum/settings`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    studentCanCreate.value = res.allow_student_forum_creation;
  } catch (err) {
    console.error(err);
  }
};

const openForum = (f) => {
  router.push(`/${props.role}/forum/${f.id}`);
};

const deleteForum = async (e, forum) => {
  e.stopPropagation();
  const result = await swal.fire({
    title: "Hapus forum ini?",
    text: `"${forum.title}" beserta seluruh postingannya akan dihapus permanen.`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Ya, hapus!",
    cancelButtonText: "Batal",
  });

  if (!result.isConfirmed) return;

  try {
    await $fetch(`${config.public.backend}/api/forums/${forum.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Forum dihapus.", color: "green" });
    fetchForums();
  } catch (err) {
    toast.add({ title: "Gagal menghapus forum.", color: "red" });
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
};

fetchSettings();
fetchForums();
</script>