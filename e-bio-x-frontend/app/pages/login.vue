<template>
  <div class="px-4 max-w-4xl mx-auto w-full flex items-center justify-center">
    <div class="w-full max-w-md">
      <div
        class="bg-surface text-body shadow-md rounded-xl overflow-hidden">
        <div class="relative bg-brand-700 text-white text-center py-4">
          <h4 class="text-xl font-semibold">Masuk ke E-Bio X</h4>
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
                class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-slate-700 dark:text-white" />
            </div>
            <div>
              <label for="password" class="block font-medium mb-1">Kata sandi</label>
              <div class="relative">
                <input
                  :type="showPassword ? 'text' : 'password'"
                  id="password"
                  v-model="password"
                  required
                  class="w-full px-4 py-2 border border-gray-300 dark:border-slate-600 rounded focus:outline-none focus:ring-2 focus:ring-brand-500 dark:bg-slate-700 dark:text-white" />
                <Icon
                  :name="showPassword ? 'fluent:eye-20-filled' : 'fluent:eye-hide-20-filled'"
                  class="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-gray-500 h-5 w-5"
                  @click="showPassword = !showPassword" />
              </div>
            </div>
            <button
              type="submit"
              class="w-full bg-brand-700 hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 text-white font-semibold py-2 rounded transition-colors">
              Masuk
            </button>
          </form>

          <p v-if="message" class="mt-4 text-red-600 text-sm text-center">{{ message }}</p>

          <p class="mt-3 text-center text-xs leading-relaxed text-muted">
            Lupa kata sandi? Hubungi guru atau admin sekolah, ya.
          </p>

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

      <p class="mt-4 text-center text-xs leading-relaxed text-muted">
        Dikembangkan oleh
        <NuxtLink
          to="/tentang"
          class="font-medium text-body transition hover:text-brand-700 hover:underline dark:hover:text-brand-300">
          Muhammad Ghazali Alhakim
        </NuxtLink>
        <br />
        Universitas Negeri Padang &middot; v1.0.0
      </p>
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
      message.value = "Email atau kata sandi belum cocok. Coba periksa lagi, ya.";
    } else if (status === 418) {
      message.value = "Akun ini terdaftar lewat Google. Silakan masuk dengan tombol Google di bawah.";
    } else if (status >= 500) {
      message.value = "Server sedang sibuk. Coba beberapa saat lagi, ya.";
    } else {
      message.value = "Ada kendala saat masuk. Coba lagi; kalau masih gagal, hubungi guru atau admin sekolah.";
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
      message.value = "Email atau kata sandi belum cocok. Coba periksa lagi, ya.";
    } else if (status >= 500) {
      message.value = "Server sedang sibuk. Coba beberapa saat lagi, ya.";
    } else {
      message.value = "Ada kendala saat masuk. Coba lagi; kalau masih gagal, hubungi guru atau admin sekolah.";
    }
  }
};

// handle an error google login
const handleLoginError = () => {
  message.value = "Masuk dengan Google belum berhasil. Coba lagi, ya.";
  console.error("Login failed");
};
</script>
