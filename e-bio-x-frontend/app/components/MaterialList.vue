<template>
  <div class="p-3 sm:p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <h2 class="text-lg sm:text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2 mb-3 sm:mb-4">
      <Icon name="simple-icons:bookstack" class="text-green-500" /> Materi
    </h2>

    <!-- Skeleton -->
    <div v-if="materials.length === 0 && isLoading">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <div v-for="i in 3" :key="i" class="rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse">
          <div class="h-24 sm:h-28 bg-green-200 dark:bg-green-900" />
          <div class="p-3 sm:p-4 space-y-3">
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
      <p class="text-sm sm:text-base text-gray-500 dark:text-gray-400">Belum ada materi di kelas ini.</p>
    </div>

    <!-- STUDENT: Card Grid -->
    <div v-else-if="isStudent" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
      <NuxtLink
        v-for="m in materials"
        :key="m.id"
        :to="m.category === 'interactive' ? `/student/materials/${m.id}` : m.file_url"
        :target="m.category !== 'interactive' ? '_blank' : undefined"
        class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md hover:border-green-400 transition group"
      >
        <!-- Thumbnail -->
        <div class="h-24 sm:h-28 relative">
          <img
            v-if="m.thumbnail_url"
            :src="m.thumbnail_url"
            :alt="m.title"
            loading="lazy"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white">
            <Icon name="material-symbols:menu-book" class="w-10 h-10 sm:w-12 sm:h-12" />
          </div>
          <span
            v-if="m.student_progress?.finished"
            class="absolute top-2 right-2 px-2 py-0.5 text-[10px] uppercase font-bold rounded-full bg-green-600 text-white"
          >
            Selesai
          </span>
        </div>

        <!-- Body -->
        <div class="p-3 sm:p-4 flex flex-col flex-1">
          <h3 class="font-semibold text-sm sm:text-base text-gray-800 dark:text-gray-100 group-hover:text-green-600 line-clamp-2">
            {{ m.title }}
          </h3>
          <p class="text-xs sm:text-sm text-gray-500 mt-1 line-clamp-2 leading-relaxed">{{ m.description }}</p>

          <!-- Meta badges -->
          <div class="mt-2 sm:mt-3 flex flex-wrap gap-1.5 sm:gap-2 text-[10px] sm:text-xs">
            <span v-if="m.subject" class="px-1.5 sm:px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">
              {{ m.subject }}
            </span>
            <span v-if="m.phase" class="px-1.5 sm:px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
              Fase {{ m.phase }}{{ m.class_level ? " · " + m.class_level : "" }}
            </span>
            <span
              v-if="m.estimated_time"
              class="px-1.5 sm:px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 inline-flex items-center gap-1"
            >
              <Icon name="material-symbols:schedule" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
              {{ m.estimated_time }}
            </span>
          </div>

          <!-- Topic + Section (compact on mobile) -->
          <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] sm:text-xs text-gray-400">
            <span v-if="m.topic" class="flex items-center gap-1">
              <Icon name="material-symbols:category" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
              <span class="truncate max-w-[140px]">{{ m.topic }}</span>
            </span>
            <span class="flex items-center gap-1">
              <Icon name="material-symbols:format-list-numbered" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
              {{ m.section_count }} bagian
            </span>
          </div>

          <!-- Progress -->
          <div class="mt-auto pt-2 sm:pt-3">
            <MaterialProgress v-if="m.student_progress" :percentage="m.student_progress.percentage" />
            <p v-else class="text-[10px] sm:text-xs text-gray-400 text-center py-1">Belum ada progress</p>
            <p class="text-[10px] sm:text-[11px] text-gray-400 mt-1">
              {{ m.student_progress ? `${m.student_progress.completed} dari ${m.student_progress.total} bagian selesai` : "Belum pernah dibuka" }}
            </p>
          </div>

          <!-- Action -->
          <div class="mt-2 sm:mt-3 flex items-center justify-between">
            <span
              v-if="m.difficulty"
              class="text-[9px] sm:text-[10px] uppercase font-bold px-1.5 sm:px-2 py-0.5 rounded-full"
              :class="difficultyColor(m.difficulty)"
            >
              {{ m.difficulty }}
            </span>
            <span v-else />
            <span
              class="inline-flex items-center gap-1 sm:gap-1.5 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm font-semibold transition"
              :class="
                m.student_progress?.finished
                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-200 group-hover:bg-gray-200 dark:group-hover:bg-gray-600'
                  : 'bg-green-600 text-white group-hover:bg-green-700'
              "
            >
              <Icon :name="actionIcon(m)" class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              {{ actionLabel(m) }}
            </span>
          </div>
        </div>
      </NuxtLink>
    </div>

    <!-- TEACHER: Card Grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
      <div
        v-for="material in materials"
        :key="material.id"
        class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md hover:border-green-400 transition group"
      >
        <!-- Thumbnail -->
        <div class="h-24 sm:h-28 relative">
          <img
            v-if="material.thumbnail_url"
            :src="material.thumbnail_url"
            :alt="material.title"
            loading="lazy"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center text-white">
            <Icon name="material-symbols:menu-book" class="w-10 h-10 sm:w-12 sm:h-12" />
          </div>
          <span
            v-if="material.status === 'draft'"
            class="absolute top-2 right-2 px-2 py-0.5 text-[10px] uppercase font-bold rounded-full bg-amber-100 text-amber-700"
          >
            Draft
          </span>
          <button
            @click.stop="deleteMateri(material.id)"
            class="absolute top-2 left-2 w-7 h-7 flex items-center justify-center rounded-full bg-red-500 text-white hover:bg-red-600 transition opacity-0 group-hover:opacity-100"
            title="Hapus materi"
          >
            <Icon name="material-symbols:delete-rounded" class="w-4 h-4" />
          </button>
        </div>

        <!-- Body -->
        <div class="p-3 sm:p-4 flex flex-col flex-1">
          <h3 class="font-semibold text-sm sm:text-base text-gray-800 dark:text-gray-100 group-hover:text-green-600 line-clamp-2">
            {{ material.title }}
          </h3>
          <p class="text-xs sm:text-sm text-gray-500 mt-1 line-clamp-2 leading-relaxed">{{ material.description }}</p>

          <!-- Meta badges -->
          <div class="mt-2 sm:mt-3 flex flex-wrap gap-1.5 sm:gap-2 text-[10px] sm:text-xs">
            <span v-if="material.subject" class="px-1.5 sm:px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300">
              {{ material.subject }}
            </span>
            <span v-if="material.phase" class="px-1.5 sm:px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
              Fase {{ material.phase }}{{ material.class_level ? " · " + material.class_level : "" }}
            </span>
            <span
              v-if="material.category === 'interactive'"
              class="px-1.5 sm:px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300"
            >
              Interaktif · {{ material.section_count }} bagian
            </span>
          </div>

          <!-- Meta info -->
          <div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] sm:text-xs text-gray-400">
            <span v-if="material.topic" class="flex items-center gap-1">
              <Icon name="material-symbols:category" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
              <span class="truncate max-w-[140px]">{{ material.topic }}</span>
            </span>
            <span class="flex items-center gap-1">
              <Icon name="material-symbols:schedule" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
              {{ material.uploaded_at }}
            </span>
          </div>

          <!-- Spacer -->
          <div class="flex-1" />

          <!-- Action -->
          <div class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
            <NuxtLink
              v-if="material.category === 'interactive'"
              :to="`/teacher/materials/builder/${material.id}`"
              class="block w-full bg-green-600 hover:bg-green-700 text-white text-xs sm:text-sm px-3 py-2 rounded-lg text-center transition font-medium"
            >
              <Icon name="material-symbols:auto-stories" class="w-4 h-4 inline mr-1" />
              Buka Materi
            </NuxtLink>
            <a
              v-else
              :href="material.file_url"
              target="_blank"
              class="block w-full bg-green-600 hover:bg-green-700 text-white text-xs sm:text-sm px-3 py-2 rounded-lg text-center transition font-medium"
            >
              <Icon name="material-symbols:open-in-new-rounded" class="w-4 h-4 inline mr-1" />
              Lihat Materi
            </a>
          </div>
        </div>
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

const shortLabel = (m) => {
  const p = m.student_progress;
  if (!p || p.completed === 0) return "Mulai";
  if (p.finished) return "Ulangi";
  return "Lanjut";
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
