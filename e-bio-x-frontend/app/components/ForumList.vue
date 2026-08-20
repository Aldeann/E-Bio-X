<template>
  <div class="p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <div class="flex items-center justify-between mb-4 gap-3 flex-wrap">
      <h2 class="text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
        <Icon name="mdi:forum-outline" class="text-green-500" /> Forum Diskusi Interaktif
      </h2>
      <button
        v-if="canCreate"
        @click="openCreate"
        class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center gap-1 text-sm">
        <Icon name="mdi:message-plus" /> Forum Baru
      </button>
    </div>

    <div class="flex flex-wrap items-center gap-2 mb-4 text-xs">
      <button
        v-for="t in forumTypes"
        :key="t.value"
        @click="setType(t.value)"
        class="px-3 py-1 rounded-full border font-medium transition"
        :class="selectedType === t.value
          ? 'bg-green-600 text-white border-green-600'
          : 'bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-green-200 dark:border-green-800 hover:bg-green-50 dark:hover:bg-gray-700'">
        {{ t.label }}
      </button>
    </div>

    <!-- Create Forum Modal -->
    <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="showCreate = false"></div>
      <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-green-700 dark:text-green-400 flex items-center gap-2">
            <Icon name="mdi:forum-plus-outline" /> Buat Forum Baru
          </h3>
          <Icon name="material-symbols:close" class="cursor-pointer text-gray-400 hover:text-gray-600" @click="showCreate = false" />
        </div>

        <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Judul *</label>
        <input v-model="form.title" type="text" placeholder="Judul forum..."
          class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 mb-3" />

        <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Deskripsi</label>
        <textarea v-model="form.description" rows="3" placeholder="Tujuan dan aturan forum..."
          class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 mb-3"></textarea>

        <div class="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Tipe</label>
            <select v-model="form.type" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500">
              <option v-for="t in forumTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Visibilitas</label>
            <select v-model="form.visibility" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500">
              <option value="COURSE">Kelas (semua anggota)</option>
              <option value="CLASS">Kelas</option>
              <option value="PRIVATE">Pribadi</option>
            </select>
          </div>
        </div>

        <div v-if="role === 'teacher'" class="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Status</label>
            <select v-model="form.status" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500">
              <option value="ACTIVE">Aktif</option>
              <option value="DRAFT">Draft</option>
              <option value="SCHEDULED">Terjadwal</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Topik</label>
            <input v-model="form.topic" type="text" placeholder="cth: Sel, Genetika..."
              class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500" />
          </div>
        </div>

        <div v-if="form.type === 'PRESENTATION'" class="mb-3 p-3 bg-green-50 dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-800">
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Nama Kelompok Presentasi</label>
          <input v-model="form.presentation_group_name" type="text" placeholder="cth: Kelompok 1"
            class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 mb-2" />
          <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Pertanyaan Inti (pinned question)</label>
          <textarea v-model="form.pinned_question" rows="2" placeholder="Pertanyaan inti presentasi..."
            class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500"></textarea>
        </div>

        <div class="flex gap-2 justify-end">
          <button class="px-4 py-2 rounded-lg bg-gray-300 dark:bg-gray-700 hover:bg-gray-400" @click="showCreate = false">Batal</button>
          <button
            @click="createForum"
            :disabled="!form.title.trim() || saving"
            class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50">
            {{ saving ? "Menyimpan..." : "Buat Forum" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="border rounded-xl p-4 animate-pulse">
        <div class="h-5 bg-green-200 dark:bg-gray-700 rounded w-2/3 mb-2"></div>
        <div class="h-3 bg-green-200 dark:bg-gray-700 rounded w-1/2"></div>
      </div>
    </div>

    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <div v-else>
      <div v-if="filtered.length === 0" class="text-gray-500 text-center py-8">
        <Icon name="mdi:forum-outline" class="text-4xl mx-auto mb-2 text-gray-300 dark:text-gray-600" />
        Belum ada forum. Mulai diskusi interaktif pertamamu!
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="forum in filtered"
          :key="forum.id"
          class="rounded-xl p-4 shadow-md dark:shadow-green-200 bg-white dark:bg-gray-900 border dark:border-gray-700 hover:shadow-lg transition cursor-pointer"
          @click="openForum(forum)">
          <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1 flex-wrap">
                <Icon v-if="forum.is_pinned" name="mdi:pin" class="text-red-500 shrink-0" title="Disematkan" />
                <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wide"
                  :class="typeBadge(forum.type).class">{{ typeBadge(forum.type).label }}</span>
                <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wide"
                  :class="statusBadge(forum.status).class">{{ statusBadge(forum.status).label }}</span>
                <h3 class="font-semibold text-gray-800 dark:text-white truncate">{{ forum.title }}</h3>
              </div>
              <div class="flex items-center gap-1 text-xs text-gray-500 flex-wrap">
                <span class="font-medium text-green-600 dark:text-green-400">{{ forum.author_name }}</span>
                <span>•</span>
                <span>{{ formatDate(forum.created_at) }}</span>
                <template v-if="forum.course_name"><span>•</span><span>{{ forum.course_name }}</span></template>
              </div>
              <span v-if="forum.presentation_group_name" class="inline-flex items-center gap-1 mt-1 text-xs text-purple-600 dark:text-purple-400">
                <Icon name="mdi:microphone-outline" class="w-3.5 h-3.5" /> {{ forum.presentation_group_name }}
              </span>
              <p v-if="forum.description" class="text-sm text-gray-600 dark:text-gray-300 mt-1 line-clamp-2">{{ forum.description }}</p>
            </div>

            <div class="flex items-center gap-3 shrink-0">
              <div class="flex items-center gap-3 text-xs text-gray-500">
                <span class="flex items-center gap-1" title="Postingan">
                  <Icon name="mdi:message-text-outline" class="text-green-500" /> {{ forum.posts_count }}
                </span>
                <span class="flex items-center gap-1" title="Balasan">
                  <Icon name="mdi:comment-outline" class="text-green-500" /> {{ forum.replies_count }}
                </span>
                <span class="flex items-center gap-1" title="Reaksi">
                  <Icon name="mdi:heart-outline" class="text-green-500" /> {{ forum.reactions_count }}
                </span>
                <span class="flex items-center gap-1" title="Peserta" v-if="forum.participants_count">
                  <Icon name="mdi:account-group-outline" class="text-green-500" /> {{ forum.participants_count }}
                </span>
              </div>
              <button
                v-if="forum.can_manage"
                @click.stop="deleteForum(forum)"
                class="p-1 rounded hover:bg-red-100 dark:hover:bg-gray-700"
                title="Hapus forum">
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

const forumTypes = [
  { value: "ALL", label: "Semua" },
  { value: "GENERAL_DISCUSSION", label: "Diskusi" },
  { value: "PRESENTATION", label: "Presentasi" },
  { value: "QUESTION_ANSWER", label: "Tanya Jawab" },
  { value: "CASE_STUDY", label: "Studi Kasus" },
];

const forums = ref([]);
const loading = ref(true);
const error = ref(null);
const selectedType = ref("ALL");
const showCreate = ref(false);
const saving = ref(false);
const form = ref({
  title: "",
  description: "",
  type: "GENERAL_DISCUSSION",
  visibility: "COURSE",
  status: "ACTIVE",
  topic: "",
  pinned_question: "",
  presentation_group_name: "",
});

const canCreate = computed(() =>
  role === "teacher" || role === "admin" || (role === "student" && settings.allowStudentCreation)
);
const settings = reactive({ allowStudentCreation: true });

const filtered = computed(() =>
  selectedType.value === "ALL" ? forums.value : forums.value.filter((f) => f.type === selectedType.value)
);

const typeBadge = (t) => {
  const map = {
    GENERAL_DISCUSSION: { label: "Diskusi", class: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200" },
    PRESENTATION: { label: "Presentasi", class: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200" },
    QUESTION_ANSWER: { label: "Tanya Jawab", class: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200" },
    CASE_STUDY: { label: "Studi Kasus", class: "bg-teal-100 text-teal-700 dark:bg-teal-900 dark:text-teal-200" },
  };
  return map[t] || { label: t, class: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200" };
};

const statusBadge = (s) => {
  const map = {
    ACTIVE: { label: "Aktif", class: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200" },
    DRAFT: { label: "Draft", class: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300" },
    SCHEDULED: { label: "Jadwal", class: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200" },
    CLOSED: { label: "Tutup", class: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200" },
    ARCHIVED: { label: "Arsip", class: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300" },
  };
  return map[s] || { label: s, class: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200" };
};

const fetchForumSettings = async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/forum/settings`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    settings.allowStudentCreation = res.allow_student_forum_creation;
  } catch (err) {
    console.error(err);
  }
};

const fetchForums = async () => {
  loading.value = true;
  error.value = null;
  try {
    const res = await $fetch(`${config.public.backend}/api/forums?course_id=${props.courseId}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    forums.value = res.forums || [];
  } catch (err) {
    console.error(err);
    error.value = "Gagal memuat forum.";
  } finally {
    loading.value = false;
  }
};

const setType = (t) => {
  selectedType.value = t;
};

const openCreate = () => {
  form.value = {
    title: "",
    description: "",
    type: "GENERAL_DISCUSSION",
    visibility: role === "student" ? "CLASS" : "COURSE",
    status: "ACTIVE",
    topic: "",
    pinned_question: "",
    presentation_group_name: "",
  };
  showCreate.value = true;
};

const createForum = async () => {
  saving.value = true;
  try {
    await $fetch(`${config.public.backend}/api/forums`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ...form.value, course_id: Number(props.courseId) }),
    });
    toast.add({ title: "Forum berhasil dibuat.", color: "green" });
    showCreate.value = false;
    fetchForums();
  } catch (err) {
    const msg = err?.data?.error || "Gagal membuat forum.";
    toast.add({ title: msg, color: "red" });
  } finally {
    saving.value = false;
  }
};

const openForum = (forum) => {
  router.push(`/${role}/forum/${forum.id}`);
};

const deleteForum = async (forum) => {
  const result = await swal.fire({
    title: "Hapus forum ini?",
    text: `"${forum.title}" beserta seluruh postingannya akan dihapus.`,
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
  return new Date(dateStr).toLocaleString("id-ID");
};

fetchForumSettings();
fetchForums();
</script>