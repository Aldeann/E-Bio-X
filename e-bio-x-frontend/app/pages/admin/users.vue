<script setup>
import { useSwal } from "~/utils/swal";
import Cookies from "js-cookie";
import { useRuntimeConfig } from "#app";
import { ref, onMounted } from "vue";

const config = useRuntimeConfig();
const users = ref([]);

onMounted(async () => {
  await fetchUsers();
});

const token = Cookies.get("access_token");
const swal = useSwal();
const toast = useToast();

const fetchUsers = async () => {
  try {
    users.value = await $fetch(`${config.public.backend}/api/users`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch (err) {
    console.error("Gagal mengambil data pengguna", err);
  }
};

const createUser = async () => {
  const { value: formValues } = await swal.fire({
    title: "Tambah Pengguna Baru",
    html:
      '<input id="swal-input-name" class="p-2 mb-3 bg-gray-100 dark:bg-gray-700 w-full" placeholder="Nama">' +
      '<input id="swal-input-email" class="p-2 mb-3 bg-gray-100 dark:bg-gray-700 w-full" placeholder="Email" type="email">' +
      '<input id="swal-input-password" class="p-2 mb-3 bg-gray-100 dark:bg-gray-700 w-full" placeholder="Kata sandi" type="password">' +
      '<select id="swal-input-role" class="p-2 mb-3 bg-gray-100 dark:bg-gray-700 w-full">' +
        '<option value="" disabled selected>Pilih peran</option>' +
        '<option value="student">Siswa</option>' +
        '<option value="teacher">Guru</option>' +
        '<option value="admin">Admin</option>' +
      '</select>',
    focusConfirm: false,
    showCancelButton: true,
    confirmButtonText: "Simpan",
    cancelButtonText: "Batal",
    preConfirm: () => {
      const name = document.getElementById('swal-input-name').value;
      const email = document.getElementById('swal-input-email').value;
      const password = document.getElementById('swal-input-password').value;
      const role = document.getElementById('swal-input-role').value;
      if (!name || !email || !password || !role) {
        swal.showValidationMessage('Semua kolom harus diisi');
        return false;
      }
      if (!/^[\w-]+(\.[\w-]+)*@([\w-]+\.)+[a-zA-Z]{2,7}$/.test(email)) {
        swal.showValidationMessage('Email tidak valid');
        return false;
      }
      if (password.length < 8) {
        swal.showValidationMessage('Kata sandi minimal 8 karakter');
        return false;
      }
      return { name, email, password, role };
    }
  });

  if (!formValues) return;

  try {
    await $fetch(`${config.public.backend}/api/users`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formValues,
    });
    toast.add({title: "Pengguna berhasil dibuat", color: "green"});
    fetchUsers();
  } catch (err) {
    console.error(err);
    toast.add({title: "Pengguna gagal dibuat.", color: "red"});
  }
};

const updateUser = async (user) => {
  const confirm = await swal.fire({
    icon: "question",
    title: `Ubah pengguna: ${user.name}`,
    html: `
      <input id="swal-input-name" class="p-2 mb-3 bg-gray-100 dark:bg-gray-700 w-full" value="${user.name}" placeholder="Nama">
      <input id="swal-input-password" class="p-2 mb-3 bg-gray-100 dark:bg-gray-700 w-full" placeholder="Kata sandi baru (opsional)" type="password">
      <select id="swal-input-role" class="p-2 mb-3 bg-gray-100 dark:bg-gray-700 w-full">
        <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
        <option value="teacher" ${user.role === 'teacher' ? 'selected' : ''}>Guru</option>
        <option value="student" ${user.role === 'student' ? 'selected' : ''}>Siswa</option>
      </select>
    `,
    showCancelButton: true,
    confirmButtonText: "Simpan",
    cancelButtonText: "Batal",
    preConfirm: () => {
      const name = document.getElementById('swal-input-name').value;
      const password = document.getElementById('swal-input-password').value;
      const role = document.getElementById('swal-input-role').value;

      if (!name.trim()) {
        swal.showValidationMessage('Nama tidak boleh kosong');
        return false;
      }

      return {
        name: name.trim(),
        password: password || undefined,
        role: role
      };
    }
  });

  if (!confirm.isConfirmed || !confirm.value) return;

  try {
    const updateData = {};
    
    if (confirm.value.name !== user.name) {
      updateData.name = confirm.value.name;
    }
    
    if (confirm.value.password) {
      if (confirm.value.password.length < 8) {
        swal.showValidationMessage('Kata sandi minimal 8 karakter');
        return false;
      }
      updateData.password = confirm.value.password;
    }
    
    if (confirm.value.role !== user.role) {
      updateData.role = confirm.value.role;
    }

    if (Object.keys(updateData).length === 0) {
      toast.add({title: "Tidak ada perubahan untuk disimpan"});
      return;
    }

    await $fetch(`${config.public.backend}/api/users/${user.id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: updateData,
    });
    
    toast.add({title: "Data pengguna berhasil diperbarui"});
    fetchUsers();
  } catch (err) {
    console.error(err);
    toast.add({title: "Data pengguna gagal diperbarui", color: "red"});
  }
};

const deleteUser = async (user) => {
  const confirm = await swal.fire({
    icon: "warning",
    title: `Hapus pengguna ini?`,
    text:`${
      user.role == "teacher" ? "Kelas dan kuis milik guru ini akan ikut terhapus." : "Seluruh data milik pengguna ini akan ikut terhapus."
    }`,
    showCancelButton: true,
    confirmButtonText: "Ya",
    cancelButtonText: "Batal",
  });
  if (!confirm.isConfirmed) return;

  try {
    await $fetch(`${config.public.backend}/api/users/${user.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    users.value = users.value.filter((u) => u.id !== user.id);
    swal.fire("Berhasil", "Pengguna dan seluruh datanya berhasil dihapus", "success");
  } catch (err) {
    console.error(err);
    swal.fire("Gagal", "Pengguna tidak bisa dihapus", "error");
  }
};

definePageMeta({
  layout: "admin",
  middleware: "auth",
  role: "admin",
});

const roleLabels = {
  admin: "Admin",
  teacher: "Guru",
  student: "Siswa",
};

const columns = [
  { header: "Nama", accessorKey: "name" },
  { header: "Email", accessorKey: "email" },
  {
    header: "Peran",
    accessorKey: "role",
    cell: ({ row }) => roleLabels[row.original.role] || row.original.role,
  },
];

const filters = [
  {
    title: "Peran",
    options: [
      { value: "admin", label: "Admin" },
      { value: "teacher", label: "Guru" },
      { value: "student", label: "Siswa" },
    ],
    accessorKey: "role",
  },
];
</script>

<template>
  <div class="p-4 pb-2">
    <h2 class="text-2xl font-semibold text-green-600 dark:text-green-500">Data Pengguna</h2>
    <div class="absolute top-0 right-0 mt-6 mr-6">
      <button
          class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
          @click="createUser">
          Buat Pengguna Baru
      </button>
    </div>
  </div>
  <div class="overflow-x-auto max-w-full">
    <AdminTable
      :data="users"
      :columns="columns"
      :pageSize="10"
      :filters="filters"
      @refresh="fetchUsers"
      :onUpdate="updateUser"
      :onDelete="deleteUser" />
  </div>
</template>
