<template>
  <div class="p-3 sm:p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <h2 class="text-lg sm:text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2 mb-3 sm:mb-4">
      <Icon name="hugeicons:quiz-04" class="text-green-500" /> Kuis
    </h2>

    <div>
      <!-- Skeleton -->
      <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <div v-for="i in 3" :key="i" class="border rounded-xl p-3 sm:p-4 shadow bg-white dark:bg-gray-900 animate-pulse">
          <div class="flex items-center justify-between mb-3">
            <div class="space-y-2 flex-1">
              <div class="h-4 bg-green-200 rounded w-3/4"></div>
              <div class="h-3 bg-green-200 rounded w-1/2"></div>
            </div>
            <div class="h-6 w-16 bg-green-200 rounded-full"></div>
          </div>
          <div class="flex flex-wrap gap-1.5 mt-3">
            <div class="h-5 w-16 bg-green-100 rounded-full"></div>
            <div class="h-5 w-20 bg-green-100 rounded-full"></div>
          </div>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>

      <!-- Empty -->
      <div v-else-if="quizzes.length === 0" class="text-center py-8">
        <Icon name="material-symbols:quiz" class="w-10 h-10 sm:w-12 sm:h-12 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
        <p class="text-sm text-gray-500 dark:text-gray-400">Belum ada kuis untuk kelas ini.</p>
      </div>

      <!-- Card Grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <div
          v-for="quiz in quizzes"
          :key="quiz.quiz_id"
          class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden flex flex-col shadow-sm hover:shadow-md transition"
        >
          <!-- Header stripe -->
          <div
            class="h-2"
            :class="quiz.is_closed ? 'bg-red-400' : 'bg-gradient-to-r from-green-500 to-emerald-500'"
          />

          <!-- Body -->
          <div class="p-3 sm:p-4 flex flex-col flex-1">
            <!-- Status + title -->
            <div class="flex items-start justify-between gap-2">
              <h3 class="font-semibold text-sm sm:text-base text-gray-800 dark:text-gray-100 line-clamp-2">
                {{ quiz.title }}
              </h3>
              <span
                class="shrink-0 text-[9px] sm:text-[10px] uppercase font-bold px-1.5 sm:px-2 py-0.5 rounded-full"
                :class="quiz.is_closed
                  ? 'bg-red-100 text-red-600'
                  : 'bg-green-100 text-green-700'"
              >
                {{ quiz.is_closed ? "Tutup" : "Buka" }}
              </span>
            </div>

            <!-- Meta -->
            <div class="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] sm:text-xs text-gray-400">
              <span class="flex items-center gap-1">
                <Icon name="material-symbols:calendar-today" class="w-3 h-3" />
                {{ formatDate(quiz.created_at) }}
              </span>
              <span class="flex items-center gap-1">
                <Icon name="material-symbols:help-outline" class="w-3 h-3" />
                {{ quiz.questions }} soal
              </span>
            </div>

            <!-- Teacher: toggle status -->
            <div v-if="role === 'teacher'" class="mt-2">
              <button
                @click="toggleActivateQuizz(quiz.quiz_id, quiz.is_closed)"
                class="text-[10px] sm:text-xs mt-1 px-2 sm:px-3 py-1 rounded-full font-semibold transition border focus:outline-none"
                :class="quiz.is_closed
                  ? 'bg-red-100 text-red-600 border-red-300 hover:bg-red-200'
                  : 'bg-green-100 text-green-600 border-green-300 hover:bg-green-200'"
              >
                {{ quiz.is_closed ? "Status: Ditutup" : "Status: Terbuka" }}
              </button>
            </div>

            <!-- Student: status -->
            <div v-else class="mt-2">
              <span
                class="text-[10px] sm:text-xs font-medium"
                :class="quiz.is_closed ? 'text-red-500' : 'text-green-600'"
              >
                {{ quiz.is_closed ? "Ditutup" : "Terbuka" }}
              </span>
            </div>

            <!-- Student: score -->
            <div
              v-if="role === 'student' && quiz.student_status === 'completed'"
              class="mt-2 flex flex-wrap items-center gap-2"
            >
              <span class="text-[10px] sm:text-xs text-gray-500">Skor terbaik:</span>
              <span class="text-xs sm:text-sm font-bold text-green-700 dark:text-green-500">
                {{ quiz.best_percentage !== null && quiz.best_percentage !== undefined ? quiz.best_percentage + "%" : "-" }}
              </span>
              <span
                class="px-1.5 sm:px-2 py-0.5 rounded-full text-[9px] sm:text-[10px] font-medium"
                :class="quiz.passed
                  ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                  : 'bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300'"
              >
                {{ quiz.passed ? "Lulus" : "Belum Lulus" }}
              </span>
            </div>

            <!-- Spacer -->
            <div class="flex-1" />

            <!-- Actions -->
            <div class="mt-3 pt-2.5 sm:pt-3 border-t border-gray-100 dark:border-gray-800">
              <!-- Teacher actions -->
              <div v-if="role === 'teacher'" class="grid grid-cols-3 gap-1.5 sm:gap-2">
                <NuxtLink
                  :to="`/teacher/quizzes/${quiz.quiz_id}/analytics`"
                  class="bg-green-600 hover:bg-green-700 text-white text-[10px] sm:text-xs px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center transition flex items-center justify-center gap-1"
                >
                  <Icon name="material-symbols:bar-chart-4-bars" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                  Analisis
                </NuxtLink>
                <NuxtLink
                  :to="`/teacher/quizzes/${quiz.quiz_id}`"
                  class="bg-amber-400 hover:bg-amber-500 text-white text-[10px] sm:text-xs px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center transition flex items-center justify-center gap-1"
                >
                  <Icon name="material-symbols:edit-square" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                  Edit
                </NuxtLink>
                <button
                  @click="deleteQuiz(quiz.quiz_id)"
                  class="bg-red-600 hover:bg-red-700 text-white text-[10px] sm:text-xs px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center transition flex items-center justify-center gap-1"
                >
                  <Icon name="material-symbols:delete-rounded" class="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                  Hapus
                </button>
              </div>

              <!-- Student: open quiz -->
              <div v-else-if="role === 'student' && !quiz.is_closed">
                <div v-if="quiz.student_status === 'completed'" class="grid grid-cols-2 gap-1.5 sm:gap-2">
                  <NuxtLink
                    :to="`/student/quizzes/${quiz.quiz_id}/result`"
                    class="bg-green-600 hover:bg-green-700 text-white text-[10px] sm:text-xs px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center transition"
                  >
                    Lihat Hasil
                  </NuxtLink>
                  <button
                    v-if="quiz.attempts_used < quiz.max_attempts"
                    @click="startQuiz(quiz.quiz_id)"
                    class="border border-green-600 text-green-700 dark:text-green-400 text-[10px] sm:text-xs px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center hover:bg-green-50 dark:hover:bg-gray-800 transition"
                  >
                    Ulangi
                  </button>
                  <span
                    v-else
                    class="border border-gray-300 dark:border-gray-600 text-gray-400 text-[10px] sm:text-xs px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg text-center"
                  >
                    Selesai
                  </span>
                </div>
                <button
                  v-else
                  @click="startQuiz(quiz.quiz_id)"
                  class="w-full bg-green-600 hover:bg-green-700 text-white text-[10px] sm:text-xs px-3 py-1.5 sm:py-2 rounded-lg text-center transition flex items-center justify-center gap-1"
                >
                  <Icon name="mdi:play-circle-outline" class="w-3.5 h-3.5" />
                  {{ quiz.student_status === 'in_progress' ? 'Lanjutkan' : 'Kerjakan' }}
                </button>
              </div>

              <!-- Student: closed -->
              <div
                v-else-if="role === 'student' && quiz.is_closed"
                class="bg-gray-100 dark:bg-gray-800 px-3 py-1.5 text-[10px] sm:text-xs text-gray-500 rounded-lg flex items-center justify-center gap-1"
              >
                <Icon name="material-symbols:cancel-rounded" class="w-3.5 h-3.5" />
                Kuis ditutup
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
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    quizzes.value = res.quizzes;
  } catch (err) {
    console.error(err);
    error.value = "Gagal memuat data kuis.";
    toast.add({ title: "Gagal memuat data kuis.", color: "red" });
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
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.add({ title: `Kuis telah ${isClosed ? "dibuka" : "ditutup"}.`, color: "green" });
      fetchQuizzes();
    } catch (err) {
      toast.add({ title: `Kuis gagal ${isClosed ? "dibuka" : "ditutup"}.`, color: "red" });
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
        headers: { Authorization: `Bearer ${token}` },
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
        router.push(`/student/quizzes/${quizId}`);
      }
    });
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleString("id-ID");
};

fetchQuizzes();
</script>
