<template>
  <div class="space-y-3">
    <div class="rounded-xl border border-gray-200 dark:border-gray-700 p-4"
      :class="{ 'bg-green-50/60 dark:bg-green-950/20 border-green-200 dark:border-green-800': post.post_type === 'question', 'bg-purple-50/50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800': post.is_best_answer }">
      <!-- header -->
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-2 text-sm min-w-0">
          <UAvatar :alt="post.author_name" size="sm" />
          <div class="min-w-0">
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="font-medium text-green-600 dark:text-green-400">{{ post.author_name }}</span>
              <span v-if="post.author_role === 'teacher'" class="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200 font-semibold uppercase">Guru</span>
              <Icon v-if="post.is_pinned" name="mdi:pin" class="text-red-500 w-4 h-4" title="Disematkan" />
              <span v-if="post.is_best_answer" class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 font-semibold uppercase flex items-center gap-1">
                <Icon name="mdi:star-circle" class="w-3 h-3" /> Best Answer
              </span>
              <span v-if="post.post_type === 'question'" class="text-[10px] px-1.5 py-0.5 rounded-full bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-200 font-semibold uppercase">Pertanyaan</span>
              <span v-if="post.is_deleted" class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200 font-semibold uppercase">Dihapus</span>
            </div>
            <div class="text-xs text-gray-400">
              {{ formatDate(post.created_at) }}
              <span v-if="post.edited" class="text-gray-300 dark:text-gray-600">(diedit)</span>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <button v-if="post.can_best_answer" @click="$emit('best', post)" title="Tandai jawaban terbaik"
            class="p-1.5 rounded-lg hover:bg-amber-100 dark:hover:bg-gray-700" :class="{ 'text-amber-500': post.is_best_answer, 'text-gray-400': !post.is_best_answer }">
            <Icon name="mdi:star-circle" class="w-5 h-5" />
          </button>
          <button v-if="post.can_pin" @click="$emit('pin', post)" title="Semat/lepas semat"
            class="p-1.5 rounded-lg hover:bg-green-100 dark:hover:bg-gray-700" :class="post.is_pinned ? 'text-red-500' : 'text-gray-400'">
            <Icon name="mdi:pin" class="w-4.5 h-4.5 w-[18px] h-[18px]" />
          </button>
          <button v-if="post.can_delete" @click="$emit('delete', post)" title="Hapus"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-gray-700 text-red-400">
            <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- quoted -->
      <div v-if="post.quoted_content" class="mt-2 pl-3 border-l-2 border-green-300 dark:border-green-700 text-xs text-gray-500 dark:text-gray-400 italic">
        {{ post.quoted_content }}
      </div>

      <!-- content -->
      <div v-if="!post.is_deleted" class="mt-2 text-gray-800 dark:text-gray-200 text-sm whitespace-pre-line break-words"
        v-html="renderMarkdown(post.content)"></div>
      <div v-else class="mt-2 text-gray-400 italic text-sm">Postingan telah dihapus.</div>

      <!-- attachments -->
      <div v-if="post.attachments && post.attachments.length" class="mt-2 flex flex-wrap gap-2">
        <a v-for="att in post.attachments" :key="att.id" :href="baseUrl + att.file_url" target="_blank" rel="noopener"
          class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs hover:bg-green-50 dark:hover:bg-gray-700">
          <Icon name="mdi:file-download-outline" class="text-green-600 dark:text-green-400" />
          <span class="max-w-[180px] truncate">{{ att.original_name }}</span>
          <span class="text-gray-400">({{ formatSize(att.file_size) }})</span>
        </a>
      </div>

      <!-- feedback (teacher) -->
      <div v-if="post.feedback" class="mt-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
        <div class="flex items-center gap-1.5 text-xs font-semibold text-amber-700 dark:text-amber-300 mb-1">
          <Icon name="mdi:clipboard-text-outline" /> Feedback Guru
          <span class="text-gray-400 font-normal">oleh {{ post.feedback.teacher_name }}</span>
        </div>
        <p class="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-line">{{ post.feedback.feedback }}</p>
      </div>

      <!-- question answer info -->
      <div v-if="post.question" class="mt-2 text-xs text-gray-500 dark:text-gray-400">
        <span v-if="post.question.status === 'UNANSWERED'" class="text-sky-600 dark:text-sky-400">Menunggu jawaban presenter...</span>
        <span v-else-if="post.question.status === 'ANSWERED'" class="text-green-600 dark:text-green-400">
          Terjawab oleh {{ post.question.answer?.presenter_name }}
        </span>
      </div>

      <!-- actions bar -->
      <div class="mt-3 flex items-center gap-1 flex-wrap">
        <button v-for="rt in reactionTypes" :key="rt.type"
          @click="$emit('react', post, rt.type)"
          class="flex items-center gap-1 px-2 py-1 rounded-lg text-xs border transition"
          :class="post.my_reaction === rt.type
            ? 'bg-green-600 text-white border-green-600'
            : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-300 hover:bg-green-50 dark:hover:bg-gray-800'"
          :title="rt.label">
          <Icon :name="post.my_reaction === rt.type ? rt.filled : rt.outline" class="w-4 h-4" />
          <span>{{ post.reactions?.[rt.type] || 0 }}</span>
        </button>

        <button v-if="forumCanPost" @click="toggleReplyBox" class="flex items-center gap-1 px-2 py-1 rounded-lg text-xs border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-300 hover:bg-green-50 dark:hover:bg-gray-800">
          <Icon name="mdi:reply-outline" class="w-4 h-4" /> Balas
        </button>

        <button v-if="post.can_feedback" @click="$emit('feedback', post)" class="flex items-center gap-1 px-2 py-1 rounded-lg text-xs border border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-gray-800">
          <Icon name="mdi:clipboard-plus-outline" class="w-4 h-4" /> Feedback
        </button>

        <button v-if="post.can_report" @click="$emit('report', post)" class="flex items-center gap-1 px-2 py-1 rounded-lg text-xs border border-red-200 dark:border-red-800 text-red-500 dark:text-red-400 hover:bg-red-50 dark:hover:bg-gray-800">
          <Icon name="mdi:flag-outline" class="w-4 h-4" /> Laporkan
        </button>

        <span v-if="post.children_count > 0 && hasNestedReplies" class="text-xs text-gray-400 ml-auto">
          {{ post.children_count }} balasan
        </span>
      </div>

      <!-- inline reply box -->
      <div v-if="replyOpen && forumCanPost" class="mt-3">
        <textarea v-model="replyText" rows="2" placeholder="Tulis balasan..."
          class="w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 p-2.5 rounded-lg focus:outline-green-500 text-sm"></textarea>
        <div class="flex gap-2 mt-2">
          <button @click="submitReply" :disabled="!replyText.trim()"
            class="bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">Kirim</button>
          <button @click="replyOpen = false" class="px-3 py-1.5 rounded-lg text-sm bg-gray-300 dark:bg-gray-700 hover:bg-gray-400">Batal</button>
        </div>
      </div>
    </div>

    <!-- nested replies -->
    <div v-if="post.replies && post.replies.length" class="ml-5 lg:ml-8 border-l-2 border-gray-100 dark:border-gray-800 pl-3 space-y-3">
      <ForumPostItem
        v-for="child in post.replies"
        :key="child.id"
        :post="child"
        :forum-can-post="forumCanPost"
        @reply="$emit('reply', $event)"
        @react="$emit('react', $event)"
        @delete="$emit('delete', $event)"
        @pin="$emit('pin', $event)"
        @best="$emit('best', $event)"
        @feedback="$emit('feedback', $event)"
        @report="$emit('report', $event)"
      />
    </div>

    <div v-else-if="post.children_count > 0 && !post.replies" class="ml-5 lg:ml-8 pl-3 text-xs text-gray-400">
      {{ post.children_count }} balasan tersimpan (buka halaman untuk melihat semua).
    </div>
  </div>
</template>

<script setup>
import { renderMarkdown } from "~/utils/markdown";

const props = defineProps({
  post: { type: Object, required: true },
  forumCanPost: { type: Boolean, default: false },
});

const emit = defineEmits(["reply", "react", "delete", "pin", "best", "feedback", "report"]);

const baseUrl = useRuntimeConfig().public.backend;
const replyText = ref("");
const replyOpen = ref(false);

const reactionTypes = [
  { type: "like", label: "Suka", outline: "mdi:thumb-up-outline", filled: "mdi:thumb-up" },
  { type: "idea", label: "Ide", outline: "mdi:lightbulb-on-outline", filled: "mdi:lightbulb-on" },
  { type: "love", label: "Love", outline: "mdi:heart-outline", filled: "mdi:heart" },
  { type: "confused", label: "Bingung", outline: "mdi:emoticon-confused-outline", filled: "mdi:emoticon-confused" },
  { type: "insight", label: "Wawasan", outline: "mdi:star-four-points-outline", filled: "mdi:star-four-points" },
  { type: "agree", label: "Setuju", outline: "mdi:check-circle-outline", filled: "mdi:check-circle" },
  { type: "disagree", label: "Menolak", outline: "mdi:close-circle-outline", filled: "mdi:close-circle" },
];

const hasNestedReplies = computed(() => (props.post.replies && props.post.replies.length) || props.post.children_count === 0);

const toggleReplyBox = () => {
  replyOpen.value = !replyOpen.value;
  replyText.value = "";
};

const submitReply = () => {
  emit("reply", { post: props.post, content: replyText.value });
  replyText.value = "";
  replyOpen.value = false;
};

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

const formatSize = (bytes) => {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(1)} ${units[i]}`;
};
</script>