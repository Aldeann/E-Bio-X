<template>
  <div>
    <PageHeader
      title="Dasbor Guru"
      :subtitle="username ? `Halo, ${username}!` : 'Ringkasan aktivitas kelas Anda'"
    >
      <button
        class="bg-green-600 hover:bg-green-700 hover:shadow hover:shadow-green-300 text-white px-4 py-2 rounded"
        @click="showCreateClassSwal">
        + Buat Kelas Baru
      </button>
      <NuxtLink
        to="/teacher/materials"
        class="bg-white dark:bg-gray-900 border border-green-600 text-green-700 dark:text-green-400 hover:bg-green-50 dark:hover:bg-gray-800 px-4 py-2 rounded flex items-center gap-1">
        <Icon name="material-symbols:menu-book" class="w-4 h-4" />
        Materi Pembelajaran
      </NuxtLink>
    </PageHeader>

    <h4 class="text-lg font-medium mb-4">Kelas Saya</h4>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-if="myCourses.length === 0" class="col-span-full">
        <EmptyState
          icon="mdi:class-variant"
          title="Belum ada kelas"
          description="Klik 'Buat Kelas Baru' untuk membuat kelas pertama."
        />
      </div>
      <AppCard v-for="(kelas, index) in myCourses" :key="index" withShadow class="relative">
        <div class="p-4">
          <button
            @click="deleteClass(kelas.id)"
            class="absolute top-1 right-1 text-red-600 w-9 h-9 flex items-center justify-center rounded-lg hover:text-red-700 hover:bg-red-50 dark:hover:bg-gray-800 transition"
            aria-label="Hapus kelas">
            <Icon name="material-symbols:delete-rounded" class="w-5 h-5" />
          </button>
          <div class="flex justify-between items-start mb-2 pr-8">
            <h5 class="text-lg font-semibold truncate">{{ kelas.name }}</h5>
            <span class="bg-green-100 text-green-600 text-sm px-2 py-1 rounded flex items-center gap-1">
              <Icon name="mdi:account-multiple" />
              {{ kelas.students }}
            </span>
          </div>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">{{ kelas.description }}</p>
          <div class="flex justify-between items-center text-sm text-gray-500">
            <div class="flex items-center space-x-2">
              <span class="text-sm text-gray-600 dark:text-gray-200">Kode: {{ kelas.code }}</span>
              <button
                @click="copyToClipboard(kelas.code)"
                class="text-green-500 hover:text-green-800 p-1.5 -m-1.5 rounded transition duration-200"
                aria-label="Salin kode kelas">
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
      </AppCard>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const username = useCookie("username").value;
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
