<template>
  <main class="flex-1 px-4 py-6 max-w-6xl mx-auto w-full">
    <div class="max-w-3xl mx-auto p-6">
      <div v-if="loading">
        <p class="text-center text-gray-500">Loading...</p>
      </div>
  
      <div v-else>
        <div class="flex justify-between items-center mb-4">
          <h1 class="text-2xl font-bold">{{ quiz.title }}</h1>
          <ToggleDark />
        </div>
  
        <div class="text-center mb-4 text-gray-500">Waktu: {{ timer }}</div>
  
        <div class="mb-6">
          <p class="font-semibold mb-2">{{ currentIndex + 1 }}. {{ currentQuestion.question_text }}</p>
          <div class="space-y-2">
            <label
              v-for="option in currentQuestion.options"
              :key="option.option_id"
              class="flex items-center space-x-2"
            >
              <input
                type="radio"
                :name="'question_' + currentQuestion.question_id"
                :value="option.option_id"
                v-model="answers[currentQuestion.question_id]"
                class="text-green-600 focus:ring-green-500"
                required
              />
              <span>{{ option.option_text }}</span>
            </label>
          </div>
        </div>
  
        <div class="flex flex-wrap justify-center gap-2 mb-4">
          <button
            v-for="(q, idx) in quiz.questions"
            :key="q.question_id"
            @click="goToQuestion(idx)"
            class="w-8 h-8 rounded-full border text-sm"
            :class="answers[q.question_id] ? 'bg-green-600 text-white' : 'border-gray-400 text-gray-600'"
          >
            {{ idx + 1 }}
          </button>
        </div>
  
        <div class="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 p-4 border-t flex justify-between">
          <button
            v-if="currentIndex > 0"
            @click="prevQuestion"
            class="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
          >
            Sebelumnya
          </button>
  
          <div class="flex-1"></div>
  
          <button
            v-if="currentIndex < quiz.questions.length - 1"
            @click="nextQuestion"
            class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Berikutnya
          </button>
  
          <button
            v-else
            @click="submitQuiz"
            class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Kirim Jawaban
          </button>
        </div>
      </div>
    </div>
  </main>
</template>

<script setup>
import { useSwal } from '~/utils/swal'

const route = useRoute()
const router = useRouter()
const config = useRuntimeConfig()
const token = useCookie('access_token').value
const swal = useSwal()

const quiz = ref({ questions: [] })
const answers = ref({})
const currentIndex = ref(0)
const loading = ref(true)
const timer = ref('00:00:00')
let timerInterval

const currentQuestion = computed(() => quiz.value.questions[currentIndex.value] || {})

onMounted(async () => {
  const data = await $fetch(`${config.public.backend}/api/quiz/${route.params.quizId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  quiz.value = data
  loading.value = false
  startTimer()
})

function startTimer() {
  let seconds = 0
  timerInterval = setInterval(() => {
    seconds++
    const h = String(Math.floor(seconds / 3600)).padStart(2, '0')
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0')
    const s = String(seconds % 60).padStart(2, '0')
    timer.value = `${h}:${m}:${s}`
  }, 1000)
}

function goToQuestion(index) {
  currentIndex.value = index
}

function nextQuestion() {
  if (currentIndex.value < quiz.value.questions.length - 1) currentIndex.value++
}

function prevQuestion() {
  if (currentIndex.value > 0) currentIndex.value--
}

async function submitQuiz() {
  const unanswered = quiz.value.questions.filter(q => !answers.value[q.question_id])
  if (unanswered.length > 0) {
    await swal.fire({
      icon: 'warning',
      title: 'Ada soal yang belum dijawab',
      text: 'Harap jawab semua soal sebelum mengirim.',
    })
    return
  }

  const submittedAnswers = Object.entries(answers.value).map(([question_id, option_id]) => ({
    question_id: parseInt(question_id),
    option_id: parseInt(option_id),
  }))

  try {
    const res = await $fetch(`${config.public.backend}/api/quiz/${route.params.quizId}/submit`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: { 
        work_time: timer.value,
        answers: submittedAnswers 
      },
    })

    clearInterval(timerInterval)

    await swal.fire({
      icon: 'success',
      title: 'Quiz Terkirim!',
      html: `<p><b>Nama:</b> ${res.data.student}</p><p><b>Nilai:</b> ${res.data.score}</p>`
    })

    const courseId = localStorage.getItem('course_id')
    router.replace({ path: `/student/course/${courseId}` })
  } catch (err) {
    await swal.fire({
      icon: 'error',
      title: 'Gagal kirim',
      text: err.data?.error || 'Terjadi kesalahan',
    })
  }
}

definePageMeta({
  layout: "blank",
  middleware: "auth",
});
</script>

<style scoped>
input[type='radio'] {
  accent-color: #16a34a;
}
</style>
