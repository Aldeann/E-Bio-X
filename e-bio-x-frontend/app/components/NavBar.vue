<template>
  <nav class="bg-gradient-to-br from-green-500 to-emerald-600 dark:from-green-600 dark:to-emerald-700 text-white shadow">
    <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <button
          v-if="!['/', '/student', '/teacher', '/admin'].includes($route.path)"
          class="flex items-center text-white dark:text-gray-100 rounded-full transition duration-200 transform hover:scale-110 h-5"
          @click="$router.back()"
        >
          <Icon name="material-symbols:arrow-back-ios-new" class="w-4 h-4" />
        </button>
      </div>

      <div v-if="username" class="relative flex items-center space-x-2">
          <span class="font-medium text-white dark:text-gray-100">{{ username }}</span>
          <button @click.stop="toggleDropdown" class="focus:outline-none">
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
  </nav>
</template>

<script setup>
import Cookies from "js-cookie";
import { useCookie } from "#app";
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { useRouter } from "vue-router";
import { useSwal } from "~/utils/swal";

const router = useRouter();
const swal = useSwal();

const usernameCookie = useCookie("username");
const username = ref(usernameCookie || "E-Bio X");

const dropdownOpen = ref(false);
const dropdown = ref(null);

watch(usernameCookie, (newVal) => {
  username.value = newVal;
});

watch(
  () => router.currentRoute.value.path,
  () => {
    dropdownOpen.value = false;
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
