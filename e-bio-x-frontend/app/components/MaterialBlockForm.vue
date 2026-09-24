<script setup>
import { reactive, computed, watch } from "vue";
import { useSwal } from "~/utils/swal";

const props = defineProps({
  block: { type: Object, required: true },
  materialId: { type: [String, Number], required: true },
});

const emit = defineEmits(["save", "cancel"]);

const type = computed(() => props.block.type);

const newQuestion = () => ({
  qtype: "multiple_choice",
  question: "",
  options: ["", ""],
  correct_answer: 0,
  explanation: "",
});

const blank = () => ({
  text: { content: "" },
  heading: { content: "", level: 2 },
  image: { url: "", caption: "" },
  video: { url: "", title: "" },
  pdf: { url: "", title: "" },
  link: { url: "", label: "" },
  box: { content: "", variant: "info" },
  question: {
    qtype: "multiple_choice",
    question: "",
    options: ["", ""],
    correct_answer: 0,
    explanation: "",
  },
  quiz: { title: "Latihan Soal", questions: [newQuestion()] },
  diagram: { url: "", title: "", points: [], explanation: "" },
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

const qtypeOptions = [
  { value: "multiple_choice", label: "Pilihan Ganda" },
  { value: "true_false", label: "Benar / Salah" },
  { value: "multi_select", label: "Pilihan Ganda (multi-jawaban)" },
  { value: "short_answer", label: "Isian Singkat" },
  { value: "matching", label: "Menjodohkan" },
];

const addOption = (target) => {
  if (!target.options) target.options = [];
  if (target.options.length >= 10) return;
  target.options.push("");
};

const removeOption = (target, index) => {
  target.options.splice(index, 1);
  if (Array.isArray(target.correct_answer)) {
    target.correct_answer = target.correct_answer
      .filter((x) => x !== index)
      .map((x) => (x > index ? x - 1 : x));
  } else if (target.correct_answer >= target.options.length) {
    target.correct_answer = Math.max(0, target.options.length - 1);
  }
  if (target.options.length === 0) target.options = [""];
};

const addQuizQuestion = () => form.questions.push(newQuestion());
const removeQuizQuestion = (index) => form.questions.splice(index, 1);

const setQuestionType = (q, t) => {
  q.qtype = t;
  if (t === "true_false") {
    q.options = ["Benar", "Salah"];
    if (typeof q.correct_answer !== "number") q.correct_answer = 0;
  } else if (t === "multiple_choice") {
    if (!Array.isArray(q.options) || q.options.length === 0) q.options = ["", ""];
    if (typeof q.correct_answer !== "number") q.correct_answer = 0;
  } else if (t === "multi_select") {
    if (!Array.isArray(q.options) || q.options.length === 0) q.options = ["", ""];
    if (!Array.isArray(q.correct_answer)) q.correct_answer = [];
  } else if (t === "short_answer") {
    if (!Array.isArray(q.correct_answer)) q.correct_answer = [];
    delete q.options;
  } else if (t === "matching") {
    if (!Array.isArray(q.left) || q.left.length === 0) q.left = ["", ""];
    if (!Array.isArray(q.right) || q.right.length === 0) q.right = ["", "", ""];
    if (!Array.isArray(q.answer)) q.answer = [];
  }
};

const toggleMultiCorrect = (q, oi) => {
  if (!Array.isArray(q.correct_answer)) q.correct_answer = [];
  const idx = q.correct_answer.indexOf(oi);
  if (idx >= 0) q.correct_answer.splice(idx, 1);
  else q.correct_answer.push(oi);
};

const linesToArray = (text) =>
  String(text || "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

const setLeft = (q, e) => (q.left = linesToArray(e.target.value));
const setRight = (q, e) => (q.right = linesToArray(e.target.value));
const setShortCorrect = (q, e) => (q.correct_answer = linesToArray(e.target.value));

const setMatchAnswer = (q, i, v) => {
  if (!Array.isArray(q.answer)) q.answer = [];
  while (q.answer.length <= i) q.answer.push(0);
  q.answer[i] = v === "" || v === undefined || v === null ? undefined : Number(v);
};

// ---------- Diagram interaktif ----------
const addDiagramPoint = (e) => {
  if (!form.url) return;
  const rect = e.currentTarget.getBoundingClientRect();
  const x = Math.round(((e.clientX - rect.left) / rect.width) * 1000) / 10;
  const y = Math.round(((e.clientY - rect.top) / rect.height) * 1000) / 10;
  if (!Array.isArray(form.points)) form.points = [];
  form.points.push({
    id: `pt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    x,
    y,
    label: "",
  });
};

const removeDiagramPoint = (index) => form.points.splice(index, 1);

const diagramMarkerStyle = (p) => ({ left: `${p.x || 0}%`, top: `${p.y || 0}%` });

// ---------- Validasi ----------
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
    case "diagram": {
      if (!d.url) return fail("Pilih gambar diagram terlebih dahulu.");
      if (!Array.isArray(d.points) || d.points.length === 0)
        return fail("Klik pada gambar untuk menambah minimal 1 titik label.");
      if (d.points.some((p) => !p.label || !p.label.trim()))
        return fail("Semua titik diagram wajib diberi label.");
      const labels = d.points.map((p) => p.label.trim().toLowerCase());
      if (new Set(labels).size !== labels.length)
        return fail("Label diagram harus unik (tidak boleh ada yang sama).");
      break;
    }
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
        const t = q.qtype || "multiple_choice";
        const preview = q.question.slice(0, 30);
        if (t === "matching") {
          const leftCount = (q.left || []).filter((s) => s && s.trim()).length;
          const rightCount = (q.right || []).filter((s) => s && s.trim()).length;
          if (leftCount < 2)
            return fail(`Soal "${preview}..." butuh minimal 2 item di kolom kiri.`);
          if (rightCount < 2)
            return fail(`Soal "${preview}..." butuh minimal 2 item di kolom kanan.`);
          const ans = q.answer || [];
          if (ans.length !== leftCount || ans.some((v) => v === undefined || v === null || v === ""))
            return fail(`Lengkapi pasangan jawaban pada soal "${preview}...".`);
          if (ans.some((v) => v >= rightCount))
            return fail("Ada pasangan yang menunjuk item kolom kanan yang tidak valid.");
        } else if (t === "short_answer") {
          if (
            !Array.isArray(q.correct_answer) ||
            q.correct_answer.filter((s) => s && s.trim()).length === 0
          )
            return fail(`Soal "${preview}..." butuh minimal 1 jawaban yang diterima.`);
        } else if (t === "multi_select") {
          if (!q.options || q.options.filter((o) => o && o.trim()).length < 2)
            return fail(`Soal "${preview}..." butuh minimal 2 pilihan jawaban.`);
          if (!Array.isArray(q.correct_answer) || q.correct_answer.length === 0)
            return fail(`Tandai minimal satu jawaban benar pada soal "${preview}...".`);
        } else {
          if (!q.options || q.options.filter((o) => o && o.trim()).length < 2)
            return fail(`Soal "${preview}..." butuh minimal 2 pilihan jawaban.`);
        }
      }
      break;
    }
  }
  return true;
};

const save = () => {
  if (!validate()) return;
  const payload = JSON.parse(JSON.stringify(form));
  // rapikan data menjodohkan: pastikan answer sepanjang kiri
  if (type.value === "quiz" && Array.isArray(payload.questions)) {
    for (const q of payload.questions) {
      if ((q.qtype || "multiple_choice") === "matching" && Array.isArray(q.left)) {
        q.answer = (q.answer || []).slice(0, q.left.length);
      }
    }
  }
  emit("save", { type: type.value, data: payload });
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

    <!-- DIAGRAM INTERAKTIF -->
    <template v-else-if="type === 'diagram'">
      <div>
        <label class="labelClass">Judul diagram (opsional)</label>
        <input v-model="form.title" type="text" :class="inputClass" placeholder="Contoh: Struktur Sel Hewan" />
      </div>
      <MaterialInlineUpload v-model="form.url" :material-id="materialId" preview-type="image" />

      <template v-if="form.url">
        <div>
          <label class="labelClass">Klik pada gambar untuk menambah titik label</label>
          <div class="relative rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 inline-block max-w-full">
            <img
              :src="form.url"
              alt="Diagram"
              class="max-w-full h-auto block cursor-crosshair"
              draggable="false"
              @click="addDiagramPoint"
            />
            <span
              v-for="(p, pi) in form.points"
              :key="p.id"
              class="absolute -translate-x-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-green-600 border-2 border-white text-white text-xs font-bold flex items-center justify-center pointer-events-none z-10"
              :style="diagramMarkerStyle(p)"
            >
              {{ pi + 1 }}
            </span>
          </div>
        </div>

        <div v-if="form.points.length" class="space-y-2">
          <div v-for="(p, pi) in form.points" :key="p.id" class="flex items-center gap-2">
            <span class="w-6 h-6 shrink-0 rounded-full bg-green-600 text-white text-xs font-bold flex items-center justify-center">
              {{ pi + 1 }}
            </span>
            <span class="text-xs text-gray-400 shrink-0 w-16">{{ p.x }}%, {{ p.y }}%</span>
            <input v-model="p.label" type="text" :class="inputClass" placeholder="Nama bagian / label..." />
            <button @click="removeDiagramPoint(pi)" class="text-red-500 hover:text-red-700 shrink-0" title="Hapus titik">
              <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
            </button>
          </div>
          <p class="text-xs text-gray-400">
            Label harus unik — siswa akan mencocokkan titik dengan label dari daftar acak.
          </p>
        </div>
      </template>

      <div>
        <label class="labelClass">Penjelasan (opsional)</label>
        <textarea v-model="form.explanation" rows="2" :class="inputClass" placeholder="Penjelasan setelah siswa menjawab..."></textarea>
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

      <div v-for="(q, qi) in form.questions" :key="qi" class="border border-green-200 dark:border-green-800 rounded-lg p-3 space-y-2">
        <div class="flex items-center justify-between">
          <label class="font-semibold text-sm text-green-600">Soal {{ qi + 1 }}</label>
          <button @click="removeQuizQuestion(qi)" class="text-red-500 hover:text-red-700" title="Hapus soal">
            <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
          </button>
        </div>

        <div>
          <label :class="labelClass">Tipe soal</label>
          <select
            :class="inputClass"
            :value="q.qtype || 'multiple_choice'"
            @change="(e) => setQuestionType(q, e.target.value)"
          >
            <option v-for="t in qtypeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>

        <textarea v-model="q.question" rows="2" :class="inputClass" placeholder="Tulis soal..."></textarea>

        <!-- Editor opsi: PG / Benar-Salah / Multi-pilih -->
        <div v-if="q.qtype === 'multiple_choice' || q.qtype === 'true_false' || q.qtype === 'multi_select'" class="mt-1">
          <div v-for="(opt, oi) in q.options" :key="oi" class="flex items-center gap-2 mb-1">
            <label class="flex items-center gap-1 text-sm cursor-pointer shrink-0">
              <input
                v-if="q.qtype === 'multi_select'"
                type="checkbox"
                :checked="(q.correct_answer || []).includes(oi)"
                @change="toggleMultiCorrect(q, oi)"
              />
              <input
                v-else
                type="radio"
                :name="'q' + qi + '-correct'"
                :value="oi"
                v-model.number="q.correct_answer"
              />
              <span class="font-semibold">{{ optionLabel(oi) }}</span>
            </label>
            <input v-model="q.options[oi]" type="text" :class="inputClass" :placeholder="`Opsi ${optionLabel(oi)}`" />
            <button
              v-if="q.qtype !== 'true_false'"
              @click="removeOption(q, oi)"
              class="text-red-500 hover:text-red-700 shrink-0"
              title="Hapus opsi"
            >
              <Icon name="material-symbols:backspace" class="w-5 h-5" />
            </button>
          </div>
          <div class="flex items-center justify-between">
            <button v-if="q.qtype !== 'true_false'" @click="addOption(q)" class="text-green-600 hover:text-green-700 text-sm font-medium">
              + Tambah Opsi
            </button>
            <span v-else class="text-xs text-gray-400">Pilihan tetap: Benar / Salah.</span>
            <span v-if="q.qtype === 'multi_select'" class="text-xs text-gray-400">
              Centang pilihan yang benar (boleh lebih dari satu).
            </span>
          </div>
        </div>

        <!-- Editor isian singkat -->
        <div v-else-if="q.qtype === 'short_answer'" class="mt-1">
          <label :class="labelClass">Jawaban yang diterima (satu per baris)</label>
          <textarea
            :class="inputClass"
            rows="2"
            placeholder="contoh:&#10;sel eukariotik"
            :value="(q.correct_answer || []).join('\n')"
            @input="setShortCorrect(q, $event)"
          ></textarea>
          <p class="text-xs text-gray-400">Penilaian tidak membedakan huruf besar/kecil.</p>
        </div>

        <!-- Editor menjodohkan -->
        <div v-else-if="q.qtype === 'matching'" class="mt-1 space-y-2">
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label :class="labelClass">Kolom kiri (satu per baris)</label>
              <textarea
                :class="inputClass"
                rows="3"
                placeholder="Mitokondria&#10;Ribosom"
                :value="(q.left || []).join('\n')"
                @input="setLeft(q, $event)"
              ></textarea>
            </div>
            <div>
              <label :class="labelClass">Kolom kanan (satu per baris)</label>
              <textarea
                :class="inputClass"
                rows="3"
                placeholder="Tempat respirasi&#10;Sintesis protein"
                :value="(q.right || []).join('\n')"
                @input="setRight(q, $event)"
              ></textarea>
            </div>
          </div>
          <div>
            <label :class="labelClass">Pasangan yang benar</label>
            <div v-for="(l, li) in q.left || []" :key="li" class="flex items-center gap-2 mb-1 text-sm">
              <span class="w-6 h-6 shrink-0 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 flex items-center justify-center font-semibold">
                {{ optionLabel(li) }}
              </span>
              <span class="flex-1 truncate text-gray-700 dark:text-gray-200">{{ l || `Item ${li + 1}` }}</span>
              <select
                :class="inputClass"
                :value="(q.answer && q.answer[li]) ?? ''"
                @change="(e) => setMatchAnswer(q, li, e.target.value)"
              >
                <option value="" disabled>Pilih...</option>
                <option v-for="(r, ri) in q.right || []" :key="ri" :value="ri">
                  {{ optionLabel(ri) }}. {{ r || `Item ${ri + 1}` }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <div>
          <label :class="labelClass">Penjelasan (opsional)</label>
          <textarea v-model="q.explanation" rows="1" :class="inputClass" placeholder="Penjelasan..."></textarea>
        </div>
      </div>

      <button @click="addQuizQuestion" class="text-green-600 hover:text-green-700 text-sm font-medium">
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