<script setup>
import Cookies from "js-cookie";
import { useRuntimeConfig } from "#app";
import { ref, onMounted } from "vue";

const config = useRuntimeConfig();
const token = Cookies.get("access_token");
const toast = useToast();

const foreword = ref("");
const saving = ref(false);

onMounted(async () => {
  try {
    const res = await $fetch(`${config.public.backend}/api/app-settings`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    foreword.value = (res && res.foreword) || "";
  } catch (e) {
    toast.add({ title: "Gagal memuat pengaturan.", color: "red" });
  }
});

const save = async () => {
  saving.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/app-settings`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: { foreword: foreword.value },
    });
    foreword.value = (res && res.foreword) || "";
    toast.add({ title: "Pengaturan disimpan.", color: "green" });
  } catch (e) {
    toast.add({ title: "Gagal menyimpan pengaturan.", color: "red" });
  } finally {
    saving.value = false;
  }
};

definePageMeta({
  layout: "admin",
  middleware: "auth",
  role: "admin",
});
</script>

<template>
  <div class="p-6 bg-gray-100 dark:bg-gray-900 min-h-screen">
    <h1
      class="text-2xl font-semibold text-green-700 dark:text-green-400 flex items-center gap-2 mb-6"
    >
      <Icon name="material-symbols:settings-applications" class="text-green-500 dark:text-green-300" />
      Pengaturan Aplikasi
    </h1>

    <div
      class="bg-white dark:bg-gray-800 border border-green-200 dark:border-green-600 rounded-lg p-4 shadow max-w-3xl"
    >
      <label class="block text-sm font-medium text-gray-900 dark:text-gray-100">
        Kata Pengantar
      </label>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 mb-3">
        Teks ini tampil di bagian atas <strong>semua</strong> halaman materi murid.
        Satu baris = satu paragraf.
      </p>
      <textarea
        v-model="foreword"
        rows="8"
        class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-sm p-3 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500"
        placeholder="Tulis kata pengantar (mis. alasan website ini dikembangkan)..."
      ></textarea>
      <div class="mt-3 flex justify-end">
        <button
          type="button"
          :disabled="saving"
          @click="save"
          class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-500 disabled:opacity-60"
        >
          <Icon name="material-symbols:save" class="w-4 h-4" />
          {{ saving ? "Menyimpan..." : "Simpan" }}
        </button>
      </div>
    </div>
  </div>
</template>
