<template>
  <div class="p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <h2 class="text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
      <Icon name="simple-icons:bookstack" class="text-green-500" /> Materi
    </h2>

    <div class="my-4">
      <div v-if="materials.length === 0 && isLoading">
        <!-- Skeleton Loader for Empty State -->
        <div class="space-y-4">
          <div class="flex gap-4 animate-pulse">
            <div class="w-10 h-10 bg-green-200 rounded-full"></div>
            <div class="flex-1 space-y-2">
              <div class="h-6 bg-green-200 rounded w-3/4"></div>
              <div class="h-4 bg-green-200 rounded w-1/2"></div>
            </div>
          </div>
          <div class="h-3 bg-green-200 rounded w-1/4"></div>
        </div>
      </div>
      
      <div v-if="materials.length === 0 && !isLoading">
        <p class="text-gray-500">Belum ada materi yang diupload.</p>
      </div>

      <div
        v-for="material in materials"
        :key="material.id"
        class="mb-4 p-5 shadow-md bg-green-50 text-green-700 rounded-xl hover:shadow-lg relative dark:shadow-green-200 dark:bg-gray-900 transition"
      >
        <button
          v-if="useCookie('role').value === 'teacher'"
          @click="deleteMateri(material.id)"
          class="absolute top-4 right-4 text-red-600 w-6 h-6 flex items-center justify-center hover:text-red-700"
        >
          <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
        </button>
        <div class="flex items-center gap-3 mb-3">
          <Icon name="material-symbols:menu-book-outline-rounded" class="text-green-500 text-2xl" />
          <h3 class="text-lg font-semibold text-green-800 dark:text-green-500">{{ material.title }}</h3>
        </div>
        <p class="text-gray-600 dark:text-gray-300 mb-3 text-sm leading-relaxed">
          {{ material.description }}
        </p>
        <p class="text-gray-400 dark:text-gray-500 mb-1 text-sm leading-relaxed">
          {{ material.uploaded_at }}
        </p>
        <a
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
import { ref } from "vue";
import { useSwal } from "~/utils/swal";

const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();
const props = defineProps({
  courseId: String,
});

const materials = ref([]);
const isLoading = ref(true); // Track loading state

const fetchData = async () => {
  try {
    const response = await $fetch(
      `${useRuntimeConfig().public.backend}/api/courses/materials/${props.courseId}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    materials.value = response.data;
  } catch (err) {
    toast.add({title: 'Gagal mengambil materi.', color: 'red'})
  } finally {
    isLoading.value = false;
  }
};

const deleteMateri = async (materialId) => {
  swal.fire({
    title: "Menghapus...",
    text: "Mohon tunggu",
    allowOutsideClick: false,
    didOpen: () => {
      swal.showLoading();
    },
  });

  try {
    await $fetch(`${useRuntimeConfig().public.backend}/api/materials/${materialId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    swal.fire({
      icon: "success",
      title: "Berhasil",
      text: "Materi berhasil dihapus",
    });
  } catch (err) {
    swal.fire({
      icon: "error",
      title: "Gagal",
      text: "Terjadi kesalahan saat menghapus materi",
    });
  } finally {
    fetchData();
  }
};

fetchData();
</script>
