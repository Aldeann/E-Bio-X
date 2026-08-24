<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  block: { type: Object, required: true },
  interactive: { type: Boolean, default: false },
  materialId: { type: [Number, String], default: null },
  sectionId: { type: [Number, String], default: null },
});

const emit = defineEmits(["submitted"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;

const data = computed(() => (props.block && props.block.data) || {});

const externalResults = ref({});
const submitting = ref(null);
const videoEl = ref(null);
const lastVideoReport = ref(0);

const reportVideo = async () => {
  const v = videoEl.value;
  if (!v || !props.materialId) return;
  const now = Date.now();
  if (now - lastVideoReport.value < 15000 && !v.ended) return;
  lastVideoReport.value = now;
  const dur = Math.round(v.duration || 0);
  const pos = Math.round(v.currentTime || 0);
  const watched = Math.round(v.currentTime || 0);
  const completed = !!(v.ended || (v.duration && v.currentTime >= v.duration - 1));
  try {
    await $fetch(`${config.public.backend}/api/materials/${props.materialId}/video-progress`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: {
        section_id: props.sectionId,
        content_id: props.block.id,
        video_duration: dur,
        watched_duration: watched,
        last_position: pos,
        completed,
      },
    });
  } catch (e) {
    // tracking video opsional
  }
};

const signalPdfOpened = async () => {
  if (!props.materialId) return;
  try {
    await $fetch(`${config.public.backend}/api/materials/${props.materialId}/activity`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: { event_type: "pdf_opened", section_id: props.sectionId, content_id: props.block.id },
    });
  } catch (e) {
    // opsional
  }
};

const isYoutube = computed(() => {
  const url = data.value.url || "";
  return /youtube\.com|youtu\.be/.test(url);
});

const youtubeEmbed = computed(() => {
  const url = data.value.url || "";
  const m = url.match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})/);
  return m ? `https://www.youtube.com/embed/${m[1]}` : null;
});

const boxClasses = computed(() => {
  const variant = data.value.variant || "info";
  const map = {
    info: "bg-blue-50 dark:bg-blue-900/30 border-blue-300 text-blue-900 dark:text-blue-100",
    warning:
      "bg-amber-50 dark:bg-amber-900/30 border-amber-300 text-amber-900 dark:text-amber-100",
    success:
      "bg-green-50 dark:bg-green-900/30 border-green-300 text-green-900 dark:text-green-100",
    danger: "bg-red-50 dark:bg-red-900/30 border-red-300 text-red-900 dark:text-red-100",
  };
  return map[variant] || map.info;
});

const boxIcon = computed(() => {
  const variants = {
    info: "material-symbols:info-outline",
    warning: "material-symbols:warning-outline",
    success: "material-symbols:task-alt",
    danger: "material-symbols:error-outline",
  };
  return variants[data.value.variant] || variants.info;
});

const handleSubmit = async (key, selected, questionIndex = null) => {
  if (!props.materialId) return;
  submitting.value = key;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/materials/${props.materialId}/answers`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: {
          section_id: props.sectionId,
          content_id: props.block.id,
          selected_answer: selected,
          ...(questionIndex !== null ? { question_index: questionIndex } : {}),
        },
      }
    );
    externalResults.value[key] = {
      correct: !!res.correct,
      explanation: res.explanation || "",
    };
    emit("submitted", { content_id: props.block.id, ...res });
  } catch (e) {
    const msg = e && e.data && e.data.error ? e.data.error : "Gagal mengirim jawaban.";
    externalResults.value[key] = { correct: false, explanation: msg };
  } finally {
    submitting.value = null;
  }
};
</script>

<template>
  <div class="w-full">
    <!-- Text -->
    <p
      v-if="block.type === 'text'"
      class="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap text-justify"
    >
      {{ data.content }}
    </p>

    <!-- Heading -->
    <component
      :is="'h' + (data.level || 2)"
      v-else-if="block.type === 'heading'"
      class="font-bold text-green-700 dark:text-green-400"
      :class="{ 'text-2xl': (data.level || 2) === 2, 'text-xl': (data.level || 2) >= 3 }"
    >
      {{ data.content }}
    </component>

    <!-- Image -->
    <figure v-else-if="block.type === 'image'" class="text-center space-y-2">
      <img
        v-if="data.url"
        :src="data.url"
        :alt="data.caption || ''"
        class="max-h-96 w-auto max-w-full h-auto mx-auto rounded-xl shadow-md border border-gray-200 dark:border-gray-700"
      />
      <figcaption
        v-if="data.caption"
        class="text-sm text-gray-500 dark:text-gray-400 italic"
      >
        {{ data.caption }}
      </figcaption>
    </figure>

    <!-- Video -->
    <div v-else-if="block.type === 'video'" class="space-y-2">
      <p
        v-if="data.title"
        class="font-semibold text-gray-800 dark:text-gray-100"
      >
        {{ data.title }}
      </p>
      <iframe
        v-if="isYoutube && youtubeEmbed"
        :src="youtubeEmbed"
        class="w-full aspect-video rounded-xl shadow-md border border-gray-200 dark:border-gray-700"
        frameborder="0"
        allowfullscreen
      ></iframe>
      <video
        v-else-if="data.url"
        ref="videoEl"
        :src="data.url"
        controls
        class="w-full rounded-xl shadow-md bg-black"
        @timeupdate="reportVideo"
        @ended="reportVideo"
        @pause="reportVideo"
      ></video>
    </div>

    <!-- PDF -->
    <div v-else-if="block.type === 'pdf'" class="space-y-3">
      <a
        :href="data.url"
        target="_blank"
        @click="signalPdfOpened"
        class="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-semibold"
      >
        <Icon name="mdi:file-pdf-box" class="w-5 h-5" />
        {{ data.title || "Buka Dokumen PDF" }}
      </a>
      <iframe
        v-if="data.url && data.url.includes('.pdf')"
        :src="data.url"
        class="w-full h-96 rounded-xl border border-gray-200 dark:border-gray-700"
      ></iframe>
    </div>

    <!-- Link -->
    <a
      v-else-if="block.type === 'link'"
      :href="data.url"
      target="_blank"
      class="inline-flex items-center gap-2 text-green-600 dark:text-green-400 font-medium hover:underline"
    >
      <Icon name="mdi:link-variant" class="w-5 h-5" />
      {{ data.label || data.url }}
    </a>

    <!-- Info Box -->
    <div
      v-else-if="block.type === 'box'"
      class="rounded-xl border p-4 flex gap-3"
      :class="boxClasses"
    >
      <Icon :name="boxIcon" class="w-6 h-6 shrink-0 mt-0.5" />
      <div class="whitespace-pre-wrap">{{ data.content }}</div>
    </div>

    <!-- Question -->
    <div v-else-if="block.type === 'question'" class="rounded-xl border p-4 border-green-200 dark:border-green-800 bg-white dark:bg-gray-900">
      <p class="font-semibold text-gray-800 dark:text-gray-100 mb-3">
        {{ data.question }}
      </p>
      <MaterialQuestionBlock
        :question="data.question"
        :options="data.options || []"
        :correct-answer="data.correct_answer ?? null"
        :explanation="data.explanation || ''"
        :interactive="interactive"
        :external-result="externalResults['q-' + block.id] || null"
        @submit="(sel) => handleSubmit('q-' + block.id, sel)"
        @answered="(r) => emit('submitted', { content_id: block.id, ...r })"
      />
      <p v-if="submitting === 'q-' + block.id" class="text-xs text-gray-400 mt-2">Menilai jawaban...</p>
    </div>

    <!-- Quiz -->
    <div
      v-else-if="block.type === 'quiz'"
      class="rounded-xl border border-green-200 dark:border-green-800 bg-white dark:bg-gray-900"
    >
      <div class="bg-green-50 dark:bg-green-900/30 rounded-t-xl px-4 py-3 font-bold text-green-700 dark:text-green-300 flex items-center gap-2">
        <Icon name="hugeicons:quiz-04" class="w-5 h-5" />
        {{ data.title || "Latihan Soal" }}
      </div>
      <div class="p-4 space-y-6">
        <div
          v-for="(q, qi) in data.questions || []"
          :key="qi"
          class="space-y-3"
        >
          <p class="font-semibold text-gray-800 dark:text-gray-100">
            {{ qi + 1 }}. {{ q.question }}
          </p>
          <MaterialQuestionBlock
            :question="q.question"
            :options="q.options || []"
            :correct-answer="q.correct_answer ?? null"
            :explanation="q.explanation || ''"
            :interactive="interactive"
            :external-result="externalResults['z-' + block.id + '-' + qi] || null"
            @submit="(sel) => handleSubmit('z-' + block.id + '-' + qi, sel, qi)"
            @answered="(r) => emit('submitted', { content_id: block.id, question_index: qi, ...r })"
          />
          <p
            v-if="submitting === 'z-' + block.id + '-' + qi"
            class="text-xs text-gray-400 mt-2"
          >
            Menilai jawaban...
          </p>
        </div>
      </div>
    </div>
  </div>
</template>