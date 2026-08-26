<template>
  <div class="container mx-auto px-3 sm:px-4 py-4 sm:py-6">
    <h1 class="text-2xl sm:text-3xl font-bold text-green-500">{{ course.name }}</h1>
    <span class="text-sm sm:text-lg text-gray-700 dark:text-gray-300">Bareng {{ course.teacher }}</span>

    <div class="flex overflow-x-auto mt-3 sm:mt-4 space-x-2 pb-2 -mx-3 px-3 sm:mx-0 sm:px-0">
      <button
        @click="activeTab = 'materi'"
        :class="[
          'flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 border rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap',
          activeTab === 'materi'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="simple-icons:bookstack" class="w-4 h-4" />
        Materi
      </button>
      <button
        @click="activeTab = 'siswa'"
        :class="[
          'flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 border rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap',
          activeTab === 'siswa'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="arcticons:classchartsstudents" class="w-4 h-4" />
        Siswa
      </button>
      <button
        @click="activeTab = 'kuis'"
        :class="[
          'flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 border rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap',
          activeTab === 'kuis'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="hugeicons:quiz-04" class="w-4 h-4" />
        Kuis
      </button>
      <button
        @click="activeTab = 'buat-kuis'"
        :class="[
          'flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 border rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap',
          activeTab === 'buat-kuis'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="fluent:quiz-new-24-filled" class="w-4 h-4" />
        Buat Kuis
      </button>
      <button
        @click="activeTab = 'forum'"
        :class="[
          'flex items-center gap-1 px-2.5 sm:px-3 py-1.5 sm:py-2 border rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap',
          activeTab === 'forum'
            ? 'bg-white dark:bg-gray-900 dark:text-green-200 text-green-600 border-green-300 shadow shadow-green-300'
            : 'bg-gray-100 text-gray-600 border-gray-200 dark:border-green-800 dark:text-green-200 dark:bg-gray-800',
        ]">
        <Icon name="mdi:forum-outline" class="w-4 h-4" />
        Forum
      </button>
    </div>

    <div class="mb-3">
      <div v-if="activeTab === 'materi'" class="mb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <span class="text-xs sm:text-sm text-gray-500">Materi yang terkait dengan kelas ini.</span>
        <NuxtLink
          :to="`/teacher/materials/create?course_id=${courseId}`"
          class="inline-flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs sm:text-sm font-semibold self-start sm:self-auto"
        >
          <Icon name="material-symbols:add" class="w-4 h-4" />
          Buat Materi
        </NuxtLink>
      </div>
      <MaterialList v-if="activeTab === 'materi'" class="mb-3" :courseId="courseId" />
      <StudentList 
        v-if="activeTab === 'siswa'" 
        class="mb-3" 
        :students="course.students" 
        :courseId="courseId"
        @studentRemoved="handleStudentRemoved"
      />
      <div
        v-if="activeTab === 'buat-kuis'"
        class="mb-3 bg-white dark:bg-gray-900 border border-green-200 dark:border-gray-700 rounded-xl shadow-md p-8 text-center">
        <Icon name="fluent:quiz-new-24-filled" class="w-12 h-12 text-green-500 mx-auto mb-3" />
        <h3 class="text-lg font-semibold text-gray-800 dark:text-white mb-1">Buat Kuis Baru</h3>
        <p class="text-sm text-gray-500 mb-4">
          Buat kuis dengan pengaturan lengkap: materi, durasi, nilai lulus, dan jumlah percobaan.
        </p>
        <NuxtLink
          to="/teacher/quizzes/create"
          class="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-sm font-semibold">
          <Icon name="material-symbols:add" class="w-5 h-5" />
          Buat Kuis
        </NuxtLink>
      </div>
      <QuizList v-if="activeTab === 'kuis'" class="mb-3" :courseId="Number(courseId)" />
      <ForumList v-if="activeTab === 'forum'" class="mb-3" :courseId="courseId" />
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