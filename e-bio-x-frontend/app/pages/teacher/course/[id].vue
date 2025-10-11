<template>
  <div class="container mx-auto px-4 py-6">
    <h1 class="text-3xl font-bold text-green-500">{{ course.name }}</h1>
    <span class="text-lg text-gray-700 dark:text-gray-300">Bareng {{ course.teacher }}</span>

    <div class="flex overflow-x-auto mt-4 space-x-2 pb-2">
      <button
        @click="activeTab = 'materi'"
        :class="[
          'flex items-center gap-1 px-3 py-2 border rounded-lg text-sm font-medium whitespace-nowrap',
          activeTab === 'materi'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="simple-icons:bookstack" />
        Materi
      </button>
      <button
        @click="activeTab = 'upload-materi'"
        :class="[
          'flex items-center gap-1 px-3 py-2 border rounded-lg text-sm font-medium whitespace-nowrap',
          activeTab === 'upload-materi'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="material-symbols:upload-rounded" />
        Upload
      </button>
      <button
        @click="activeTab = 'siswa'"
        :class="[
          'flex items-center gap-1 px-3 py-2 border rounded-lg text-sm font-medium whitespace-nowrap',
          activeTab === 'siswa'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
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
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="hugeicons:quiz-04" />
        Kuis
      </button>
      <button
        @click="activeTab = 'buat-kuis'"
        :class="[
          'flex items-center gap-1 px-3 py-2 border rounded-lg text-sm font-medium whitespace-nowrap',
          activeTab === 'buat-kuis'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="fluent:quiz-new-24-filled" />
        Buat Kuis
      </button>
    </div>

    <div class="mb-3">
      <MaterialUpload v-if="activeTab === 'upload-materi'" class="mb-3" :courseId="courseId" />
      <MaterialList v-if="activeTab === 'materi'" class="mb-3" :courseId="courseId" />
      <StudentList 
        v-if="activeTab === 'siswa'" 
        class="mb-3" 
        :students="course.students" 
        :courseId="courseId"
        @studentRemoved="handleStudentRemoved"
      />
      <QuizCreate v-if="activeTab === 'buat-kuis'" class="mb-3" :courseId="Number(courseId)" />
      <QuizList v-if="activeTab === 'kuis'" class="mb-3" :courseId="Number(courseId)" />
    </div>
  </div>
</template>

<script setup>
const token = useCookie("access_token").value;
const route = useRoute();
const toast = useToast();
const config = useRuntimeConfig();

const courseId = route.params.id;
const activeTab = ref("materi");
const course = ref([]);

const fetchCourse = async () => {
  try {
    const response = await $fetch(`${config.public.backend}/api/courses/${courseId}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    course.value = response;
  } catch (error) {
    toast.add({title: 'Gagal mengambil data kelas.', color: 'red' });
  }
};

const handleStudentRemoved = async (studentId) => {
  if (course.value.students) {
    course.value.students = course.value.students.filter(student => student.id !== studentId);
  }
  
  await fetchCourse();
};

onMounted(() => {
  fetchCourse();
});

definePageMeta({
  middleware: "auth",
  role: "teacher",
});
</script>