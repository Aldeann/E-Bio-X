<template>
  <div class="container mx-auto px-4 py-4">
    <div class="flex flex-col md:flex-row justify-between items-center mb-6">
      <h2 class="text-2xl font-semibold mb-3">
        Halo,
        <span class="text-green-700 dark:text-green-500">{{ useCookie("username").value }}</span
        >!
      </h2>
      <button
        class="bg-green-600 hover:bg-green-700 hover:shadow hover:shadow-green-300 text-white px-4 py-2 rounded"
        @click="showCreateClassSwal">
        + Buat Kelas Baru
      </button>
    </div>

    <h4 class="text-lg font-medium mb-4">Kelas Saya</h4>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-if="myCourses.length === 0" class="text-gray-500 text-sm mt-4">
        Anda belum membuat kelas. Klik tombol di atas untuk membuat kelas baru.
      </div>
      <div
        v-else
        v-for="(kelas, index) in myCourses"
        :key="index"
        class="bg-white dark:bg-gray-900 border rounded-lg p-4 shadow-md shadow-green-300 hover:shadow-lg hover:shadow-green-300 relative">
        <button
          @click="deleteClass(kelas.id)"
          class="absolute top-0 right-0 text-red-600 w-6 h-6 flex items-center justify-center hover:text-red-700">
          <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
        </button>
        <div class="flex justify-between items-start mb-2">
          <h5 class="text-lg font-semibold">{{ kelas.name }}</h5>
          <span class="bg-green-100 text-green-600 text-sm px-2 py-1 rounded">
            <Icon name="mdi:account-multiple" />
            {{ kelas.students }}
          </span>
        </div>
        <p class="text-sm text-gray-600 mb-4">{{ kelas.description }}</p>
        <div class="flex justify-between items-center text-sm text-gray-500">
          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-600 dark:text-gray-200">Kode: {{ kelas.code }}</span>
            <button
              @click="copyToClipboard(kelas.code)"
              class="text-green-500 hover:text-green-800 transition duration-200">
              <Icon name="material-symbols:content-copy" class="w-5 h-5" />
            </button>
          </div>

          <NuxtLink
            :to="'/teacher/course/' + kelas.id"
            class="inline-flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-500 hover:shadow hover:shadow-green-300  transition">
            <Icon name="material-symbols:login" class="w-4 h-4" />
            Kelola
          </NuxtLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const swal = useSwal();
const toast = useToast();
const myCourses = ref([]);

const fetchCoursesData = async () => {
  const { data, error } = await useAsyncData("my-courses", () =>
    $fetch(`${config.public.backend}/api/courses/teacher`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
  );

  if (error.value) {
    toast.add({title: 'Gagal mengambil data kelas.', color: 'red'});
  } else {
    myCourses.value = data.value;
  }
};

const showCreateClassSwal = async () => {
  const { value: className } = await swal.fire({
    title: "Buat Kelas Baru",
    input: "text",
    inputLabel: "Nama Kelas",
    inputPlaceholder: "Masukkan nama kelas",
    showCancelButton: true,
    confirmButtonText: "Buat",
    cancelButtonText: "Batal",
    inputValidator: (value) => {
      if (!value) {
        return "Nama kelas wajib diisi!";
      }
    },
  });

  if (className) {
    createClass(className);
  }
};

const createClass = async (className) => {
  try {
    await $fetch(`${config.public.backend}/api/courses`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: className,
      }),
    });

    fetchCoursesData();

    toast.add({title: 'Kelas berhasil dibuat', color: 'green' })
  } catch (err) {
    toast.add({title: 'Gagal membuat kelas.', color: 'red' })
  }
};

const copyToClipboard = (text) => {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text);
    toast.add({ title: `${text} disalin ke clipboard`, color: 'green' })
  }
};

const deleteClass = async (id) => {
  const result = await swal.fire({
    title: "Hapus kelas ini?",
    text: "Siswa akan dikeluarkan dan kelas tidak akan bisa dikembalikan lagi.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Hapus",
    cancelButtonText: "Batal",
  });

  if (!result.isConfirmed) {
    return;
  }
  try {
    await $fetch(`${config.public.backend}/api/courses/${id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
    await fetchCoursesData();
    toast.add({title: 'Kelas berhasil dihapus.', color: 'green' })
  } catch (err) {
    toast.add({title: 'Gagal menghapus kelas.', color: 'red' })
  }
};

fetchCoursesData();

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>
