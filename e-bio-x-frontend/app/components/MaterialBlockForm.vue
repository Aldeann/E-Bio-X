<script setup>
import { reactive, computed, watch } from "vue";
import { useSwal } from "~/utils/swal";

const props = defineProps({
  block: { type: Object, required: true },
  materialId: { type: [String, Number], required: true },
});

const emit = defineEmits(["save", "cancel"]);

const type = computed(() => props.block.type);

const blank = () => ({
  text: { content: "" },
  heading: { content: "", level: 2 },
  image: { url: "", caption: "" },
  video: { url: "", title: "" },
  pdf: { url: "", title: "" },
  link: { url: "", label: "" },
  box: { content: "", variant: "info" },
  question: { question: "", options: ["", ""], correct_answer: 0, explanation: "" },
  quiz: {
    title: "Latihan Soal",
    questions: [{ question: "", options: ["", ""], correct_answer: 0, explanation: "" }],
  },
});

const form = reactive(
  JSON.parse(JSON.stringify(props.block.data || blank()[props.block.type] || {}))
);

watch(
  () => props.block.id,
  () => {
    const next = JSON.parse(JSON.stringify(props.block.data || blank()[props.block.type] || {}));
    Object.keys(form).forEach((k) => delete form[k]);
    Object.assign(form, next);
  }
);

const optionLabel = (i) => String.fromCharCode(65 + i);

const addOption = (target) => {
  if (!target.options) target.options = [];
  if (target.options.length >= 10) return;
  target.options.push("");
};

const removeOption = (target, index) => {
  target.options.splice(index, 1);
  if (target.correct_answer >= target.options.length) {
    target.correct_answer = Math.max(0, target.options.length - 1);
  }
  if (target.options.length === 0) target.options = [""];
};

const addQuizQuestion = () => {
  form.questions.push({ question: "", options: ["", ""], correct_answer: 0, explanation: "" });
};

const removeQuizQuestion = (index) => form.questions.splice(index, 1);

const inputClass =
  "w-full p-2 border border-gray-300 dark:border-gray-700 rounded bg-white dark:bg-gray-900 text-sm focus:outline-green-500";
const labelClass = "block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300";

const validate = () => {
  const d = form;
  const fail = (msg) => {
    useSwal().fire({ icon: "warning", title: "Periksa kembali", text: msg });
    return false;
  };

  switch (type.value) {
    case "text":
    case "heading":
      if (!d.content || !d.content.trim()) return fail("Konten tidak boleh kosong.");
      break;
    case "image":
      if (!d.url) return fail("Pilih gambar terlebih dahulu.");
      break;
    case "video":
      if (!d.url) return fail("Pilih video atau masukkan URL video.");
      break;
    case "pdf":
      if (!d.url) return fail("Pilih file PDF terlebih dahulu.");
      break;
    case "link":
      if (!d.url) return fail("URL tautan wajib diisi.");
      break;
    case "box":
      if (!d.content || !d.content.trim()) return fail("Isi kotak info tidak boleh kosong.");
      break;
    case "question": {
      if (!d.question || !d.question.trim()) return fail("Pertanyaan wajib diisi.");
      const filled = d.options.filter((o) => o && o.trim()).length;
      if (filled < 2) return fail("Minimal butuh 2 pilihan jawaban.");
      break;
    }
    case "quiz": {
      if (!d.questions || d.questions.length === 0) return fail("Quiz minimal 1 soal.");
      for (const q of d.questions) {
        if (!q.question || !q.question.trim()) return fail("Ada soal yang belum diisi.");
        if (!q.options || q.options.filter((o) => o && o.trim()).length < 2)
          return fail(`Soal "${q.question.slice(0, 30)}..." butuh minimal 2 pilihan jawaban.`);
      }
      break;
    }
  }
  return true;
};

const save = () => {
  if (!validate()) return;
  emit("save", { type: type.value, data: JSON.parse(JSON.stringify(form)) });
};
</script>

<template>
  <div class="space-y-3">
    <!-- TEXT -->
    <template v-if="type === 'text'">
      <label :class="labelClass">Isi teks</label>
      <textarea v-model="form.content" rows="5" :class="inputClass" placeholder="Tulis konten materi..."></textarea>
    </template>

    <!-- HEADING -->
    <template v-else-if="type === 'heading'">
      <div>
        <label class="labelClass">Teks judul</label>
        <input v-model="form.content" type="text" :class="inputClass" placeholder="Judul bab / sub-bab" />
      </div>
      <div>
        <label class="labelClass">Ukuran judul</label>
        <select v-model="form.level" :class="inputClass">
          <option :value="1">H1 - Judul utama</option>
          <option :value="2">H2 - Sub judul</option>
          <option :value="3">H3 - Sub-sub judul</option>
        </select>
      </div>
    </template>

    <!-- IMAGE -->
    <template v-else-if="type === 'image'">
      <MaterialInlineUpload v-model="form.url" :material-id="materialId" preview-type="image" />
      <div>
        <label class="labelClass">Caption (opsional)</label>
        <input v-model="form.caption" type="text" :class="inputClass" placeholder="Keterangan gambar" />
      </div>
    </template>

    <!-- VIDEO -->
    <template v-else-if="type === 'video'">
      <div>
        <label class="labelClass">Judul video (opsional)</label>
        <input v-model="form.title" type="text" :class="inputClass" placeholder="Nama video" />
      </div>
      <MaterialInlineUpload v-model="form.url" :material-id="materialId" preview-type="video" accept=".mp4,.webm" />
      <p class="text-xs text-gray-400">Bisa juga tempel link YouTube pada kolom URL.</p>
    </template>

    <!-- PDF -->
    <template v-else-if="type === 'pdf'">
      <div>
        <label class="labelClass">Judul dokumen (opsional)</label>
        <input v-model="form.title" type="text" :class="inputClass" placeholder="Nama dokumen" />
      </div>
      <MaterialInlineUpload v-model="form.url" :material-id="materialId" preview-type="pdf" accept=".pdf" />
    </template>

    <!-- LINK -->
    <template v-else-if="type === 'link'">
      <div>
        <label class="labelClass">Label tautan</label>
        <input v-model="form.label" type="text" :class="inputClass" placeholder="Contoh: Baca lebih lanjut" />
      </div>
      <div>
        <label class="labelClass">URL</label>
        <input v-model="form.url" type="url" :class="inputClass" placeholder="https://..." />
      </div>
    </template>

    <!-- BOX -->
    <template v-else-if="type === 'box'">
      <div>
        <label class="labelClass">Warna kotak</label>
        <select v-model="form.variant" :class="inputClass">
          <option value="info">Info (biru)</option>
          <option value="success">Penting (hijau)</option>
          <option value="warning">Perhatian (kuning)</option>
          <option value="danger">Bahaya (merah)</option>
        </select>
      </div>
      <div>
        <label class="labelClass">Isi kotak</label>
        <textarea v-model="form.content" rows="4" :class="inputClass" placeholder="Info tambahan / highlight..."></textarea>
      </div>
    </template>

    <!-- QUESTION -->
    <template v-else-if="type === 'question'">
      <div>
        <label class="labelClass">Pertanyaan</label>
        <textarea v-model="form.question" rows="2" :class="inputClass" placeholder="Tulis pertanyaan..."></textarea>
      </div>
      <div>
        <label class="labelClass">Pilihan jawaban</label>
        <div v-for="(opt, i) in form.options" :key="i" class="flex items-center gap-2 mb-1">
          <label class="flex items-center gap-1 text-sm cursor-pointer shrink-0">
            <input type="radio" name="correct-answer" :value="i" v-model.number="form.correct_answer" />
            <span class="font-semibold">{{ optionLabel(i) }}</span>
          </label>
          <input v-model="form.options[i]" type="text" :class="inputClass" :placeholder="`Opsi ${optionLabel(i)}`" />
          <button
            @click="removeOption(form, i)"
            class="text-red-500 hover:text-red-700 shrink-0"
            title="Hapus opsi"
          >
            <Icon name="material-symbols:backspace" class="w-5 h-5" />
          </button>
        </div>
        <button @click="addOption(form)" class="text-green-600 hover:text-green-700 text-sm font-medium">
          + Tambah Opsi
        </button>
        <p class="text-xs text-gray-400 mt-1">Tandai radio pada pilihan yang benar.</p>
      </div>
      <div>
        <label class="labelClass">Penjelasan (opsional)</label>
        <textarea v-model="form.explanation" rows="2" :class="inputClass" placeholder="Penjelasan jawaban..."></textarea>
      </div>
    </template>

    <!-- QUIZ -->
    <template v-else-if="type === 'quiz'">
      <div>
        <label class="labelClass">Judul quiz</label>
        <input v-model="form.title" type="text" :class="inputClass" placeholder="Contoh: Latihan Soal Virus" />
      </div>

      <div v-for="(q, qi) in form.questions" :key="qi" class="border border-green-200 dark:border-green-800 rounded-lg p-3">
        <div class="flex items-center justify-between mb-2">
          <label class="font-semibold text-sm text-green-600">Soal {{ qi + 1 }}</label>
          <button @click="removeQuizQuestion(qi)" class="text-red-500 hover:text-red-700">
            <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
          </button>
        </div>
        <textarea v-model="q.question" rows="2" :class="inputClass" placeholder="Tulis soal..."></textarea>
        <div class="mt-2">
          <div v-for="(opt, oi) in q.options" :key="oi" class="flex items-center gap-2 mb-1">
            <label class="flex items-center gap-1 text-sm cursor-pointer shrink-0">
              <input type="radio" :name="'q' + qi + '-correct'" :value="oi" v-model.number="q.correct_answer" />
              <span class="font-semibold">{{ optionLabel(oi) }}</span>
            </label>
            <input v-model="q.options[oi]" type="text" :class="inputClass" :placeholder="`Opsi ${optionLabel(oi)}`" />
            <button @click="removeOption(q, oi)" class="text-red-500 hover:text-red-700 shrink-0">
              <Icon name="material-symbols:backspace" class="w-5 h-5" />
            </button>
          </div>
          <button @click="addOption(q)" class="text-green-600 hover:text-green-700 text-sm font-medium">
            + Tambah Opsi
          </button>
        </div>
        <div class="mt-2">
          <label class="labelClass">Penjelasan (opsional)</label>
          <textarea v-model="q.explanation" rows="1" :class="inputClass" placeholder="Penjelasan..." ></textarea>
        </div>
      </div>

      <button
        @click="addQuizQuestion"
        class="text-green-600 hover:text-green-700 text-sm font-medium"
      >
        + Tambah Soal
      </button>
    </template>

    <div class="flex gap-2 pt-2">
      <button
        @click="save"
        class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-1"
      >
        <Icon name="material-symbols:save" class="w-4 h-4" />
        Simpan
      </button>
      <button
        @click="emit('cancel')"
        class="bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-100 px-4 py-2 rounded-lg text-sm font-semibold"
      >
        Batal
      </button>
    </div>
  </div>
</template>