<script setup>
import { ref, computed, onMounted } from "vue";
import { useSwal } from "~/utils/swal";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();

const materials = ref([]);
const loading = ref(true);
const filterCourse = ref("");

const courseList = computed(() => {
  const set = new Set();
  materials.value.forEach((m) => (m.courses || []).forEach((c) => set.add(c)));
  return [...set].sort();
});

const filteredMaterials = computed(() => {
  if (!filterCourse.value) return materials.value;
  return materials.value.filter((m) => (m.courses || []).includes(filterCourse.value));
});

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/materials`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    materials.value = res || [];
  } catch (e) {
    toast.add({ title: "Gagal memuat materi.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
};

const difficultyColor = (v) =>
  ({ mudah: "bg-green-100 text-green-700", sedang: "bg-amber-100 text-amber-700", sulit: "bg-red-100 text-red-700" }[v] || "bg-gray-100 text-gray-600");

const publishToggle = async (m) => {
  const target = m.status === "published" ? "draft" : "published";
  const result = await swal.fire({
    title: target === "published" ? "Publikasikan materi?" : "Batalkan publikasi?",
    text:
      target === "published"
        ? "Materi akan terlihat oleh siswa."
        : "Materi akan disembunyikan dari siswa.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: target === "published" ? "Ya, Publish" : "Ya, Jadikan Draft",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/materials/${m.id}/publish`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
      body: { status: target },
    });
    toast.add({
      title: target === "published" ? "Materi dipublikasikan." : "Materi diubah menjadi draft.",
      color: "green",
    });
    fetchData();
  } catch (e) {
    toast.add({ title: "Gagal mengubah status.", color: "red" });
  }
};

const deleteMaterial = async (m) => {
  const result = await swal.fire({
    title: "Hapus materi ini?",
    text: `"${m.title}" beserta semua section dan file akan dihapus permanen.`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });
  if (!result.isConfirmed) return;
  try {
    await $fetch(`${config.public.backend}/api/materials/${m.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Materi dihapus.", color: "green" });
    fetchData();
  } catch (e) {
    toast.add({ title: "Gagal menghapus materi.", color: "red" });
  }
};

onMounted(fetchData);

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>

<template>
  <div>
    <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-3">
      <div>
        <h1 class="text-2xl font-bold text-green-700 dark:text-green-400">
          Materi Pembelajaran
        </h1>
        <p class="text-sm text-gray-500">Kelola materi interaktif untuk siswa.</p>
      </div>
      <NuxtLink
        to="/teacher/materials/create"
        class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded flex items-center gap-1"
      >
        <Icon name="material-symbols:add" class="w-5 h-5" />
        Buat Materi
      </NuxtLink>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="i in 6" :key="i" class="rounded-xl border border-gray-200 dark:border-gray-700 p-4 animate-pulse bg-white dark:bg-gray-900 h-48"></div>
    </div>

    <div v-else-if="materials.length === 0" class="text-center py-20 text-gray-400">
      <Icon name="material-symbols:auto-stories-outline" class="w-16 h-16 mx-auto mb-3" />
      <p>Belum ada materi. Klik <span class="font-semibold">+ Buat Materi</span> untuk memulai.</p>
    </div>

    <div v-else>
      <div class="flex items-center gap-2 mb-4">
        <label class="text-sm text-gray-500">Filter kelas:</label>
        <select v-model="filterCourse" class="border border-gray-300 dark:border-gray-700 rounded px-3 py-1.5 text-sm bg-white dark:bg-gray-900">
          <option value="">Semua kelas</option>
          <option v-for="c in courseList" :key="c" :value="c">{{ c }}</option>
        </select>
        <span class="text-xs text-gray-400">{{ filteredMaterials.length }} materi</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="m in filteredMaterials"
        :key="m.id"
        class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md transition"
      >
        <div
          class="h-24 flex items-center justify-center text-white font-bold text-lg"
          :style="m.thumbnail_url ? '' : undefined"
        >
          <img
            v-if="m.thumbnail_url"
            :src="m.thumbnail_url"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
            <Icon name="material-symbols:menu-book" class="w-10 h-10" />
          </div>
        </div>

        <div class="p-4 flex flex-col flex-1">
          <div class="flex items-start justify-between gap-2">
            <NuxtLink
              :to="`/teacher/materials/builder/${m.id}`"
              class="font-semibold text-gray-800 dark:text-gray-100 hover:text-green-600 line-clamp-2"
            >
              {{ m.title }}
            </NuxtLink>
            <span
              class="shrink-0 text-[10px] uppercase font-bold px-2 py-0.5 rounded-full"
              :class="
                m.status === 'published'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-amber-100 text-amber-700'
              "
            >
              {{ m.status }}
            </span>
          </div>

          <p class="text-xs text-gray-500 mt-1">
            {{ m.subject }} · Fase {{ m.phase }}{{ m.class_level ? " · " + m.class_level : "" }}
          </p>
          <p class="text-xs text-gray-400">Topik: {{ m.topic || "-" }}</p>

          <div class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="c in m.courses"
              :key="c"
              class="px-2 py-0.5 text-[10px] rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 inline-flex items-center gap-1"
            >
              <Icon name="material-symbols:groups" class="w-3 h-3" />
              {{ c }}
            </span>
            <span
              v-if="!m.courses || m.courses.length === 0"
              class="px-2 py-0.5 text-[10px] rounded-full bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
            >
              Umum
            </span>
          </div>

          <div class="text-xs text-gray-400 mt-1 flex flex-wrap gap-x-3">
            <span class="inline-flex items-center gap-1">
              <Icon name="material-symbols:category" class="w-3.5 h-3.5" />
              {{ m.section_count }} section
            </span>
            <span
              class="inline-flex items-center gap-1 px-1.5 rounded"
              :class="difficultyColor(m.difficulty)"
            >
              {{ m.difficulty || "sedang" }}
            </span>
          </div>

          <div class="mt-3">
            <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span class="inline-flex items-center gap-1">
                <Icon name="mdi:account-multiple" class="w-4 h-4" />
                {{ m.students || 0 }} siswa
              </span>
              <span>{{ m.completion_percentage || 0 }}% selesai</span>
            </div>
            <div class="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                class="h-full bg-green-500 rounded-full"
                :style="{ width: (m.completion_percentage || 0) + '%' }"
              ></div>
            </div>
          </div>

          <div class="text-[11px] text-gray-400 mt-3 flex justify-between">
            <span>Dibuat: {{ formatDate(m.created_at) }}</span>
            <span>Diubah: {{ formatDate(m.updated_at || m.created_at) }}</span>
          </div>

          <div class="flex flex-wrap gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
            <NuxtLink
              :to="`/teacher/materials/builder/${m.id}`"
              class="px-3 py-1.5 text-xs rounded font-semibold bg-green-600 hover:bg-green-700 text-white flex items-center gap-1"
            >
              <Icon name="material-symbols:edit-square" class="w-3.5 h-3.5" />
              Edit
            </NuxtLink>
            <NuxtLink
              :to="`/teacher/materials/preview/${m.id}`"
              target="_blank"
              class="px-3 py-1.5 text-xs rounded font-semibold bg-blue-500 hover:bg-blue-600 text-white flex items-center gap-1"
            >
              <Icon name="material-symbols:visibility" class="w-3.5 h-3.5" />
              Preview
            </NuxtLink>
            <NuxtLink
              :to="`/teacher/materials/analytics/${m.id}`"
              class="px-3 py-1.5 text-xs rounded font-semibold bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-100 flex items-center gap-1"
            >
              <Icon name="material-symbols:monitoring" class="w-3.5 h-3.5" />
              Analitik
            </NuxtLink>
            <button
              @click="publishToggle(m)"
              class="px-3 py-1.5 text-xs rounded font-semibold flex items-center gap-1"
              :class="
                m.status === 'published'
                  ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                  : 'bg-green-100 text-green-700 hover:bg-green-200'
              "
            >
              <Icon
                :name="m.status === 'published' ? 'material-symbols:visibility-off' : 'material-symbols:public'"
                class="w-3.5 h-3.5"
              />
              {{ m.status === "published" ? "Unpublish" : "Publish" }}
            </button>
            <button
              @click="deleteMaterial(m)"
              class="px-3 py-1.5 text-xs rounded font-semibold bg-red-100 text-red-600 hover:bg-red-200 flex items-center gap-1"
            >
              <Icon name="material-symbols:delete-rounded" class="w-3.5 h-3.5" />
              Hapus
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>