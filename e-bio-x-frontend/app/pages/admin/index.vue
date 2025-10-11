<template>
  <div class="p-6 bg-gray-100 dark:bg-gray-900 min-h-screen">
    <h1
      class="text-2xl font-semibold text-green-700 dark:text-green-400 flex items-center gap-2 mb-6"
    >
      <Icon name="mdi:home" class="text-green-500 dark:text-green-300" /> Dashboard Admin
    </h1>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
      <div
        class="bg-white dark:bg-gray-800 border border-green-200 dark:border-green-600 rounded-lg p-4 shadow flex flex-col gap-2"
      >
        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">Total Pengguna</h3>
        <p class="text-2xl font-bold text-green-600 dark:text-green-400">
          {{ stats.totalUsers }}
        </p>
        <NuxtLink
          to="/admin/users"
          class="flex items-center gap-1 text-green-600 px-3 py-1 rounded-md text-xs font-medium hover:text-green-500 dark:hover:text-green-600 hover:scale-105 transition-all duration-200"
        >
          <Icon name="mdi:cog" class="w-4 h-4" />
          Kelola
        </NuxtLink>
      </div>
      <div
        class="bg-white dark:bg-gray-800 border border-green-200 dark:border-green-600 rounded-lg p-4 shadow flex flex-col gap-2"
      >
        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">Total Kursus</h3>
        <p class="text-2xl font-bold text-green-600 dark:text-green-400">
          {{ stats.totalCourses }}
        </p>
        <NuxtLink
          to="/admin/courses"
          class="flex items-center gap-1 text-green-600 px-3 py-1 rounded-md text-xs font-medium hover:text-green-500 dark:hover:text-green-600 hover:scale-105 transition-all duration-200"
        >
          <Icon name="mdi:cog" class="w-4 h-4" />
          Kelola
        </NuxtLink>
      </div>
      <div
        class="bg-white dark:bg-gray-800 border border-green-200 dark:border-green-600 rounded-lg p-4 shadow flex flex-col gap-2"
      >
        <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">Total Materi</h3>
        <p class="text-2xl font-bold text-green-600 dark:text-green-400">
          {{ stats.totalMaterials }}
        </p>
        <NuxtLink
          to="/admin/materials"
          class="flex items-center gap-1 text-green-600 px-3 py-1 rounded-md text-xs font-medium hover:text-green-500 dark:hover:text-green-600 hover:scale-105 transition-all duration-200"
        >
          <Icon name="mdi:cog" class="w-4 h-4" />
          Kelola
        </NuxtLink>
      </div>
    </div>

    <div class="mb-8">
      <h2
        class="text-xl font-semibold text-green-700 dark:text-green-400 mb-4 flex items-center gap-2"
      >
        <Icon name="mdi:user" class="text-green-500 dark:text-green-300" /> User
      </h2>
      <AdminTable
        :data="recentUsers"
        :columns="userColumns"
        :pageSize="5"
        :onUpdate="updateUser"
        :onDelete="deleteUser"
      />
    </div>

    <div class="mb-8">
      <h2
        class="text-xl font-semibold text-green-700 dark:text-green-400 mb-4 flex items-center gap-2"
      >
        <Icon name="arcticons:classchartsstudents" class="text-green-500 dark:text-green-300" />
        Kelas
      </h2>
      <AdminTable
        :data="recentCourses"
        :columns="courseColumns"
        :pageSize="5"
        :onDelete="deleteCourse"
      />
    </div>

    <div>
      <h2
        class="text-xl font-semibold text-green-700 dark:text-green-400 mb-4 flex items-center gap-2"
      >
        <Icon name="simple-icons:bookstack" class="text-green-500 dark:text-green-300" /> Materi
      </h2>
      <AdminTable
        :data="recentMaterials"
        :columns="materialColumns"
        :pageSize="5"
        :onDelete="deleteMaterial"
      />
    </div>
  </div>
</template>

<script setup>
import Cookies from "js-cookie";
import { ref } from "vue";

const toast = useToast();
const config = useRuntimeConfig();
const token = Cookies.get("access_token");

const stats = ref({
  totalUsers: 0,
  totalCourses: 0,
  totalMaterials: 0,
});

const recentUsers = ref([]);
const recentCourses = ref([]);
const recentMaterials = ref([]);

const userColumns = [
  { header: "Nama", accessorKey: "name" },
  { header: "Email", accessorKey: "email" },
];

const courseColumns = [
  { header: "Nama Kursus", accessorKey: "name" },
  { header: "ID", accessorKey: "id" },
];

const materialColumns = [
  { header: "Nama Materi", accessorKey: "title" },
  { header: "Kelas", accessorKey: "course" },
];

const fetchStats = async () => {
  try {
    const [users, courses, materials] = await Promise.all([
      $fetch(`${config.public.backend}/api/users`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      $fetch(`${config.public.backend}/api/courses`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      $fetch(`${config.public.backend}/api/materials`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ]);

    stats.value.totalUsers = users.length;
    stats.value.totalCourses = courses.length;
    stats.value.totalMaterials = materials.length;

    // Mengambil data terbaru (misalnya, 5 teratas)
    recentUsers.value = users.slice(0, 5);
    recentCourses.value = courses.slice(0, 5);
    recentMaterials.value = materials.slice(0, 5);
  } catch (error) {
    toast.add({
      title: "Gagal memuat data dashboard: " + error.message,
      color: "red",
    });
  }
};

// Fungsi aksi untuk tabel
const updateUser = async (user) => {
  try {
    await $fetch(`${config.public.backend}/api/users/${user.id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: user,
    });
    toast.add({ title: "Sukses", description: "Pengguna diperbarui", color: "green" });
    await fetchStats(); // Refresh data
  } catch (error) {
    toast.add({ title: "Error", description: "Gagal memperbarui pengguna", color: "red" });
  }
};

const deleteUser = async (user) => {
  try {
    await $fetch(`${config.public.backend}/api/users/${user.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Sukses", description: "Pengguna dihapus", color: "green" });
    await fetchStats();
  } catch (error) {
    toast.add({ title: "Error", description: "Gagal menghapus pengguna", color: "red" });
  }
};

const deleteCourse = async (course) => {
  try {
    await $fetch(`${config.public.backend}/api/courses/${course.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Sukses", description: "Kursus dihapus", color: "green" });
    await fetchStats();
  } catch (error) {
    toast.add({ title: "Error", description: "Gagal menghapus kursus", color: "red" });
  }
};

const deleteMaterial = async (material) => {
  try {
    await $fetch(`${config.public.backend}/api/materials/${material.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    toast.add({ title: "Sukses", description: "Materi dihapus", color: "green" });
    await fetchStats();
  } catch (error) {
    toast.add({ title: "Error", description: "Gagal menghapus materi", color: "red" });
  }
};

onMounted(() => {
  fetchStats();
});

definePageMeta({
  layout: "admin",
  middleware: "auth",
  role: "admin",
});
</script>