<template>
  <div class="px-4 max-w-4xl mx-auto w-full flex items-center justify-center">
    <div class="w-full max-w-md">
      <div
        class="bg-white dark:bg-gray-800 dark:text-gray-200 shadow-md rounded-xl overflow-hidden">
        <div class="relative bg-green-600 dark:bg-green-700 text-white text-center py-4">
          <h4 class="text-xl font-semibold">Login E Bio X</h4>
          <div class="absolute top-0 right-0 pr-4 pt-5">
            <ToggleDark />
          </div>
        </div>
        <div class="p-6">
          <form @submit.prevent="handleLogin" class="space-y-4">
            <div>
              <label for="email" class="block font-medium mb-1">Email</label>
              <input
                type="email"
                id="email"
                v-model="email"
                required
                class="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500 dark:bg-gray-700" />
            </div>
            <div>
              <label for="password" class="block font-medium mb-1">Password</label>
              <div class="relative">
                <input
                  :type="showPassword ? 'text' : 'password'"
                  id="password"
                  v-model="password"
                  required
                  class="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500 dark:bg-gray-700" />
                <Icon
                  :name="showPassword ? 'fluent:eye-20-filled' : 'fluent:eye-hide-20-filled'"
                  class="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-gray-500 h-5 w-5"
                  @click="showPassword = !showPassword" />
              </div>
            </div>
            <button
              type="submit"
              class="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded">
              Login
            </button>
          </form>

          <p v-if="message" class="mt-4 text-red-600 text-sm text-center">{{ message }}</p>

          <div class="flex justify-center mt-6">
            <GoogleSignInButton
              :buttonConfig="{
                theme: isDark ? 'filled_black' : 'outline',
                size: 'large',
              }"
              @success="handleLoginSuccess"
              @error="handleLoginError" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig, useRouter } from "#app";
import { GoogleSignInButton, type CredentialResponse } from "vue3-google-signin";
import Cookies from "js-cookie";

const router = useRouter();
const config = useRuntimeConfig();

definePageMeta({
  layout: "blank",
  middleware: "guest",
});

const email = ref("");
const password = ref("");
const message = ref("");
const showPassword = ref(false);
const isDark = ref(false);

onMounted(() => {
  isDark.value = localStorage.getItem("theme") === "dark";

  window.addEventListener("storage", () => {
    isDark.value = localStorage.getItem("theme") === "dark";
  });
});

// handle normal login
const handleLogin = async () => {
  try {
    const user = (await $fetch(`${config.public.backend}/api/login`, {
      method: "POST",
      body: {
        email: email.value,
        password: password.value,
      },
    })) as any;

    Cookies.set("access_token", user.access_token, { expires: 1, path: "/" });
    Cookies.set("email", user.email, { expires: 1, path: "/" });
    Cookies.set("username", user.name, { expires: 1, path: "/" });
    Cookies.set("role", user.role, { expires: 1, path: "/" });
    Cookies.set("has_password", user.has_password, { expires: 1, path: "/" });
    Cookies.set("profile_pic", user.profile_pic, { expires: 1, path: "/" });

    router.replace(`/${user.role}`);
  } catch (error: any) {
    const status = error?.response?.status || error?.statusCode || error?.data?.statusCode;

    if (status === 401) {
      message.value = "Email atau password salah";
    } else if (status === 418) {
      message.value = "Akun terdaftar dengan google. Gunakan google untuk login.";
    } else if (status >= 500) {
      message.value = "Server sedang bermasalah. Coba lagi nanti.";
    } else {
      message.value = `Terjadi kesalahan. Silakan coba lagi.`;
    }
  }
};

// handle success google login
const handleLoginSuccess = async (response: CredentialResponse) => {
  const { credential } = response;

  if (!credential) {
    console.error("Login failed, credential not found");
    return;
  }
  try {
    const user = await $fetch(`${config.public.backend}/api/google-login`, {
      method: "POST",
      body: { token: credential },
    });

    Cookies.set("access_token", user.access_token, { expires: 1, path: "/" });
    Cookies.set("email", user.email, { expires: 1, path: "/" });
    Cookies.set("username", user.name, { expires: 1, path: "/" });
    Cookies.set("role", user.role, { expires: 1, path: "/" });
    Cookies.set("has_password", user.has_password, { expires: 1, path: "/" });
    Cookies.set("profile_pic", user.profile_pic, { expires: 1, path: "/" });

    router.replace(`/${user.role}`);
  } catch (error: any) {
    const status = error?.response?.status || error?.statusCode || error?.data?.statusCode;

    if (status === 401) {
      message.value = "Email atau password salah";
    } else if (status >= 500) {
      message.value = "Server sedang bermasalah. Coba lagi nanti.";
    } else {
      message.value = "Terjadi kesalahan. Silakan coba lagi.";
    }
  }
};

// handle an error google login
const handleLoginError = () => {
  message.value = "Login Google gagal. Silakan coba lagi.";
  console.error("Login failed");
};
</script>
