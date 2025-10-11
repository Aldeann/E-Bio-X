<script setup>
import { useSwal } from "~/utils/swal";
import Cookies from "js-cookie";
import { useRuntimeConfig } from "#app";
import { ref, onMounted, computed } from "vue";

const config = useRuntimeConfig();
const courses = ref([]);
const teachers = ref([]);
const toast = useToast();

onMounted(async () => {
  await fetchCourse();
});

const token = Cookies.get("access_token");
const swal = useSwal();

const fetchCourse = async () => {
  try {
    courses.value = await $fetch(`${config.public.backend}/api/courses`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    teachers.value = [...new Set(courses.value.map((m) => m.teacher))];
  } catch (err) {
    toast.add({title: "Gagal mengambil data.", color: 'red'});
  }
};

const deleteCourse = async (course) => {
  const confirm = await swal.fire({
    icon: "warning",
    title: "Yakin hapus kelas ini?",
    showCancelButton: true,
    confirmButtonText: "Ya",
    cancelButtonText: "Batal",
  });
  if (!confirm.isConfirmed) return;

  try {
    await $fetch(`${config.public.backend}/api/courses/${course.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    courses.value = courses.value.filter((u) => u.id !== course.id);
    swal.fire("Berhasil", "Kelas berhasil dihapus", "success");
  } catch (err) {
    swal.fire("Gagal", "Gagal menghapus kelas", "error");
  }
};

definePageMeta({
  layout: "admin",
  middleware: "auth",
  role: "admin",
});

const columns = [
  { header: "Nama Kelas", accessorKey: "name" },
  { header: "Pengajar", accessorKey: "teacher" },
  { header: "Jumlah sisiwa", accessorKey: "students" },
];

const filters = computed(() => [
  { title: "Teacher", options: teachers.value, accessorKey: "teacher" },
]);
</script>

<template>
  <div class="p-4 pb-2">
    <h2 class="text-2xl font-semibold text-green-600 dark:text-green-500">Data Materi</h2>
  </div>
  <div class="overflow-x-auto max-w-full">
    <AdminTable
      :data="courses"
      :columns="columns"
      :pageSize="10"
      :filters="filters"
      @refresh="fetchCourse"
      :onDelete="deleteCourse" />
  </div>
</template>
