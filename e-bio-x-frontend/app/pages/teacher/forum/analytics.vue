<template>
  <div class="container mx-auto px-4 py-6">
    <h1 class="text-3xl font-bold text-green-500 mb-6 flex items-center gap-2">
      <Icon name="mdi:chart-box-outline" /> Analitik Forum
    </h1>

    <div v-if="loading" class="animate-pulse space-y-3">
      <div v-for="i in 3" :key="i" class="h-24 bg-green-200 dark:bg-gray-700 rounded-xl"></div>
    </div>

    <div v-else class="space-y-6">
      <!-- KPI cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
          <p class="text-2xl font-bold text-green-500">{{ data.forums_count }}</p>
          <p class="text-xs text-gray-500">Total Forum</p>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
          <p class="text-2xl font-bold text-sky-500">{{ data.questions }}</p>
          <p class="text-xs text-gray-500">Pertanyaan</p>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
          <p class="text-2xl font-bold text-purple-500">{{ data.replies }}</p>
          <p class="text-xs text-gray-500">Balasan</p>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
          <p class="text-2xl font-bold text-amber-500">{{ data.participants }}</p>
          <p class="text-xs text-gray-500">Peserta Aktif</p>
        </div>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
          <p class="text-lg font-bold text-green-500">{{ data.active_forums }}</p>
          <p class="text-xs text-gray-500">Forum Aktif</p>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
          <p class="text-lg font-bold text-red-500">{{ data.closed_forums }}</p>
          <p class="text-xs text-gray-500">Forum Ditutup</p>
        </div>
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm">
          <p class="text-lg font-bold text-sky-500">{{ data.unanswered_questions }}</p>
          <p class="text-xs text-gray-500">Belum Terjawab</p>
        </div>
      </div>

      <!-- most discussed topics -->
      <section>
        <h2 class="font-semibold text-green-700 dark:text-green-300 mb-3 flex items-center gap-2">
          <Icon name="mdi:tag-multiple-outline" /> Topik Paling Dibahas
        </h2>
        <div v-if="!data.most_discussed_topics?.length" class="text-gray-500 text-sm">Belum ada data topik.</div>
        <div v-else class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 p-4 shadow-sm space-y-2">
          <div v-for="t in data.most_discussed_topics" :key="t.topic" class="flex items-center gap-3">
            <span class="flex-1 text-sm font-medium text-gray-700 dark:text-gray-200">{{ t.topic }}</span>
            <div class="flex-1 h-2 rounded-full bg-green-100 dark:bg-gray-700 overflow-hidden">
              <div class="h-full rounded-full bg-green-500 transition-all"
                :style="{ width: pct(t.count) }"></div>
            </div>
            <span class="text-sm text-gray-500 w-8 text-right">{{ t.count }}</span>
          </div>
        </div>
      </section>

      <!-- per-forum table -->
      <section>
        <h2 class="font-semibold text-green-700 dark:text-green-300 mb-3 flex items-center gap-2">
          <Icon name="mdi:table-outline" /> Detail per Forum
        </h2>
        <div class="bg-white dark:bg-gray-900 rounded-xl border dark:border-gray-700 overflow-hidden shadow-sm">
          <table class="w-full text-sm">
            <thead class="bg-green-50 dark:bg-gray-800 text-left text-gray-600 dark:text-gray-300">
              <tr>
                <th class="px-4 py-2">Forum</th>
                <th class="px-4 py-2">Tipe</th>
                <th class="px-4 py-2 text-center">Status</th>
                <th class="px-4 py-2 text-center">Pertanyaan</th>
                <th class="px-4 py-2 text-center">Balasan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in data.forums" :key="f.id" class="border-t border-gray-100 dark:border-gray-800">
                <td class="px-4 py-2">
                  <NuxtLink :to="`/teacher/forum/${f.id}`" class="text-green-600 dark:text-green-400 hover:underline font-medium">{{ f.title }}</NuxtLink>
                </td>
                <td class="px-4 py-2 text-gray-500">{{ f.type }}</td>
                <td class="px-4 py-2 text-center">
                  <span class="px-2 py-0.5 rounded-full text-xs font-semibold uppercase" :class="statusClass(f.status)">{{ f.status }}</span>
                </td>
                <td class="px-4 py-2 text-center">{{ f.questions }}</td>
                <td class="px-4 py-2 text-center">{{ f.replies }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
definePageMeta({ middleware: "auth", role: "teacher" });

const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const toast = useToast();

const data = ref({});
const loading = ref(true);

const fetchData = async () => {
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/teacher/forum/analytics`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    data.value = res;
  } catch (err) {
    console.error(err);
    toast.add({ title: "Gagal memuat analitik forum.", color: "red" });
  } finally {
    loading.value = false;
  }
};

const pct = (count) => {
  const max = Math.max(...(data.value.most_discussed_topics || [{ count: 1 }]).map((t) => t.count));
  return `${(count / max) * 100}%`;
};

const statusClass = (s) => ({
  ACTIVE: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200",
  CLOSED: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-200",
  DRAFT: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
  SCHEDULED: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200",
  ARCHIVED: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
}[s] || "bg-gray-100 text-gray-600");

fetchData();
</script>