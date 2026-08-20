<template>
  <div class="max-w-4xl mx-auto">
    <button
      v-if="forum"
      @click="goBack"
      class="flex items-center gap-1 text-green-600 dark:text-green-400 hover:underline text-sm mb-4">
      <Icon name="material-symbols:arrow-back-ios-new" class="w-4 h-4" /> Kembali
    </button>

    <div v-if="loading" class="animate-pulse space-y-4">
      <div class="h-8 bg-green-200 dark:bg-gray-700 rounded w-2/3"></div>
      <div class="h-4 bg-green-200 dark:bg-gray-700 rounded w-1/3"></div>
      <div class="h-32 bg-green-200 dark:bg-gray-700 rounded"></div>
    </div>

    <div v-else-if="forum" class="space-y-4">
      <!-- Forum header -->
      <div class="bg-white dark:bg-gray-900 border dark:border-gray-700 rounded-xl p-6 shadow-md dark:shadow-green-200">
        <div class="flex flex-wrap items-center gap-2 mb-2">
          <span v-if="forum.is_pinned"><Icon name="mdi:pin" class="text-red-500" /></span>
          <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold uppercase" :class="typeBadge(forum.type).class">{{ typeBadge(forum.type).label }}</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold uppercase" :class="statusBadge(forum.status).class">{{ statusBadge(forum.status).label }}</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold uppercase bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300">{{ visibilityLabel(forum.visibility) }}</span>
          <h1 class="text-2xl font-bold text-gray-800 dark:text-white">{{ forum.title }}</h1>
        </div>
        <div class="flex items-center gap-3 text-sm text-gray-500 flex-wrap">
          <div class="flex items-center gap-2">
            <UAvatar :alt="forum.author_name" size="sm" />
            <span class="font-medium text-green-600 dark:text-green-400">{{ forum.author_name }}</span>
          </div>
          <span>•</span>
          <span>{{ formatDate(forum.created_at) }}</span>
          <template v-if="forum.course_name"><span>•</span><span>{{ forum.course_name }}</span></template>
        </div>
        <p v-if="forum.description" class="text-gray-700 dark:text-gray-300 whitespace-pre-line mt-3">{{ forum.description }}</p>

        <!-- stats -->
        <div class="flex flex-wrap items-center gap-4 mt-4 text-xs text-gray-500 border-t border-gray-100 dark:border-gray-700 pt-3">
          <span class="flex items-center gap-1"><Icon name="mdi:message-text-outline" class="text-green-500" /> {{ forum.posts_count }} posting</span>
          <span class="flex items-center gap-1"><Icon name="mdi:comment-outline" class="text-green-500" /> {{ forum.replies_count }} balasan</span>
          <span class="flex items-center gap-1"><Icon name="mdi:heart-outline" class="text-green-500" /> {{ forum.reactions_count }} reaksi</span>
          <span v-if="forum.participants_count" class="flex items-center gap-1"><Icon name="mdi:account-group-outline" class="text-green-500" /> {{ forum.participants_count }} peserta</span>
          <span v-if="forum.unanswered_questions_count" class="flex items-center gap-1 text-sky-600 dark:text-sky-400"><Icon name="mdi:comment-question-outline" /> {{ forum.unanswered_questions_count }} pertanyaan belum terjawab</span>
        </div>

        <!-- manage actions -->
        <div v-if="forum.can_manage" class="flex flex-wrap gap-2 mt-4">
          <button @click="toggleLock" class="px-3 py-1.5 rounded-lg text-sm border transition"
            :class="forum.status === 'CLOSED'
              ? 'border-green-600 text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-gray-800'
              : 'border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-gray-800'">
            <Icon :name="forum.status === 'CLOSED' ? 'mdi:lock-open-outline' : 'mdi:lock-outline'" class="w-4 h-4 inline mr-1" />
            {{ forum.status === 'CLOSED' ? 'Buka Forum' : 'Kunci Forum' }}
          </button>
          <button v-if="forum.type === 'PRESENTATION'" @click="uploadPresentationFile" class="px-3 py-1.5 rounded-lg text-sm border border-purple-300 text-purple-600 hover:bg-purple-50 dark:hover:bg-gray-800">
            <Icon name="mdi:upload" class="w-4 h-4 inline mr-1" /> Upload Materi Presentasi
          </button>
        </div>
      </div>

      <!-- Presentation panel -->
      <div v-if="forum.type === 'PRESENTATION'"
        class="bg-white dark:bg-gray-900 border border-purple-200 dark:border-purple-800/50 rounded-xl p-6 shadow-md">
        <h3 class="font-semibold flex items-center gap-2 text-purple-700 dark:text-purple-300 mb-3">
          <Icon name="mdi:microphone-outline" /> Presentasi Kelas
        </h3>

        <div class="grid sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-xs text-gray-400 uppercase">Kelompok</p>
            <p class="font-medium text-gray-800 dark:text-gray-200">{{ forum.presentation_group_name || "—" }}</p>
          </div>
          <div>
            <p class="text-xs text-gray-400 uppercase">Presenter</p>
            <div class="flex flex-wrap gap-1.5 mt-1">
              <span v-for="p in forum.presenters" :key="p.id"
                class="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200 text-xs font-medium">
                {{ p.name }}
              </span>
            </div>
          </div>
          <div v-if="forum.pinned_question" class="sm:col-span-2">
            <p class="text-xs text-gray-400 uppercase">Pertanyaan Inti</p>
            <p class="mt-1 text-gray-700 dark:text-gray-200 whitespace-pre-line bg-purple-50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800 rounded-lg p-3">
              {{ forum.pinned_question }}
            </p>
          </div>
          <div class="sm:col-span-2 flex flex-wrap gap-3">
            <a v-if="forum.presentation_file_url" :href="baseUrl + forum.presentation_file_url" target="_blank" rel="noopener"
              class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-purple-600 text-white text-sm hover:bg-purple-700">
              <Icon name="mdi:file-pdf-box" /> {{ forum.presentation_file_name || "Materi Presentasi" }}
            </a>
            <a v-if="forum.presentation_video_url" :href="baseUrl + forum.presentation_video_url" target="_blank" rel="noopener"
              class="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-200 text-sm hover:bg-purple-200 dark:hover:bg-purple-800">
              <Icon name="mdi:play-box-outline" /> {{ forum.presentation_video_name || "Video Presentasi" }}
            </a>
            <span v-if="!forum.presentation_file_url && !forum.presentation_video_url" class="text-xs text-gray-400 italic">Belum ada materi presentasi.</span>
          </div>
        </div>
      </div>

      <!-- Presenter questions panel -->
      <div v-if="forum.type === 'PRESENTATION' && presenterData"
        class="bg-white dark:bg-gray-900 border border-sky-200 dark:border-sky-800/50 rounded-xl p-6 shadow-md">
        <h3 class="font-semibold flex items-center gap-2 text-sky-700 dark:text-sky-300 mb-3">
          <Icon name="mdi:comment-question-outline" />
          Pertanyaan Presenter
          <span class="text-xs text-gray-400 font-normal">({{ presenterData.answered }} terjawab / {{ presenterData.unanswered }} menunggu)</span>
        </h3>

        <div v-if="!presenterData.questions.length" class="text-sm text-gray-500">Belum ada pertanyaan untuk presenter.</div>
        <div v-else class="space-y-3">
          <div v-for="q in presenterData.questions" :key="q.id" class="rounded-lg border border-gray-200 dark:border-gray-700 p-3">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-line">{{ q.content }}</p>
                <p class="text-xs text-gray-400 mt-1">dari {{ q.questioner }} • {{ formatDate(q.created_at) }}</p>
              </div>
              <span class="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase shrink-0"
                :class="q.status === 'ANSWERED' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200' : 'bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-200'">
                {{ q.status === 'ANSWERED' ? 'Terjawab' : 'Menunggu' }}
              </span>
            </div>
            <p v-if="q.answer" class="text-sm text-gray-700 dark:text-gray-300 mt-2 pl-3 border-l-2 border-sky-300 dark:border-sky-700 whitespace-pre-line">{{ q.answer }}</p>
            <div v-if="q.can_answer && q.status === 'UNANSWERED'" class="mt-2">
              <div class="flex gap-2">
                <input v-model="answerInputs[q.id]" type="text" placeholder="Tulis jawaban..."
                  class="flex-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2 rounded-lg focus:outline-green-500 text-sm" />
                <button @click="answerQuestion(q)"
                  class="bg-sky-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-sky-700 disabled:opacity-50"
                  :disabled="!answerInputs[q.id]?.trim()">Jawab</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- New post box -->
      <div v-if="forum.can_post" class="bg-white dark:bg-gray-900 border dark:border-gray-700 rounded-xl p-6 shadow-md">
        <div class="flex items-center gap-2 mb-3">
          <h3 class="font-semibold text-gray-800 dark:text-white">Mulai Diskusi</h3>
          <div v-if="forum.type === 'PRESENTATION'" class="flex gap-1 text-xs ml-2">
            <button @click="newPostType = 'post'" class="px-2.5 py-1 rounded-full border"
              :class="newPostType === 'post' ? 'bg-green-600 text-white border-green-600' : 'border-gray-200 dark:border-gray-700 text-gray-500'">Diskusi</button>
            <button @click="newPostType = 'question'" class="px-2.5 py-1 rounded-full border"
              :class="newPostType === 'question' ? 'bg-sky-600 text-white border-sky-600' : 'border-gray-200 dark:border-gray-700 text-gray-500'">Pertanyaan Presenter</button>
          </div>
        </div>

        <textarea v-model="newPostContent" rows="3" placeholder="Tulis pemikiranmu di sini... Gunakan @nama untuk mention."
          class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 mb-3"></textarea>

        <!-- mention suggestions -->
        <div v-if="mentionSuggestions.length" class="flex flex-wrap gap-1.5 mb-3">
          <button v-for="u in mentionSuggestions" :key="u.id" @click="insertMention(u)"
            class="px-2 py-1 rounded-full bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 text-xs text-green-700 dark:text-green-300 hover:bg-green-100">
            @{{ u.name }}
          </button>
        </div>

        <!-- attachments -->
        <div class="flex items-center gap-2 mb-3">
          <input ref="fileInput" type="file" class="hidden" @change="uploadAttachment" />
          <button @click="fileInput?.click()" class="px-3 py-1.5 rounded-lg text-xs border border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800">
            <Icon name="mdi:paperclip" class="w-4 h-4 inline mr-1" /> Lampirkan
          </button>
          <span v-if="uploading" class="text-xs text-gray-500">{{ uploadProgress }}%</span>
          <span v-for="att in newAttachments" :key="att.id"
            class="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-800 text-xs text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
            <Icon name="mdi:file-outline" /> {{ att.original_name }}
            <Icon name="material-symbols:close" class="w-3.5 h-3.5 cursor-pointer hover:text-red-500" @click="removeAttachment(att.id)" />
          </span>
        </div>

        <button @click="createPost" :disabled="!newPostContent.trim() || submitting"
          class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50">
          {{ submitting ? "Mengirim..." : "Kirim" }}
        </button>
      </div>

      <div v-else class="bg-white dark:bg-gray-900 border dark:border-gray-700 rounded-xl p-4 text-sm text-gray-500">
        {{ forum.status === 'DRAFT' ? 'Forum ini masih draft.' : forum.status === 'CLOSED' ? 'Forum ini telah ditutup. Anda tidak dapat menambah diskusi baru.' : 'Anda tidak dapat berpartisipasi di forum ini.' }}
      </div>

      <!-- Posts -->
      <div>
        <h3 class="font-semibold text-gray-800 dark:text-white mb-3">{{ forum.posts.length }} Diskusi</h3>
        <div v-if="forum.posts.length === 0" class="text-gray-500">Belum ada postingan. Jadilah yang pertama berdiskusi!</div>
        <div v-else class="space-y-4">
          <ForumPostItem
            v-for="post in forum.posts"
            :key="post.id"
            :post="post"
            :forum-can-post="forum.can_post"
            @reply="handleReply"
            @react="handleReact"
            @delete="handleDelete"
            @pin="handlePin"
            @best="handleBest"
            @feedback="handleFeedback"
            @report="handleReport"
          />
        </div>
      </div>
    </div>

    <div v-else class="text-red-500">Forum tidak ditemukan.</div>

    <!-- Feedback modal -->
    <div v-if="feedbackTarget" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="feedbackTarget = null"></div>
      <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md p-6">
        <h3 class="font-semibold mb-3 text-gray-800 dark:text-white">Feedback Guru</h3>
        <textarea v-model="feedbackText" rows="3" placeholder="Tulis feedback konstruktif untuk siswa..." class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 mb-3"></textarea>
        <div class="flex gap-2 justify-end">
          <button @click="feedbackTarget = null" class="px-4 py-2 rounded-lg bg-gray-300 dark:bg-gray-700">Batal</button>
          <button @click="submitFeedback" :disabled="!feedbackText.trim()" class="bg-green-600 text-white px-4 py-2 rounded-lg disabled:opacity-50">Kirim</button>
        </div>
      </div>
    </div>

    <!-- Report modal -->
    <div v-if="reportTarget" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/50" @click="reportTarget = null"></div>
      <div class="relative bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-md p-6">
        <h3 class="font-semibold mb-3 text-gray-800 dark:text-white">Laporkan Postingan</h3>
        <label class="block text-sm font-medium mb-1 text-gray-600 dark:text-gray-300">Alasan</label>
        <select v-model="reportReason" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 mb-3">
          <option value="SPAM">Spam</option>
          <option value="INAPPROPRIATE">Konten tidak pantas</option>
          <option value="OFF_TOPIC">Di luar topik</option>
          <option value="MISINFORMATION">Informasi keliru</option>
          <option value="OTHER">Lainnya</option>
        </select>
        <textarea v-model="reportDesc" rows="2" placeholder="Keterangan tambahan (opsional)" class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 mb-3"></textarea>
        <div class="flex gap-2 justify-end">
          <button @click="reportTarget = null" class="px-4 py-2 rounded-lg bg-gray-300 dark:bg-gray-700">Batal</button>
          <button @click="submitReport" class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">Laporkan</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";
import { uploadFile } from "~/utils/upload";

const props = defineProps({
  forumId: {
    type: [String, Number],
    required: true,
  },
});

const config = useRuntimeConfig();
const baseUrl = config.public.backend;
const token = useCookie("access_token").value;
const role = useCookie("role").value;
const swal = useSwal();
const toast = useToast();
const router = useRouter();

const forum = ref(null);
const loading = ref(true);
const presenterData = ref(null);

const newPostContent = ref("");
const newPostType = ref("post");
const submitting = ref(false);
const newAttachments = ref([]);
const fileInput = ref(null);
const uploading = ref(false);
const uploadProgress = ref(0);
const mentionSuggestions = ref([]);

const feedbackTarget = ref(null);
const feedbackText = ref("");
const reportTarget = ref(null);
const reportReason = ref("SPAM");
const reportDesc = ref("");
const answerInputs = reactive({});

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

const visibilityLabel = (v) => {
  const map = { PRIVATE: "Pribadi", CLASS: "Kelas", COURSE: "Kursus" };
  return map[v] || v;
};

const fetchForum = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${baseUrl}/api/forums/${props.forumId}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    forum.value = res;
    if (forum.value.type === "PRESENTATION") {
      fetchPresenterData();
    }
    if (forum.value.can_post) {
      fetchMentions();
    }
  } catch (err) {
    console.error(err);
    toast.add({ title: "Gagal memuat forum.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const fetchPresenterData = async () => {
  try {
    const res = await $fetch(`${baseUrl}/api/forums/${props.forumId}/presenter-dashboard`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    presenterData.value = res;
  } catch (err) {
    console.error(err);
  }
};

const fetchMentions = async (q = "") => {
  try {
    const res = await $fetch(`${baseUrl}/api/forum/mentions/suggest?forum_id=${props.forumId}&q=${encodeURIComponent(q)}`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    mentionSuggestions.value = res.users || [];
  } catch (err) {
    console.error(err);
  }
};

const insertMention = (u) => {
  newPostContent.value += `@${u.name} `;
};

const uploadAttachment = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  uploading.value = true;
  uploadProgress.value = 0;
  try {
    const res = await uploadFile({
      url: `${baseUrl}/api/forums/${props.forumId}/attachments`,
      token,
      file,
      onProgress: (p) => (uploadProgress.value = p),
    });
    if (res.attachment) {
      newAttachments.value.push(res.attachment);
      toast.add({ title: "Lampiran terunggah.", color: "green" });
    } else {
      toast.add({ title: res.error || "Gagal mengunggah.", color: "red" });
    }
  } catch (err) {
    toast.add({ title: err?.error || "Gagal mengunggah.", color: "red" });
  } finally {
    uploading.value = false;
    if (fileInput.value) fileInput.value.value = "";
  }
};

const removeAttachment = (id) => {
  newAttachments.value = newAttachments.value.filter((a) => a.id !== id);
};

const createPost = async () => {
  submitting.value = true;
  try {
    await $fetch(`${baseUrl}/api/forums/${props.forumId}/posts`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content: newPostContent.value,
        post_type: newPostType.value,
        attachment_ids: newAttachments.value.map((a) => a.id),
        request_id: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      }),
    });
    toast.add({ title: "Postingan terkirim.", color: "green" });
    newPostContent.value = "";
    newAttachments.value = [];
    fetchForum();
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal mengirim postingan.", color: "red" });
  } finally {
    submitting.value = false;
  }
};

const handleReply = async ({ post, content }) => {
  try {
    await $fetch(`${baseUrl}/api/posts/${post.id}/replies`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content,
        request_id: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
      }),
    });
    toast.add({ title: "Balasan terkirim.", color: "green" });
    fetchForum();
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal mengirim balasan.", color: "red" });
  }
};

const handleReact = async (post, type) => {
  try {
    await $fetch(`${baseUrl}/api/posts/${post.id}/reactions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reaction_type: type }),
    });
    fetchForum();
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal mengubah reaksi.", color: "red" });
  }
};

const handleDelete = async (post) => {
  const result = await swal.fire({
    title: "Hapus postingan ini?",
    text: "Postingan ini akan dihapus beserta isinya.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Ya, hapus!",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${baseUrl}/api/posts/${post.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Postingan dihapus.", color: "green" });
    fetchForum();
  } catch (err) {
    toast.add({ title: "Gagal menghapus postingan.", color: "red" });
  }
};

const handlePin = async (post) => {
  try {
    await $fetch(`${baseUrl}/api/posts/${post.id}`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ is_pinned: !post.is_pinned }),
    });
    toast.add({ title: post.is_pinned ? "Semat dilepas." : "Postingan disematkan.", color: "green" });
    fetchForum();
  } catch (err) {
    toast.add({ title: "Gagal mengubah semat.", color: "red" });
  }
};

const handleBest = async (post) => {
  try {
    await $fetch(`${baseUrl}/api/posts/${post.id}/best-answer`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Jawaban terbaik ditandai.", color: "green" });
    fetchForum();
  } catch (err) {
    toast.add({ title: "Gagal menandai jawaban terbaik.", color: "red" });
  }
};

const handleFeedback = (post) => {
  feedbackTarget.value = post;
  feedbackText.value = "";
};

const submitFeedback = async () => {
  try {
    await $fetch(`${baseUrl}/api/posts/${feedbackTarget.value.id}/feedback`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ feedback: feedbackText.value }),
    });
    toast.add({ title: "Feedback disimpan.", color: "green" });
    feedbackTarget.value = null;
    fetchForum();
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal menyimpan feedback.", color: "red" });
  }
};

const handleReport = (post) => {
  reportTarget.value = post;
  reportReason.value = "SPAM";
  reportDesc.value = "";
};

const submitReport = async () => {
  try {
    await $fetch(`${baseUrl}/api/posts/${reportTarget.value.id}/report`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ reason: reportReason.value, description: reportDesc.value }),
    });
    toast.add({ title: "Laporan terkirim.", color: "green" });
    reportTarget.value = null;
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal mengirim laporan.", color: "red" });
  }
};

const answerQuestion = async (q) => {
  try {
    await $fetch(`${baseUrl}/api/questions/${q.id}/answer`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content: answerInputs[q.id], request_id: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}` }),
    });
    toast.add({ title: "Jawaban terkirim.", color: "green" });
    answerInputs[q.id] = "";
    fetchPresenterData();
    fetchForum();
  } catch (err) {
    toast.add({ title: err?.data?.error || "Gagal mengirim jawaban.", color: "red" });
  }
};

const toggleLock = async () => {
  const isClosed = forum.value.status === "CLOSED";
  const result = await swal.fire({
    title: isClosed ? "Buka kembali forum ini?" : "Kunci forum ini?",
    text: isClosed ? "Kelas dapat kembali berdiskusi." : "Diskusi baru akan dihentikan namun tetap bisa dibaca.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: isClosed ? "Ya, buka!" : "Ya, kunci!",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${baseUrl}/api/forums/${props.forumId}/${isClosed ? "unlock" : "lock"}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: isClosed ? "Forum dibuka kembali." : "Forum dikunci.", color: "green" });
    fetchForum();
  } catch (err) {
    toast.add({ title: "Gagal mengubah status forum.", color: "red" });
  }
};

const uploadPresentationFile = () => {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".pdf,.pptx,.mp4,image/*";
  input.onchange = async () => {
    const file = input.files?.[0];
    if (!file) return;
    uploading.value = true;
    uploadProgress.value = 0;
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("purpose", "presentation");
      await $fetch(`${baseUrl}/api/forums/${props.forumId}/attachments`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      toast.add({ title: "Materi presentasi diunggah.", color: "green" });
      fetchForum();
    } catch (err) {
      toast.add({ title: err?.data?.error || "Gagal mengunggah.", color: "red" });
    } finally {
      uploading.value = false;
    }
  };
  input.click();
};

const goBack = () => {
  const courseId = forum.value?.course_id;
  if (courseId) {
    router.push(`/${role}/course/${courseId}`);
  } else {
    router.push(`/${role}/forum`);
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString("id-ID", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

fetchForum();
</script>