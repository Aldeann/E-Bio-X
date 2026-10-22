<template>
  <button
    v-if="!isSidebarOpen"
    @click="toggleSidebar"
    type="button"
    class="fixed top-2 left-2 z-30 items-center p-2 text-sm text-white bg-siswa-700 rounded-lg sm:hidden hover:bg-siswa-800 focus:outline-none focus:ring-2 focus:ring-siswa-500">
    <span class="sr-only">Buka sidebar siswa</span>
    <Icon name="material-symbols:menu-rounded" class="w-6 h-6" />
  </button>

  <div
    v-if="isSidebarOpen"
    @click="toggleSidebar"
    class="fixed inset-0 bg-black bg-opacity-50 z-30 sm:hidden"></div>

  <aside
    id="student-sidebar"
    ref="sidebar"
    :class="[
      'fixed top-0 left-0 z-40 w-64 h-screen transition-transform text-white',
      isSidebarOpen ? 'translate-x-0' : '-translate-x-full',
      'sm:translate-x-0',
    ]"
    aria-label="Sidebar siswa">
    <div class="h-full px-3 py-4 overflow-y-auto bg-gradient-to-b from-siswa-700 to-siswa-900 flex flex-col">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2 px-1">
          <Icon name="mdi:leaf" class="w-5 h-5" />
          <span class="font-semibold">E-Bio X - Siswa</span>
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
                isActive(item.to) ? 'bg-white/20 ring-1 ring-inset ring-white/25' : 'hover:bg-white/10',
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
            route.path === '/account' ? 'bg-white/20 ring-1 ring-inset ring-white/25' : 'hover:bg-white/10',
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
  { to: "/student/panduan", icon: "mdi:book-open-page-variant-outline", label: "Petunjuk Penggunaan" },
  { to: "/student/dashboard", icon: "material-symbols:dashboard", label: "Dasbor" },
  { to: "/student", icon: "material-symbols:groups", label: "Kelas Saya" },
  { to: "/student/materials", icon: "material-symbols:menu-book", label: "Materi" },
  { to: "/student/quizzes", icon: "material-symbols:quiz", label: "Kuis" },
  { to: "/student/progress", icon: "material-symbols:history", label: "Riwayat Belajar" },
  { to: "/student/forum", icon: "mdi:forum-outline", label: "Forum" },
];

const isActive = (to) => {
  if (to === "/student") {
    return route.path === "/student" || route.path.startsWith("/student/course");
  }
  if (route.path === to) return true;
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
