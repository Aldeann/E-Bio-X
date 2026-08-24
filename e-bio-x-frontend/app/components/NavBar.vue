<template>
  <nav class="bg-gradient-to-br from-green-500 to-emerald-600 dark:from-green-600 dark:to-emerald-700 text-white shadow relative z-40">
    <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center space-x-3 min-w-0">
        <button
          v-if="role"
          class="sm:hidden -ms-1 p-2 rounded-lg hover:bg-white/15 transition"
          aria-label="Buka menu navigasi"
          @click.stop="mobileOpen = !mobileOpen"
        >
          <Icon name="material-symbols:menu" class="w-6 h-6" />
        </button>

        <button
          v-if="!['/', '/student', '/teacher', '/admin'].includes($route.path)"
          class="hidden sm:flex items-center text-white dark:text-gray-100 rounded-full transition duration-200 transform hover:scale-110 h-5"
          @click="$router.back()"
        >
          <Icon name="material-symbols:arrow-back-ios-new" class="w-4 h-4" />
        </button>

        <nav
          v-if="role"
          class="hidden sm:flex items-center gap-1 text-sm font-medium"
        >
          <NuxtLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="px-3 py-1.5 rounded-lg transition flex items-center gap-1"
            :class="$route.path === link.to ? 'bg-white/20' : 'hover:bg-white/15'"
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
              class="w-7 h-7 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center mx-auto border-2 border-green-800 dark:border-green-500"
            >
              <UAvatar :alt="username" size="64" class="text-gray-400 dark:text-gray-300" />
            </div>
          </button>

        <div
          v-if="dropdownOpen"
          ref="dropdown"
          @click.stop
          class="absolute right-0 top-full mt-2 w-40 bg-white dark:bg-gray-800 text-black dark:text-gray-100 rounded-md shadow-lg py-2 z-50"
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

    <!-- Mobile drawer navigation -->
    <div v-if="mobileOpen" class="fixed inset-0 z-[60] sm:hidden">
      <div class="absolute inset-0 bg-black/50" @click="mobileOpen = false"></div>
      <div class="absolute top-0 left-0 h-full w-72 max-w-[85vw] overflow-y-auto bg-gradient-to-b from-green-600 to-emerald-700 shadow-xl">
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
              :class="$route.path === link.to ? 'bg-white/25' : 'hover:bg-white/15'"
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
    links.push({ to: "/student/dashboard", icon: "material-symbols:dashboard", label: "Dashboard" });
  }
  if (role.value === "teacher") {
    links.push({ to: "/teacher/analytics", icon: "material-symbols:monitoring", label: "Analitik" });
    links.push({ to: "/teacher/analytics/ml", icon: "material-symbols:psychology", label: "ML Insights" });
  }
  links.push({ to: materialsLink.value, icon: "material-symbols:menu-book", label: "Materi" });
  links.push({ to: quizzesLink.value, icon: "material-symbols:quiz", label: "Kuis" });
  if (role.value === "teacher") {
    links.push({ to: "/teacher/question-bank", icon: "material-symbols:database", label: "Bank Soal" });
  }
  links.push({ to: forumLink.value, icon: "mdi:forum-outline", label: "Forum" });
  if (role.value === "teacher") {
    links.push({ to: "/teacher/quiz/explanations", icon: "material-symbols:lightbulb", label: "Pembahasan AI" });
  }
  return links;
});

const mobileOpen = ref(false);
const dropdownOpen = ref(false);
const dropdown = ref(null);

watch(usernameCookie, (newVal) => {
  username.value = newVal;
});

watch(
  () => router.currentRoute.value.path,
  () => {
    dropdownOpen.value = false;
    mobileOpen.value = false;
  }
);

const toggleDropdown = () => {
  dropdownOpen.value = !dropdownOpen.value;
};

const handleClickOutside = (event) => {
  if (dropdownOpen.value && dropdown.value && !dropdown.value.contains(event.target)) {
    dropdownOpen.value = false;
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
