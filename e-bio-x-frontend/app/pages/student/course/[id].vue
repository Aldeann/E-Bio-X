<template>
  <div class="container py-4">
    <h1 class="text-3xl font-semibold text-green-500">Kelas {{ course.name }}</h1>
    <span class="text-lg text-gray-700 dark:text-gray-200">Bareng {{ course.teacher }}</span>

    <div class="flex overflow-x-auto mt-4 space-x-2 pb-2">
      <button
        @click="activeTab = 'materi'"
        :class="[
          'flex items-center gap-1 px-3 py-2 border rounded-lg text-sm font-medium whitespace-nowrap',
          activeTab === 'materi'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="simple-icons:bookstack" />
        Materi
      </button>
      <button
        @click="activeTab = 'siswa'"
        :class="[
          'flex items-center gap-1 px-3 py-2 border rounded-lg text-sm font-medium whitespace-nowrap',
          activeTab === 'siswa'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="arcticons:classchartsstudents" />
        Siswa
      </button>
      <button
        @click="activeTab = 'kuis'"
        :class="[
          'flex items-center gap-1 px-3 py-2 border rounded-lg text-sm font-medium whitespace-nowrap',
          activeTab === 'kuis'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="hugeicons:quiz-04" />
        Kuis
      </button>
    </div>

    <div class="mb-3">
      <MaterialList v-if="activeTab === 'materi'" :courseId="courseId"/>
      <QuizList v-if="activeTab === 'kuis'" :courseId="Number(courseId)"/>
      <StudentList v-if="activeTab === 'siswa'" :students="course.students" :courseId="Number(courseId)"/>
    </div>
  </div>
</template>

<script setup>
import MaterialList from "~/components/MaterialList.vue";

const route = useRoute();
const courseId = route.params.id;

const activeTab = ref("materi");
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const course = ref([]);

const fetchData = async () => {
  try {
    const response = await $fetch(`${config.public.backend}/api/courses/${courseId}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    course.value = response;
  } catch (error) {
    console.error("Gagal mengambil kelas:", error);
  }
};

onMounted(() => {
  fetchData();
});
</script>
