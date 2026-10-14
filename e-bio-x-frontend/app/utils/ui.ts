// Peta warna & label semantik bersama untuk UI guru.
//
// Sebelumnya tiap halaman mendefinisikan sendiri warna "mudah/sedang/sulit"
// dan "Baik Sekali/Baik/Cukup/Kurang" dengan nilai yang berbeda-beda, sehingga
// warna yang sama bisa berarti berbeda di halaman berbeda. Semua halaman guru
// kini memakai fungsi di sini agar arti warna konsisten.

type AnyKey = string | number | null | undefined;

const norm = (k: AnyKey) => String(k ?? "").toLowerCase();

/** Label tingkat soal dalam bahasa Indonesia (kunci bisa easy/medium/hard). */
export const difficultyLabel = (key: AnyKey): string => {
  const map: Record<string, string> = {
    easy: "Mudah",
    mudah: "Mudah",
    medium: "Sedang",
    sedang: "Sedang",
    hard: "Sulit",
    sulit: "Sulit",
    unclassified: "Belum ditentukan",
  };
  return map[norm(key)] || (key == null ? "–" : String(key));
};

/** Kelas lencana (badge) untuk tingkat soal: latar lembut + teks tegas. */
export const difficultyBadgeClass = (key: AnyKey): string => {
  const map: Record<string, string> = {
    easy: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    mudah: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    medium: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    sedang: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    hard: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
    sulit: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
    unclassified: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300",
  };
  return map[norm(key)] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";
};

/** Kelas teks warna untuk tingkat soal (tanpa latar). */
export const difficultyTextClass = (key: AnyKey): string => {
  const map: Record<string, string> = {
    easy: "text-green-600",
    mudah: "text-green-600",
    medium: "text-amber-600",
    sedang: "text-amber-600",
    hard: "text-red-600",
    sulit: "text-red-600",
    unclassified: "text-gray-500",
  };
  return map[norm(key)] || "text-gray-500";
};

/** Kelas batang (bar) solid untuk tingkat soal. */
export const difficultyBarClass = (key: AnyKey): string => {
  const map: Record<string, string> = {
    easy: "bg-green-500",
    mudah: "bg-green-500",
    medium: "bg-amber-500",
    sedang: "bg-amber-500",
    hard: "bg-red-500",
    sulit: "bg-red-500",
    unclassified: "bg-gray-400",
  };
  return map[norm(key)] || "bg-gray-400";
};

/** Label status belajar siswa dalam bahasa Indonesia. */
export const statusLearningLabel = (key: AnyKey): string => {
  const map: Record<string, string> = {
    belum_dimulai: "Belum Dimulai",
    dimulai: "Dimulai",
    sedang_belajar: "Sedang Belajar",
    selesai: "Selesai",
  };
  return map[norm(key)] || (key == null ? "–" : String(key));
};

/** Kelas lencana untuk status belajar siswa. */
export const statusLearningClass = (key: AnyKey): string => {
  const map: Record<string, string> = {
    belum_dimulai: "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300",
    dimulai: "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-400",
    sedang_belajar: "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-400",
    selesai: "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-400",
  };
  return map[norm(key)] || map.belum_dimulai;
};

// Label penguasaan bagian: "Baik Sekali" > "Baik" > "Cukup" > "Kurang".
const masteryOrder = ["Baik Sekali", "Baik", "Cukup", "Kurang"] as const;

const masteryKey = (label: AnyKey): string => {
  const s = String(label ?? "").trim();
  if (masteryOrder.includes(s as (typeof masteryOrder)[number])) return s;
  // Terima juga kunci huruf kecil sebagai jaring pengaman.
  const found = masteryOrder.find((m) => m.toLowerCase() === s.toLowerCase());
  return found || "";
};

/** Kelas teks warna untuk label penguasaan bagian. */
export const masteryTextClass = (label: AnyKey): string => {
  const map: Record<string, string> = {
    "Baik Sekali": "text-green-600",
    Baik: "text-emerald-600",
    Cukup: "text-amber-500",
    Kurang: "text-red-500",
  };
  return map[masteryKey(label)] || "text-gray-500";
};

/** Kelas batang (bar) solid untuk label penguasaan bagian. */
export const masteryBarClass = (label: AnyKey): string => {
  const map: Record<string, string> = {
    "Baik Sekali": "bg-green-600",
    Baik: "bg-emerald-500",
    Cukup: "bg-amber-500",
    Kurang: "bg-red-500",
  };
  return map[masteryKey(label)] || "bg-gray-400";
};

/** Kelas sel heatmap penguasaan bagian (latar penuh + teks kontras). */
export const masteryHeatClass = (label: AnyKey): string => {
  const map: Record<string, string> = {
    "Baik Sekali": "bg-green-600 text-white",
    Baik: "bg-emerald-500 text-white",
    Cukup: "bg-amber-400 text-gray-900",
    Kurang: "bg-red-500 text-white",
  };
  return map[masteryKey(label)] || "bg-gray-400 text-white";
};
