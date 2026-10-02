<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 bg-black/50 flex items-start sm:items-center justify-center p-3 sm:p-6 overflow-y-auto"
      @click.self="close"
    >
      <div class="bg-white dark:bg-gray-900 rounded-xl shadow-xl w-full max-w-2xl my-4">
        <!-- header -->
        <div class="flex items-start justify-between gap-3 px-5 py-4 border-b border-gray-200 dark:border-gray-700">
          <div class="min-w-0">
            <h3 class="font-semibold text-gray-800 dark:text-gray-100">Latihan: {{ sectionTitle }}</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              Soal latihan disetujui guru. Jawabanmu ikut dihitung pada peta pemahaman bagian ini.
            </p>
          </div>
          <button class="text-gray-400 hover:text-gray-600 shrink-0" @click="close" aria-label="Tutup">
            <Icon name="material-symbols:close" class="w-5 h-5" />
          </button>
        </div>

        <div class="px-5 py-4">
          <div v-if="loading" class="text-center py-10 text-gray-500">
            <Icon name="mdi:loading" class="w-8 h-8 animate-spin mx-auto" />
          </div>

          <div v-else-if="loadError" class="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4">
            <p class="text-sm text-red-700 dark:text-red-300">{{ loadError }}</p>
          </div>

          <div v-else-if="!questions.length" class="text-center py-10">
            <Icon name="material-symbols:inbox" class="w-10 h-10 text-gray-300 mx-auto mb-2" />
            <p class="text-sm text-gray-600 dark:text-gray-300">{{ emptyMessage }}</p>
          </div>

          <template v-else>
            <!-- question -->
            <div v-if="current">
              <div class="flex items-center gap-2 mb-2 text-xs text-gray-500">
                <span>Soal {{ index + 1 }} dari {{ questions.length }}</span>
                <span class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 capitalize">{{ current.difficulty }}</span>
                <span class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800">{{ current.points }} poin</span>
              </div>
              <p class="text-sm font-medium text-gray-800 dark:text-gray-100 mb-3">
                {{ current.question_text }}
              </p>
              <img
                v-if="current.image_url"
                :src="current.image_url"
                alt="Ilustrasi soal"
                class="max-h-56 rounded-lg mb-3 border border-gray-200 dark:border-gray-700"
              />

              <div class="space-y-2">
                <button
                  v-for="opt in current.options"
                  :key="opt.order_index"
                  class="w-full text-left px-3 py-2.5 rounded-lg border text-sm transition disabled:cursor-default"
                  :class="optionClass(opt)"
                  :disabled="!!feedback"
                  @click="pick(opt.order_index)"
                >
                  <span class="flex items-start gap-2">
                    <Icon
                      v-if="feedback"
                      :name="optionIcon(opt)"
                      class="w-4 h-4 mt-0.5 shrink-0"
                    />
                    <span class="flex-1">
                      {{ opt.option_text }}
                      <span v-if="feedback && opt.feedback" class="block text-xs mt-1 opacity-80">
                        {{ opt.feedback }}
                      </span>
                    </span>
                  </span>
                </button>
              </div>

              <!-- feedback -->
              <div v-if="feedback" class="mt-4">
                <div
                  class="rounded-lg border p-3"
                  :class="feedback.is_correct
                    ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                    : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'"
                >
                  <p class="text-sm font-semibold" :class="feedback.is_correct ? 'text-green-700 dark:text-green-400' : 'text-amber-700 dark:text-amber-400'">
                    {{ feedback.is_correct ? 'Benar.' : 'Belum tepat.' }}
                  </p>
                  <p v-if="feedback.misconception" class="text-xs text-gray-600 dark:text-gray-300 mt-1">
                    <span class="font-semibold">Kesalahpahaman yang tercatat:</span> {{ feedback.misconception }}
                  </p>
                  <p v-if="feedback.explanation" class="text-xs text-gray-600 dark:text-gray-300 mt-1">
                    {{ feedback.explanation }}
                  </p>
                </div>
                <div class="mt-3 text-xs text-gray-500">
                  Latihan bagian ini: {{ feedback.practice_answered }} soal dijawab, {{ feedback.practice_correct }} benar.
                </div>
              </div>

              <div v-if="error" class="mt-3 text-xs text-red-600 dark:text-red-400">{{ error }}</div>
            </div>

            <!-- done -->
            <div v-else class="text-center py-8">
              <Icon name="material-symbols:task-alt" class="w-12 h-12 text-green-600 mx-auto mb-2" />
              <p class="text-sm font-semibold text-gray-800 dark:text-gray-100">Latihan selesai</p>
              <p class="text-xs text-gray-500 mt-1">
                {{ summary.answered }} soal dijawab, {{ summary.correct }} benar.
              </p>
              <p class="text-xs text-gray-400 mt-2">
                Angka ini masuk ke peta pemahaman bagian ini, terpisah dari kuis dan soal interaktif.
              </p>
              <button class="mt-4 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm" @click="close">
                Tutup
              </button>
            </div>
          </template>
        </div>

        <!-- footer nav -->
        <div v-if="!loading && !loadError && questions.length" class="flex items-center justify-between gap-2 px-5 py-3 border-t border-gray-200 dark:border-gray-700">
          <button
            class="border border-gray-300 dark:border-gray-600 px-3 py-2 rounded-lg text-sm disabled:opacity-30"
            :disabled="index === 0 || !!feedback"
            @click="index--"
          >
            Sebelumnya
          </button>
          <button
            v-if="!feedback"
            class="bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm"
            :disabled="selected === null || submitting"
            @click="submit"
          >
            {{ submitting ? 'Menilai...' : 'Periksa Jawaban' }}
          </button>
          <button
            v-else
            class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm"
            @click="next"
          >
            {{ index + 1 >= questions.length ? 'Selesai' : 'Soal Berikutnya' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
const props = defineProps({
  open: { type: Boolean, default: false },
  materialId: { type: [Number, String], required: true },
  sectionId: { type: [Number, String], default: null },
  sectionTitle: { type: String, default: '' },
});
const emit = defineEmits(["close", "answered"]);

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const questions = ref([]);
const emptyMessage = ref("Belum ada soal latihan yang disetujui guru untuk bagian ini.");
const index = ref(0);
const selected = ref(null);
const feedback = ref(null);
const loading = ref(false);
const submitting = ref(false);
const loadError = ref("");
const error = ref("");
const summary = ref({ answered: 0, correct: 0 });

const current = computed(() => questions.value[index.value] || null);

const optionClass = (opt) => {
  if (!feedback.value) {
    return selected.value === opt.order_index
      ? "border-green-500 bg-green-50 dark:bg-green-900/30 text-gray-800 dark:text-gray-100"
      : "border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-200";
  }
  if (opt.is_correct) return "border-green-500 bg-green-50 dark:bg-green-900/30 text-green-800 dark:text-green-300";
  if (opt.order_index === selected.value)
    return "border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300";
  return "border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 opacity-70";
};

const optionIcon = (opt) => {
  if (opt.is_correct) return "material-symbols:check-circle";
  if (opt.order_index === selected.value) return "material-symbols:cancel";
  return "material-symbols:radio-button-unchecked";
};

const pick = (orderIndex) => {
  if (feedback.value) return;
  selected.value = orderIndex;
  error.value = "";
};

const submit = async () => {
  if (selected.value === null || submitting.value) return;
  submitting.value = true;
  error.value = "";
  try {
    const res = await $fetch(
      `${config.public.backend}/api/student/practice/${props.materialId}/sections/${props.sectionId}/answer`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: { bank_question_id: current.value.id, selected_option: selected.value },
      }
    );
    feedback.value = res;
    emit("answered", res);
  } catch (e) {
    error.value = (e && e.data && e.data.error) || "Jawaban tidak dapat dinilai.";
  } finally {
    submitting.value = false;
  }
};

const next = () => {
  if (index.value + 1 >= questions.value.length) {
    const last = feedback.value;
    summary.value = {
      answered: last ? last.practice_answered : 0,
      correct: last ? last.practice_correct : 0,
    };
    index.value = 0;
    feedback.value = null;
    selected.value = null;
    return;
  }
  index.value += 1;
  feedback.value = null;
  selected.value = null;
};

const load = async () => {
  if (!props.open || !props.sectionId) return;
  loading.value = true;
  loadError.value = "";
  error.value = "";
  index.value = 0;
  selected.value = null;
  feedback.value = null;
  try {
    const res = await $fetch(
      `${config.public.backend}/api/student/practice/${props.materialId}/sections/${props.sectionId}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    questions.value = res.questions || [];
    emptyMessage.value = res.message || emptyMessage.value;
    summary.value = {
      answered: res.practice_answered || 0,
      correct: res.practice_correct || 0,
    };
    if (res.message && questions.value.length) toast.add({ title: res.message, color: "amber" });
  } catch (e) {
    questions.value = [];
    loadError.value = (e && e.data && e.data.error) || "Latihan tidak dapat dimuat.";
  } finally {
    loading.value = false;
  }
};

const close = () => emit("close");

watch(() => props.open, (v) => { if (v) load(); });
</script>