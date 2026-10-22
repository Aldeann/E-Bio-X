<template>
  <nav v-if="showSidebar !== false" class="bg-gradient-to-br from-brand-700 to-brand-900 text-white shadow relative z-40">
    <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center space-x-3 min-w-0">
        <button
          v-if="role && role !== 'teacher'"
          class="sm:hidden -ms-1 p-2 rounded-lg hover:bg-white/15 transition"
          aria-label="Buka menu navigasi"
          @click.stop="mobileOpen = !mobileOpen"
        >
          <Icon name="material-symbols:menu" class="w-6 h-6" />
        </button>

        <!-- Fitur guru (9 menu) diringkas jadi hamburger di kiri atas yang
             membuka kolom menu; bukan baris panjang di atas halaman. -->
        <button
          v-if="role === 'teacher'"
          class="-ms-1 p-2 rounded-lg hover:bg-white/15 transition"
          :aria-label="teacherMenuOpen ? 'Tutup menu fitur guru' : 'Buka menu fitur guru'"
          :aria-expanded="teacherMenuOpen"
          title="Menu fitur"
          @click.stop="teacherMenuOpen = !teacherMenuOpen"
        >
          <Icon
            :name="teacherMenuOpen ? 'material-symbols:close' : 'material-symbols:menu'"
            class="w-6 h-6"
          />
        </button>

        <button
          v-if="!['/', '/student', '/teacher', '/admin'].includes($route.path)"
          class="hidden sm:flex items-center text-white dark:text-gray-100 rounded-full transition duration-200 transform hover:scale-110 h-5"
          @click="$router.back()"
        >
          <Icon name="material-symbols:arrow-back-ios-new" class="w-4 h-4" />
        </button>

        <nav
          v-if="role && role !== 'teacher'"
          class="hidden sm:flex items-center gap-1 text-sm font-medium"
        >
          <NuxtLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="px-3 py-1.5 rounded-lg transition flex items-center gap-1"
            :class="isActive(link) ? 'bg-white/20' : 'hover:bg-white/15'"
          >
            <Icon :name="link.icon" class="w-4 h-4" />
            {{ link.label }}
          </NuxtLink>
        </nav>
      </div>

      <div v-if="username" class="relative flex items-center space-x-2">
          <NotificationBell v-if="role" />
          <span class="font-medium text-white dark:text-gray-100 hidden min-[380px]:inline truncate max-w-[120px]">{{ username }}</span>
          <button @click.stop="toggleDropdown" class="focus:outline-none p-0.5" aria-label="Menu akun">
            <div
              class="w-7 h-7 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center mx-auto border-2 border-brand-200 dark:border-brand-400"
            >
              <UAvatar :alt="username" size="64" class="text-gray-400 dark:text-gray-300" />
            </div>
          </button>

        <div
          v-if="dropdownOpen"
          ref="dropdown"
          @click.stop
          class="absolute right-0 top-full mt-2 w-40 bg-surface text-black dark:text-gray-100 rounded-md shadow-lg py-2 z-50"
        >
          <NuxtLink
            to="/account"
            class="block px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            Akun
          </NuxtLink>
          <button
            @click="handleLogout"
            class="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            Logout
          </button>
        </div>
        <ToggleDark />
      </div>

    </div>

    <!-- Kolom menu fitur guru (dibuka dari hamburger di kiri atas) -->
    <div
      v-if="teacherMenuOpen && role === 'teacher'"
      ref="teacherMenu"
      @click.stop
      class="absolute left-0 top-full mt-1 w-64 max-w-[85vw] max-h-[80vh] overflow-y-auto bg-surface text-black dark:text-gray-100 rounded-md shadow-lg py-2 z-50"
    >
      <p class="px-4 pb-1 pt-1 text-[11px] uppercase tracking-wide text-gray-400 font-semibold">
        Fitur Guru
      </p>
      <NuxtLink
        v-for="link in navLinks"
        :key="link.to"
        :to="link.to"
        class="flex items-start gap-3 px-4 py-2.5 transition"
        :class="isActive(link)
          ? 'bg-guru-50 dark:bg-guru-900/40 text-guru-700 dark:text-guru-300'
          : 'hover:bg-gray-100 dark:hover:bg-gray-700'"
        @click="teacherMenuOpen = false"
      >
        <Icon :name="link.icon" class="w-5 h-5 shrink-0 mt-0.5" />
        <span class="min-w-0">
          <span class="block text-sm font-medium truncate">{{ link.label }}</span>
          <span v-if="link.desc" class="block text-[11px] text-gray-400 truncate">{{ link.desc }}</span>
        </span>
      </NuxtLink>
    </div>

    <!-- Mobile drawer navigation -->
    <div v-if="mobileOpen" class="fixed inset-0 z-[60] sm:hidden">
      <div class="absolute inset-0 bg-black/50" @click="mobileOpen = false"></div>
      <div class="absolute top-0 left-0 h-full w-72 max-w-[85vw] overflow-y-auto bg-gradient-to-b from-brand-700 to-brand-900 shadow-xl">
        <div class="flex items-center justify-between px-4 py-3 border-b border-white/20">
          <span class="font-semibold flex items-center gap-2">
            <Icon name="mdi:leaf" class="w-5 h-5" /> E-Bio X
          </span>
          <button
            class="p-2 -me-2 rounded-lg hover:bg-white/15 transition"
            aria-label="Tutup menu"
            @click="mobileOpen = false"
          >
            <Icon name="material-symbols:close" class="w-6 h-6" />
          </button>
        </div>
        <ul class="p-3 space-y-1 text-sm font-medium">
          <li v-for="link in navLinks" :key="link.to">
            <NuxtLink
              :to="link.to"
              class="flex items-center gap-3 px-3 py-3 rounded-lg transition"
              :class="isActive(link) ? 'bg-white/25' : 'hover:bg-white/15'"
              @click="mobileOpen = false"
            >
              <Icon :name="link.icon" class="w-5 h-5 shrink-0" />
              {{ link.label }}
            </NuxtLink>
          </li>
        </ul>
        <hr class="border-white/20 mx-3 my-2">
        <ul class="p-3 pt-1 space-y-1 text-sm font-medium">
          <li>
            <NuxtLink
              to="/account"
              class="flex items-center gap-3 px-3 py-3 rounded-lg hover:bg-white/15 transition"
              @click="mobileOpen = false"
            >
              <Icon name="mdi:cog" class="w-5 h-5 shrink-0" />
              Akun
            </NuxtLink>
          </li>
          <li>
            <button
              class="w-full flex items-center gap-3 px-3 py-3 rounded-lg hover:bg-red-500/80 transition text-left"
              @click="handleLogout"
            >
              <Icon name="ic:baseline-log-out" class="w-5 h-5 shrink-0" />
              Logout
            </button>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script setup>
import Cookies from "js-cookie";
import { useCookie } from "#app";
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { useRouter } from "vue-router";
import { useSwal } from "~/utils/swal";

const props = defineProps({
  showSidebar: { type: Boolean, default: true },
});

const router = useRouter();
const swal = useSwal();

const usernameCookie = useCookie("username");
const username = ref(usernameCookie || "E-Bio X");

const roleCookie = useCookie("role");
const role = computed(() => roleCookie.value || null);
const materialsLink = computed(() => {
  if (role.value === "teacher") return "/teacher/materials";
  if (role.value === "student") return "/student/materials";
  if (role.value === "admin") return "/admin/materials";
  return "/";
});

const quizzesLink = computed(() => {
  if (role.value === "teacher") return "/teacher/quizzes";
  if (role.value === "student") return "/student/quizzes";
  return "/";
});

const forumLink = computed(() => {
  if (role.value === "teacher") return "/teacher/forum";
  if (role.value === "student") return "/student/forum";
  if (role.value === "admin") return "/teacher/forum";
  return "/";
});

const navLinks = computed(() => {
  if (!role.value) return [];
  const links = [];
  if (role.value === "student") {
    links.push({ to: "/student/panduan", icon: "mdi:book-open-page-variant-outline", label: "Petunjuk Penggunaan", desc: "Panduan memakai E-Bio X" });
    links.push({ to: "/student/dashboard", icon: "material-symbols:dashboard", label: "Dashboard", desc: "Ringkasan belajar kamu" });
  }
  if (role.value === "teacher") {
    links.push({ to: "/teacher", icon: "material-symbols:dashboard", label: "Dasbor", desc: "Ringkasan & pintasan fitur" });
    links.push({ to: "/teacher/analytics", icon: "material-symbols:monitoring", label: "Analitik", desc: "Progres, penguasaan & topik" });
    links.push({ to: "/teacher/analytics/ml", icon: "material-symbols:psychology", label: "ML Insights", desc: "Profil belajar & rekomendasi" });
    links.push({ to: "/teacher/analytics/impact", icon: "material-symbols:ads-click", label: "Dampak Rekomendasi", desc: "CTR, funnel & perbaikan latihan" });
  }
  links.push({ to: materialsLink.value, icon: "material-symbols:menu-book", label: "Materi", desc: "Bahan ajar & bagian materi" });
  links.push({ to: quizzesLink.value, icon: "material-symbols:quiz", label: "Kuis", desc: "Buat & pantau kuis" });
  if (role.value === "teacher") {
    links.push({ to: "/teacher/question-bank", icon: "material-symbols:database", label: "Bank Soal", desc: "Soal siap dipakai ulang" });
    links.push({ to: "/teacher/practice", icon: "material-symbols:fitness-center", label: "Latihan Bagian", desc: "Soal latihan tiap bagian" });
    links.push({ to: "/teacher/difficulty", icon: "material-symbols:bar-chart", label: "Analisis Tingkat", desc: "Kesulitan soal dari data siswa" });
  }
  links.push({ to: forumLink.value, icon: "mdi:forum-outline", label: "Forum", desc: "Diskusi kelas" });
  if (role.value === "teacher") {
    links.push({ to: "/teacher/quiz/explanations", icon: "material-symbols:lightbulb", label: "Pembahasan AI", desc: "Draf & persetujuan pembahasan" });
  }
  return links;
});

// Tandai menu aktif, termasuk saat berada di sub-halaman (mis. /teacher/quizzes/12
// tetap menyorot "Kuis"). Dasbor /teacher hanya aktif saat tepat di halaman itu,
// supaya tidak ikut menyorot semua halaman guru.
const isActive = (link) => {
  const path = router.currentRoute.value.path;
  if (path === link.to) return true;
  if (link.to === "/teacher") return false;
  return path.startsWith(link.to + "/");
};

const mobileOpen = ref(false);
const dropdownOpen = ref(false);
const dropdown = ref(null);
const teacherMenuOpen = ref(false);
const teacherMenu = ref(null);

watch(usernameCookie, (newVal) => {
  username.value = newVal;
});

watch(
  () => router.currentRoute.value.path,
  () => {
    dropdownOpen.value = false;
    mobileOpen.value = false;
    teacherMenuOpen.value = false;
  }
);

const toggleDropdown = () => {
  dropdownOpen.value = !dropdownOpen.value;
};

const handleClickOutside = (event) => {
  if (dropdownOpen.value && dropdown.value && !dropdown.value.contains(event.target)) {
    dropdownOpen.value = false;
  }
  if (teacherMenuOpen.value && teacherMenu.value && !teacherMenu.value.contains(event.target)) {
    teacherMenuOpen.value = false;
  }
};

onMounted(() => {
  window.addEventListener("click", handleClickOutside);
});

onBeforeUnmount(() => {
  window.removeEventListener("click", handleClickOutside);
});

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
