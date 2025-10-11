<script setup>
import { useSwal } from "~/utils/swal";
import Cookies from "js-cookie";
import { useRuntimeConfig } from "#app";
import { ref, onMounted, computed } from "vue";

const config = useRuntimeConfig();
const materials = ref([]);
const courses = ref([]);
const toast = useToast();

onMounted(async () => {
  await fetchMaterial();
});

const token = Cookies.get("access_token");
const swal = useSwal();

const fetchMaterial = async () => {
  try {
    materials.value = await $fetch(`${config.public.backend}/api/materials`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    courses.value = [...new Set(materials.value.map((m) => m.course))];
  } catch (err) {
    toast.add({title: "Gagal mengambil data.", color: 'red'});
  }
};

const deleteMaterial = async (material) => {
  const confirm = await swal.fire({
    icon: "warning",
    title: "Yakin hapus materi ini?",
    showCancelButton: true,
    confirmButtonText: "Ya",
    cancelButtonText: "Batal",
  });
  if (!confirm.isConfirmed) return;

  try {
    await $fetch(`${config.public.backend}/api/materials/${material.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    materials.value = materials.value.filter((u) => u.id !== material.id);
    swal.fire("Berhasil", "Materi berhasil dihapus", "success");
  } catch (err) {
    swal.fire("Gagal", "Tidak bisa hapus material", "error");
  }
};

definePageMeta({
  layout: "admin",
  middleware: "auth",
  role: "admin",
});

const columns = [
  { header: "Judul", accessorKey: "title" },
  { header: "Url", accessorKey: "file_url" },
  { header: "Kelas", accessorKey: "course" },
];

const filters = computed(() => [
  { title: "Kelas", options: courses.value, accessorKey: "course" },
]);
</script>

<template>
  <div class="p-4 pb-2">
    <h2 class="text-2xl font-semibold text-green-600 dark:text-green-500">Data Materi</h2>
  </div>
  <div class="overflow-x-auto max-w-full">
    <AdminTable
      :data="materials"
      :columns="columns"
      :pageSize="10"
      :filters="filters"
      @refresh="fetchMaterial"
      :onDelete="deleteMaterial" />
  </div>
</template>
