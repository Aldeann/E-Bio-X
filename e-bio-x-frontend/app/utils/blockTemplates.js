// Utilitas template blok untuk builder materi E-Bio X.
// Template bawaan selalu tersedia; template simpanan guru disimpan di localStorage.

export const builtinTemplates = [
  {
    key: "box-definisi",
    label: "Info Box: Definisi Kunci",
    type: "box",
    icon: "material-symbols:info-outline",
    data: {
      content:
        "Definisi kunci: tuliskan pengertian istilah penting pada bagian ini agar mudah ditemukan siswa.",
      variant: "info",
    },
  },
  {
    key: "box-perhatian",
    label: "Info Box: Perhatian",
    type: "box",
    icon: "material-symbols:warning-outline",
    data: {
      content: "Catatan penting / konsep yang sering salah dipahami siswa.",
      variant: "warning",
    },
  },
  {
    key: "question-refleksi",
    label: "Pertanyaan: Refleksi",
    type: "question",
    icon: "material-symbols:quiz-outline",
    data: {
      qtype: "multiple_choice",
      question: "Apa kesimpulan utama dari materi ini?",
      options: ["Saya sudah paham.", "Masih perlu mengulang."],
      correct_answer: 0,
      explanation: "",
    },
  },
  {
    key: "question-jawaban-singkat",
    label: "Pertanyaan: Jawaban Singkat",
    type: "question",
    icon: "material-symbols:edit-note",
    data: {
      qtype: "short_answer",
      question: "Sebutkan salah satu peranan penting dari materi ini dalam kehidupan sehari-hari.",
      correct_answer: ["jawaban diterima 1", "jawaban diterima 2"],
      explanation: "",
    },
  },
  {
    key: "quiz-latihan",
    label: "Quiz: Latihan Soal",
    type: "quiz",
    icon: "hugeicons:quiz-04",
    data: {
      title: "Latihan Soal",
      questions: [
        {
          qtype: "multiple_choice",
          question: "Pertanyaan pertama?",
          options: ["Pilihan A", "Pilihan B"],
          correct_answer: 0,
          explanation: "",
        },
      ],
    },
  },
  {
    key: "diagram-kosong",
    label: "Diagram: Berlabel",
    type: "diagram",
    icon: "material-symbols:schema",
    data: { url: "", title: "", points: [], explanation: "" },
  },
];

const STORAGE_KEY = "ebiox-block-templates";

export function loadSavedTemplates() {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

export function saveBlockTemplate({ name, type, data }) {
  if (typeof window === "undefined") return [];
  const list = loadSavedTemplates();
  list.push({
    key: `saved-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    name: name || type,
    type,
    data: JSON.parse(JSON.stringify(data || {})),
  });
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch (e) {
    // penyimpanan penuh / tidak tersedia — abaikan
  }
  return list;
}

export function removeSavedTemplate(key) {
  if (typeof window === "undefined") return [];
  const list = loadSavedTemplates().filter((t) => t.key !== key);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch (e) {
    // abaikan
  }
  return list;
}