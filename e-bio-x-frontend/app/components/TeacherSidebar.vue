<template>
  <button
    v-if="!isSidebarOpen"
    @click="toggleSidebar"
    type="button"
    class="fixed top-2 left-2 z-30 items-center p-2 text-sm text-white bg-green-600 dark:bg-green-700 rounded-lg sm:hidden hover:bg-green-500 focus:outline-none focus:ring-2 focus:ring-green-500">
    <span class="sr-only">Buka sidebar guru</span>
    <Icon name="material-symbols:menu-rounded" class="w-6 h-6" />
  </button>

  <div
    v-if="isSidebarOpen"
    @click="toggleSidebar"
    class="fixed inset-0 bg-black bg-opacity-50 z-30 sm:hidden"></div>

  <aside
    id="teacher-sidebar"
    ref="sidebar"
    :class="[
      'fixed top-0 left-0 z-40 w-64 h-screen transition-transform text-white',
      isSidebarOpen ? 'translate-x-0' : '-translate-x-full',
      'sm:translate-x-0',
    ]"
    aria-label="Sidebar guru">
    <div class="h-full px-3 py-4 overflow-y-auto bg-gradient-to-b from-green-600 to-emerald-700 dark:from-green-700 dark:to-emerald-800 flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2 px-1">
          <Icon name="mdi:leaf" class="w-5 h-5" />
          <span class="font-semibold">E-Bio X - Guru</span>
        </div>
        <button
          class="p-1.5 rounded-lg hover:bg-white/15 sm:hidden"
          aria-label="Tutup sidebar"
          @click="toggleSidebar">
          <Icon name="material-symbols:close" class="w-5 h-5" />
        </button>
      </div>

      <nav class="flex-1">
        <ul class="space-y-1 font-medium">
          <li v-for="item in menu" :key="item.to">
            <NuxtLink
              :to="item.to"
              :class="[
                'flex items-center gap-2 p-2 rounded-lg group transition',
                isActive(item.to) ? 'bg-white/25' : 'hover:bg-white/15',
              ]"
              @click="isSidebarOpen = false">
              <Icon :name="item.icon" class="w-5 h-5 shrink-0" />
              <span class="text-sm">{{ item.label }}</span>
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <div class="mt-3 space-y-1">
        <ToggleDark />
        <NuxtLink
          to="/account"
          :class="[
            'flex items-center gap-2 p-2 rounded-lg group',
            route.path === '/account' ? 'bg-white/25' : 'hover:bg-white/15',
          ]">
          <Icon name="mdi:cog" class="w-5 h-5 shrink-0" />
          <span class="text-sm">Akun</span>
        </NuxtLink>
        <button
          @click="handleLogout"
          class="flex w-full items-center gap-2 p-2 rounded-lg group hover:bg-red-500/90 transition text-left">
          <Icon name="ic:baseline-log-out" class="w-5 h-5 shrink-0" />
          <span class="text-sm">Logout</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useSwal } from "~/utils/swal";
import Cookies from "js-cookie";

const isSidebarOpen = ref(false);
const route = useRoute();
const router = useRouter();
const swal = useSwal();

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

const menu = [
  { to: "/teacher", icon: "material-symbols:dashboard", label: "Dasbor" },
  { to: "/teacher/analytics", icon: "material-symbols:monitoring", label: "Analitik" },
  { to: "/teacher/analytics/ml", icon: "material-symbols:psychology", label: "ML Insights" },
  // Disembunyikan untuk demo (di luar cakupan proposal):
  // { to: "/teacher/analytics/impact", icon: "material-symbols:ads-click", label: "Dampak Rekomendasi" },
  { to: "/teacher/materials", icon: "material-symbols:menu-book", label: "Materi" },
  { to: "/teacher/quizzes", icon: "material-symbols:quiz", label: "Kuis" },
  { to: "/teacher/question-bank", icon: "material-symbols:database", label: "Bank Soal" },
  { to: "/teacher/practice", icon: "material-symbols:fitness_center", label: "Latihan Bagian" },
  // Disembunyikan untuk demo (di luar cakupan proposal):
  // { to: "/teacher/difficulty", icon: "material-symbols:bar-chart", label: "Analisis Tingkat" },
  { to: "/teacher/forum", icon: "mdi:forum-outline", label: "Forum" },
  { to: "/teacher/quiz/explanations", icon: "material-symbols:lightbulb", label: "Pembahasan AI" },
  { to: "/teacher/panduan", icon: "mdi:book-open-page-variant-outline", label: "Petunjuk Penggunaan" },
];

const isActive = (to) => {
  if (route.path === to) return true;
  if (to === "/teacher") return false;
  return route.path.startsWith(to + "/");
};

const handleLogout = async () => {
  const result = await swal.fire({
    title: "Yakin mau keluar?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Keluar",
    cancelButtonText: "Batal",
  });
  if (result.isConfirmed) {
    Cookies.remove("access_token");
    Cookies.remove("email");
    Cookies.remove("username");
    Cookies.remove("role");
    Cookies.remove("has_password");
    Cookies.remove("profile_pic");
    router.replace("/");
  }
};
</script>
