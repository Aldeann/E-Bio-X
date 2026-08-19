<template>
  <div v-if="result" class="space-y-5">
    <div
      class="rounded-2xl shadow-lg p-8 text-center text-white"
      :class="result.passed ? 'bg-gradient-to-br from-green-500 to-emerald-600' : 'bg-gradient-to-br from-red-400 to-red-600'"
    >
      <Icon
        :name="result.passed ? 'material-symbols:celebration' : 'material-symbols:sentiment-dissatisfied'"
        class="w-16 h-16 mx-auto mb-2"
      />
      <h3 class="text-2xl font-bold">{{ result.passed ? "Selamat, Anda Lulus!" : "Belum Lulus" }}</h3>
      <p class="mt-1 opacity-90">{{ result.title }}</p>

      <div class="mt-4 inline-flex items-center gap-3 bg-white/20 rounded-2xl px-6 py-4">
        <div>
          <p class="text-4xl font-extrabold">{{ result.percentage }}%</p>
          <p class="text-xs uppercase tracking-wide opacity-80">Nilai Akhir</p>
        </div>
        <div class="w-px h-12 bg-white/40"></div>
        <div>
          <p class="text-xl font-semibold">{{ result.score }} poin</p>
          <p class="text-xs uppercase tracking-wide opacity-80">Nilai Lulus {{ result.passing_grade }}%</p>
        </div>
      </div>

      <div class="mt-5 grid grid-cols-3 gap-3 max-w-md mx-auto">
        <div class="bg-green-200/30 rounded-xl py-3">
          <p class="text-2xl font-bold">{{ result.correct_count }}</p>
          <p class="text-xs opacity-80">Benar</p>
        </div>
        <div class="bg-red-200/30 rounded-xl py-3">
          <p class="text-2xl font-bold">{{ result.wrong_count }}</p>
          <p class="text-xs opacity-80">Salah</p>
        </div>
        <div class="bg-gray-200/30 rounded-xl py-3">
          <p class="text-2xl font-bold">{{ result.unanswered_count }}</p>
          <p class="text-xs opacity-80">Kosong</p>
        </div>
      </div>
    </div>

    <div v-if="result.questions && result.questions.length" class="space-y-4">
      <QuizResultDetail :questions="result.questions" :show-explanation="result.show_explanation" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  result: { type: Object, required: true },
});
</script>