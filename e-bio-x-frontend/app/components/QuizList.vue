<template>
  <div
    class="p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <h2 class="text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
      <Icon name="hugeicons:quiz-04" class="text-green-500" /> Kuis
    </h2>

    <div class="my-3">
      <div v-if="loading" class="space-y-4">
        <div class="border rounded-xl p-4 shadow bg-white dark:bg-gray-900 animate-pulse">
          <div class="flex items-center justify-between mb-3">
            <div class="space-y-2">
              <div class="h-5 bg-green-200 rounded w-48"></div>
              <div class="h-3 bg-green-200 rounded w-32"></div>
              <div class="h-3 bg-green-200 rounded w-40"></div>
            </div>
            <div class="flex flex-col md:flex-row gap-2">
              <div class="h-8 w-20 bg-green-200 rounded"></div>
              <div class="h-8 w-20 bg-green-200 rounded"></div>
              <div class="h-8 w-20 bg-green-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="error" class="text-red-500">{{ error }}</div>
      <div v-else>
        <div v-if="quizzes.length === 0" class="text-gray-500">Belum ada kuis untuk kelas ini.</div>

        <div v-else class="space-y-4">
          <div
            v-for="quiz in quizzes"
            :key="quiz.quiz_id"
            class="rounded-xl p-4 shadow-md dark:shadow-green-200 bg-white dark:bg-gray-900 hover:shadow-lg transition">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-xl font-semibold text-gray-800 dark:text-white">
                  {{ quiz.title }}
                </h3>
                <p class="text-sm text-gray-500">
                  {{ formatDate(quiz.created_at) }}
                </p>
                <p class="text-sm text-gray-500">{{ quiz.questions }} soal</p>
                <button
                  v-if="role == 'teacher'"
                  @click="toggleActivateQuizz(quiz.quiz_id, quiz.is_closed)"
                  class="text-sm mt-1 px-3 py-1 rounded font-semibold transition border focus:outline-none"
                  :class="
                    quiz.is_closed
                      ? 'bg-red-100 text-red-600 border-red-300 hover:bg-red-200'
                      : 'bg-green-100 text-green-600 border-green-300 hover:bg-green-200'
                  ">
                  {{ quiz.is_closed ? "Status: Ditutup" : "Status: Terbuka" }}
                </button>

                <p
                  v-else
                  class="text-sm mt-1"
                  :class="quiz.is_closed ? 'text-red-500' : 'text-green-600'">
                  {{ quiz.is_closed ? "Ditutup" : "Terbuka" }}
                </p>
              </div>

              <!-- Action menu -->
              <div class="flex flex-wrap md:flex-nowrap items-center gap-3">
                <div v-if="role === 'teacher'" class="flex flex-col md:flex-row gap-2">
                  <NuxtLink
                    :to="`/teacher/quiz/${quiz.quiz_id}/analysis`"
                    class="bg-green-600 text-white px-3 py-1.5 text-sm rounded hover:bg-green-700 flex items-center gap-1">
                    <Icon name="material-symbols:bar-chart-4-bars" />
                    Analisis
                  </NuxtLink>

                  <NuxtLink
                    :to="`/teacher/quiz/${quiz.quiz_id}`"
                    class="bg-yellow-400 text-white px-3 py-1.5 text-sm rounded hover:bg-yellow-500 flex items-center gap-1">
                    <Icon name="material-symbols:edit-square" />
                    Edit
                  </NuxtLink>

                  <button
                    @click="deleteQuiz(quiz.quiz_id)"
                    class="bg-red-600 text-white px-3 py-1.5 text-sm rounded hover:bg-red-700 flex items-center gap-1">
                    <Icon name="material-symbols:delete-rounded" />
                    Hapus
                  </button>
                </div>

                <button
                  v-else-if="role === 'student' && !quiz.is_closed && !quiz.is_submited"
                  @click="startQuiz(quiz.quiz_id)"
                  class="bg-green-600 text-white px-3 py-1.5 text-sm rounded hover:bg-green-700 flex items-center gap-1">
                  <Icon name="mdi:play-circle-outline" />
                  Kerjakan
                </button>

                <div
                  v-else-if="role === 'student' && quiz.is_submited"
                  class="flex flex-col md:flex-row gap-2 py-2 rounded-lg bg-green-50 dark:bg-green-900 text-green-700 dark:text-green-200 border border-green-200 dark:border-green-700 transition-colors">
                  <div class="flex items-center gap-2 px-4">
                    <Icon name="mdi:star-outline" class="w-5 h-5" />
                    <div>
                      <p class="text-xs text-gray-500 dark:text-gray-400">Nilai</p>
                      <p class="font-semibold text-base">
                        {{ quiz.score !== undefined && quiz.score !== null ? quiz.score : "-" }}
                      </p>
                    </div>
                  </div>
                  <div class="flex items-center gap-2 px-4">
                    <Icon name="mdi:timer-outline" class="w-5 h-5" />
                    <p class="font-semibold text-base">
                      {{ quiz.work_time ? quiz.work_time : "-" }}
                    </p>
                  </div>
                </div>

                <div
                  v-else-if="role === 'student' && quiz.is_closed"
                  class="bg-gray-200 px-3 py-1.5 text-sm rounded flex items-center gap-1">
                  <Icon name="material-symbols:cancel-rounded" />
                  Kuis ditutup
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useSwal } from "~/utils/swal";

const router = useRouter();
const token = useCookie("access_token").value;
const role = useCookie("role").value;
const swal = useSwal();
const toast = useToast();

const props = defineProps({
  courseId: {
    type: Number,
    required: true,
  },
});

const quizzes = ref([]);
const loading = ref(true);
const error = ref(null);

const fetchQuizzes = async () => {
  loading.value = true;
  error.value = null;
  try {
    const res = await $fetch(
      `${useRuntimeConfig().public.backend}/api/course/quiz/${props.courseId}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    quizzes.value = res.quizzes;
  } catch (err) {
    console.error(err);
    error.value = "Gagal memuat data kuis.";
  
    toast.add({title: 'Gagal memuat data kuis.', color: 'red'})
  } finally {
    loading.value = false;
  }
};

const toggleActivateQuizz = async (quizId, isClosed) => {
  const result = await swal.fire({
    title: isClosed ? "Buka Kuis" : "Tutup Kuis",
    text: `Apakah Anda yakin ingin ${isClosed ? "membuka" : "menutup"} kuis ini?`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: isClosed ? "Ya, buka!" : "Ya, tutup!",
    cancelButtonText: "Batal",
  });

  if (result.isConfirmed) {
    try {
      await $fetch(`${useRuntimeConfig().public.backend}/api/quiz/${quizId}`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      toast.add({title: `Kuis telah ${isClosed ? "dibuka" : "ditutup"}.`, color: 'green'})
      fetchQuizzes();
    } catch (err) {
      toast.add({title: `Kuis gagal ${isClosed ? "dibuka" : "ditutup"}.`, color: 'red'})
    }
  }
};

const deleteQuiz = async (quizId) => {
  const result = await swal.fire({
    title: "Hapus Kuis",
    text: "Apakah Anda yakin ingin menghapus kuis ini?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Ya, hapus!",
    cancelButtonText: "Batal",
  });

  if (result.isConfirmed) {
    try {
      await $fetch(`${useRuntimeConfig().public.backend}/api/quiz/${quizId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      swal.fire("Terhapus!", "Kuis telah dihapus.", "success");
      fetchQuizzes();
    } catch (err) {
      console.error(err);
      swal.fire("Error", "Gagal menghapus kuis.", "error");
    }
  }
};

function startQuiz(quizId) {
  swal
    .fire({
      title: "Mulai Kuis?",
      text: "Timer akan langsung berjalan setelah kamu mulai.",
      icon: "warning",
    })
    .then((result) => {
      if (result.isConfirmed) {
        localStorage.setItem("course_id", props.courseId);
        router.push(`/student/quiz/${quizId}`);
      }
    });
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleString("id-ID");
};

fetchQuizzes();
</script>
