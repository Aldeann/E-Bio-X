<template>
  <div class="container py-4">
    <!-- Header Dashboard -->
    <div class="row mb-4">
      <div class="col-md-8">
        <h2 class="text-2xl font-semibold mb-3">
          Hi, <span class="text-green-600 dark:text-green-500">{{ useCookie("username").value }}</span
          >!
        </h2>
      </div>
      <div class="col-md-4">
        <!-- Form Kode Kelas -->
        <div class="p-4">
          <h5 class="text-xl font-semibold text-green-600 dark:text-green-500 mb-3">Gabung Kelas</h5>
          <form @submit.prevent="joinClass" class="w-full max-w-md">
            <div class="flex dark:shadow-green-300 shadow-green-300 shadow dark:shadow-lg">
              <input
                type="text"
                v-model="classCode"
                class="form-input flex-1 border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-400 rounded-l-md ps-3 focus:ring-green-500 focus:border-green-500"
                placeholder="Masukkan kode kelas"
                required />
              <button
                type="submit"
                class="bg-green-600 text-white px-4 py-2 rounded-r-md hover:bg-green-700">
                Gabung
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Daftar Kelas -->
    <div class="row mb-5 p-4">
      <div class="col-12">
        <h4 class="text-xl font-semibold text-green-600 dark:text-green-500 mb-3">Kelasku</h4>
        <div v-if="enrolledClasses.length === 0" class="text-gray-500 text-sm mt-4">
          Kamu belum terdaftar di kelas manapun. Dapatkan kode kelas dari gurumu!
        </div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="(kelas, index) in enrolledClasses"
            :key="index"
            class="bg-white dark:bg-gray-900 border rounded-lg p-4 shadow-md shadow-green-300 hover:shadow-lg hover:shadow-green-300 relative">
              <button
                @click="outClass(kelas.code)"
                class="absolute top-2 right-2 bg-red-600 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-700"
                title="Keluar Kelas">
                <Icon name="ri:logout-box-line" class="w-4 h-4" />
              </button>
              <h5 class="text-lg font-semibold text-gray-800 dark:text-gray-200">{{ kelas.name }}</h5>
              <p class="text-sm text-green-600 mb-4">Bareng {{ kelas.teacher }}</p>
              <NuxtLink
                :to="'/student/course/' + kelas.id"
                class="btn bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700">
                <Icon name="ic:outline-log-in" class="w-4 h-4 me-2" />
                Masuk Kelas
              </NuxtLink>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const config = useRuntimeConfig();
const swal = useSwal();
const toast = useToast();
const token = useCookie("access_token").value;
const enrolledClasses = ref([]);

const classCode = ref("");

const fetchCoursesData = async () => {
  const { data, error } = await useAsyncData("my-courses", () =>
    $fetch(`${config.public.backend}/api/courses/student`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
  );

  if (error.value) {
    console.error("Gagal mengambil kelas:", error.value);
  } else {
    enrolledClasses.value = data.value;
  }
};

const joinClass = async () => {
  try {
    await $fetch(`${config.public.backend}/api/courses/enroll/${classCode.value}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
    await fetchCoursesData();
    classCode.value = "";

    toast.add({title: "Berhasil bergabung dengan kelas.", color: "green"});
  } catch (err) {
    toast.add({title: "Gagal bergabung dengan kelas.", color: "red"});
  }
};

const outClass = async (code) => {
  const result = await swal.fire({
    title: "Keluar dari kelas ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Keluar",
    cancelButtonText: "Batal",
  });

  if (!result.isConfirmed) {
    return;
  }
  try {
    await $fetch(`${config.public.backend}/api/courses/out/${code}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });
    toast.add({title: "Berhasil keluar dengan kelas.", color: "green"});
    await fetchCoursesData();
    classCode.value = "";
  } catch (err) {
    toast.add({title: "Gagal keluar dengan kelas.", color: 'red'})
  }
};

await fetchCoursesData();

definePageMeta({
  middleware: "auth",
  role: "student",
});
</script>
