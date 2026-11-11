<template>
  <div class="rounded-xl shadow-lg dark:shadow-lg dark:shadow-green-200 py-8">
    <div class="max-w-3xl mx-auto px-4">
      <div class="text-center mb-10 animate-fade-in">
        <div class="relative mb-4 inline-block">
          <div
            class="w-20 h-20 rounded-full bg-green-300 flex items-center justify-center mx-auto shadow-lg animate-fade-in-slow">
            <UAvatar :alt="userData.name" size="3xl" class="bg-green-300 text-white"/>
          </div>
        </div>
        <div class="flex items-center justify-center gap-2">
          <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-2">
            {{ userData.name || "Pengguna" }}
          </h1>
          <button
          class="w-9 h-9 p-1.5 text-yellow-400 hover:text-yellow-500 transition duration-300"
          @click="updateName"
          aria-label="Ubah nama">
          <Icon name="material-symbols:edit" />
        </button>
      </div>
      </div>

      <div>
        <!-- this is a button and modal -->
        <EditPassword  />
      </div>
    </div>
  </div>
</template>

<script setup>
import Cookies from "js-cookie";
import { useSwal } from "~/utils/swal";

const config = useRuntimeConfig();
const swal = useSwal();
const accessToken = Cookies.get("access_token");

const userData = ref({
  name: Cookies.get("username"),
  role: Cookies.get("role"),
  has_password: Cookies.get("has_password"),
  profile_pic: Cookies.get("profile_pic"),
});

const updateName = async () => {
  const { value: name } = await swal.fire({
    title: "Ubah nama",
    input: "text",
    inputValue: userData.value.name,
    showCancelButton: true,
    confirmButtonText: "Simpan",
    cancelButtonText: "Batal",
    inputValidator: (value) => !value && "Nama tidak boleh kosong.",
  });

  if (name) {
    try {
      await $fetch(`${config.public.backend}/api/user/me`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${accessToken}` },
        body: { name },
      });
      userData.value.name = name;
      swal.fire("Berhasil", "Nama berhasil diperbarui.", "success");

      Cookies.set("username", name);
    } catch (e) {
      swal.fire("Gagal", "Nama belum bisa diperbarui. Coba lagi.", "error");
    }
  }
};

definePageMeta({
  middleware: "auth",
});
</script>
