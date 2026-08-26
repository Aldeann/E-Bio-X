<template>
  <div class="p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <h2 class="text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2 mb-4">
      <Icon name="simple-icons:bookstack" class="text-green-500" /> Materi
    </h2>

    <!-- Skeleton -->
    <div v-if="materials.length === 0 && isLoading">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="i in 3" :key="i" class="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse">
          <div class="h-28 bg-green-200 dark:bg-green-900" />
          <div class="p-4 space-y-3">
            <div class="h-4 bg-green-200 dark:bg-green-800 rounded w-3/4" />
            <div class="h-3 bg-green-100 dark:bg-green-900 rounded w-full" />
            <div class="h-3 bg-green-100 dark:bg-green-900 rounded w-2/3" />
          </div>
        </div>
      </div>
    </div>

    <!-- Empty -->
    <div v-else-if="materials.length === 0 && !isLoading" class="text-center py-10">
      <Icon name="material-symbols:menu-book" class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
      <p class="text-gray-500 dark:text-gray-400">Belum ada materi di kelas ini.</p>
    </div>

    <!-- STUDENT: Card Grid -->
    <div v-else-if="isStudent" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <NuxtLink
        v-for="m in materials"
        :key="m.id"
        :to="m.category === 'interactive' ? `/student/materials/${m.id}` : m.file_url"
        :target="m.category !== 'interactive' ? '_blank' : undefined"
        class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md hover:border-green-400 transition group"
      >
        <!-- Thumbnail -->
        <div class="h-28 relative">
          <img
            v-if="m.thumbnail_url"
            :src="m.thumbnail_url"
            :alt="m.title"
            loading="lazy"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white">
            <Icon name="material-symbols:menu-book" class="w-12 h-12" />
          </div>
          <span
            v-if="m.student_progress?.finished"
            class="absolute top-2 right-2 px-2 py-0.5 text-[10px] uppercase font-bold rounded-full bg-green-600 text-white"
          >
            Selesai
          </span>
        </div>

        <!-- Body -->
        <div class="p-4 flex flex-col flex-1">
          <h3 class="font-semibold text-gray-800 dark:text-gray-100 group-hover:text-green-600 line-clamp-2">
            {{ m.title }}
          </h3>
          <p class="text-sm text-gray-500 mt-1 line-clamp-2 leading-relaxed">{{ m.description }}</p>

          <!-- Meta badges -->
          <div class="mt-3 flex flex-wrap gap-2 text-xs">
            <span v-if="m.subject" class="px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">
              {{ m.subject }}
            </span>
            <span v-if="m.phase" class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
              Fase {{ m.phase }}{{ m.class_level ? " · " + m.class_level : "" }}
            </span>
            <span
              v-if="m.estimated_time"
              class="px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 inline-flex items-center gap-1"
            >
              <Icon name="material-symbols:schedule" class="w-3.5 h-3.5" />
              {{ m.estimated_time }}
            </span>
          </div>

          <!-- Topic -->
          <div v-if="m.topic" class="mt-2 text-xs text-gray-400 flex items-center gap-2">
            <Icon name="material-symbols:category" class="w-3.5 h-3.5" />
            <span class="truncate">Topik: {{ m.topic }}</span>
          </div>

          <!-- Section info -->
          <div class="mt-2 flex items-center gap-2 text-xs text-gray-400">
            <Icon name="material-symbols:format-list-numbered" class="w-3.5 h-3.5" />
            <span>{{ m.section_count }} bagian</span>
          </div>

          <!-- Progress -->
          <div class="mt-auto pt-3">
            <MaterialProgress v-if="m.student_progress" :percentage="m.student_progress.percentage" />
            <p v-else class="text-xs text-gray-400 text-center py-1">Belum ada progress</p>
            <p class="text-[11px] text-gray-400 mt-1">
              {{ m.student_progress ? `${m.student_progress.completed} dari ${m.student_progress.total} bagian selesai` : "Belum pernah dibuka" }}
            </p>
          </div>

          <!-- Action -->
          <div class="mt-3 flex items-center justify-between">
            <span
              v-if="m.difficulty"
              class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full"
              :class="difficultyColor(m.difficulty)"
            >
              {{ m.difficulty }}
            </span>
            <span v-else />
            <span
              class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold transition"
              :class="
                m.student_progress?.finished
                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-200 group-hover:bg-gray-200 dark:group-hover:bg-gray-600'
                  : 'bg-green-600 text-white group-hover:bg-green-700'
              "
            >
              <Icon :name="actionIcon(m)" class="w-4 h-4" />
              {{ actionLabel(m) }}
            </span>
          </div>
        </div>
      </NuxtLink>
    </div>

    <!-- TEACHER: List Layout (existing) -->
    <div v-else class="space-y-4">
      <div
        v-for="material in materials"
        :key="material.id"
        class="p-5 shadow-md bg-green-50 text-green-700 rounded-xl hover:shadow-lg relative dark:shadow-green-200 dark:bg-gray-900 transition"
      >
        <button
          @click="deleteMateri(material.id)"
          class="absolute top-4 right-4 text-red-600 w-6 h-6 flex items-center justify-center hover:text-red-700"
        >
          <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
        </button>
        <div class="flex items-center gap-3 mb-3">
          <Icon name="material-symbols:menu-book-outline-rounded" class="text-green-500 text-2xl" />
          <h3 class="text-lg font-semibold text-green-800 dark:text-green-500">{{ material.title }}</h3>
          <span
            v-if="material.status === 'draft'"
            class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-700"
          >
            draft
          </span>
        </div>
        <p class="text-gray-600 dark:text-gray-300 mb-3 text-sm leading-relaxed">
          {{ material.description }}
        </p>
        <div class="flex items-center gap-3 mb-1 text-xs text-gray-400 dark:text-gray-500">
          <span>{{ material.uploaded_at }}</span>
          <span
            v-if="material.category === 'interactive'"
            class="px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300"
          >
            Interaktif · {{ material.section_count }} bagian
          </span>
        </div>
        <NuxtLink
          v-if="material.category === 'interactive'"
          :to="`/teacher/materials/builder/${material.id}`"
          class="inline-flex items-center gap-2 text-green-500 hover:text-green-800 font-medium transition"
        >
          <Icon name="material-symbols:auto-stories" class="text-lg" />
          Buka Materi
        </NuxtLink>
        <a
          v-else
          :href="material.file_url"
          target="_blank"
          class="inline-flex items-center gap-2 text-green-500 hover:text-green-800 font-medium transition"
        >
          <Icon name="material-symbols:open-in-new-rounded" class="text-lg" />
          Lihat Materi
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useSwal } from "~/utils/swal";

const token = useCookie("access_token").value;
const role = useCookie("role").value;
const swal = useSwal();
const toast = useToast();
const props = defineProps({
  courseId: String,
});

const isStudent = computed(() => role === "student");

const materials = ref([]);
const isLoading = ref(true);

const actionLabel = (m) => {
  const p = m.student_progress;
  if (!p || p.completed === 0) return "Mulai Belajar";
  if (p.finished) return "Pelajari Kembali";
  return "Lanjutkan Belajar";
};

const actionIcon = (m) => {
  const p = m.student_progress;
  if (!p || p.completed === 0) return "material-symbols:play-circle";
  if (p.finished) return "material-symbols:replay";
  return "material-symbols:arrow-forward";
};

const difficultyColor = (d) =>
  (
    {
      mudah: "bg-green-100 text-green-700",
      sedang: "bg-amber-100 text-amber-700",
      sulit: "bg-red-100 text-red-700",
    }[d] || "bg-gray-100 text-gray-600"
  );

const fetchData = async () => {
  try {
    const response = await $fetch(
      `${useRuntimeConfig().public.backend}/api/courses/materials/${props.courseId}`,
      {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    materials.value = response.data;
  } catch (err) {
    toast.add({ title: "Gagal mengambil materi.", color: "red" });
  } finally {
    isLoading.value = false;
  }
};

const deleteMateri = async (materialId) => {
  swal.fire({
    title: "Menghapus...",
    text: "Mohon tunggu",
    allowOutsideClick: false,
    didOpen: () => swal.showLoading(),
  });

  try {
    await $fetch(`${useRuntimeConfig().public.backend}/api/materials/${materialId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    swal.fire({ icon: "success", title: "Berhasil", text: "Materi berhasil dihapus" });
  } catch (err) {
    swal.fire({
      icon: "error",
      title: "Gagal",
      text: err?.data?.error || "Terjadi kesalahan saat menghapus materi",
    });
  } finally {
    fetchData();
  }
};

fetchData();
</script>
