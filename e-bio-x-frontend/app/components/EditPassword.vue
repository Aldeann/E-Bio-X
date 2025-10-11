<template>
  <div class="text-center">
    <client-only> 
      <button
        @click="openPasswordModal"
        :class="
          userData.has_password === 'true'
            ? 'bg-gray-400 text-white px-4 py-2 rounded-md hover:bg-gray-500'
            : 'bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700'
        ">
        {{ userData.has_password === "true" ? "Change Password" : "Set Password" }}
      </button>
    </client-only>
  </div>

  <div
    v-if="showModal"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-white dark:bg-gray-800 rounded-lg w-full max-w-md p-6 space-y-4">
      <h2 class="text-lg font-bold mb-4">
        {{ isHasPassword ? "Change Password" : "Set Password" }}
      </h2>

      <div v-if="isHasPassword" class="mb-3">
        <label class="text-sm">Current Password</label>
        <div class="relative">
          <input
            :type="show.current ? 'text' : 'password'"
            v-model="currentPass"
            class="w-full border p-2 rounded pr-10 dark:bg-gray-700" />
          <Icon
            @click="show.current = !show.current"
            :name="show.current ? 'fluent:eye-hide-20-filled' : 'fluent:eye-20-filled'"
            class="absolute right-3 top-3 cursor-pointer" />
        </div>
        <p v-if="errors.current" class="text-red-500 text-sm">{{ errors.current }}</p>
      </div>

      <div class="mb-3">
        <label class="text-sm">New Password</label>
        <div class="relative">
          <input
            :type="show.new ? 'text' : 'password'"
            v-model="newPass"
            class="w-full border p-2 rounded pr-10 dark:bg-gray-700" />
          <Icon
            @click="show.new = !show.new"
            :name="show.new ? 'fluent:eye-hide-20-filled' : 'fluent:eye-20-filled'"
            class="absolute right-3 top-3 cursor-pointer" />
        </div>
      </div>

      <div class="mb-3">
        <label class="text-sm">Confirm Password</label>
        <div class="relative mb-3">
          <input
            :type="show.confirm ? 'text' : 'password'"
            v-model="confirmPass"
            class="w-full border p-2 rounded pr-10 dark:bg-gray-700" />
          <Icon
            @click="show.confirm = !show.confirm"
            :name="show.confirm ? 'fluent:eye-hide-20-filled' : 'fluent:eye-20-filled'"
            class="absolute right-3 top-3 cursor-pointer" />
        </div>
        <p v-if="errors.confirm" class="text-red-500 text-sm">{{ errors.confirm }}</p>
      </div>

      <div class="flex justify-end gap-2 mt-4">
        <button @click="showModal = false" class="px-4 py-2 rounded bg-gray-300">Cancel</button>
        <button @click="submitPassword" class="px-4 py-2 rounded bg-green-600 text-white">
          Save
        </button>
      </div>
      <p v-if="errors.general" class="text-red-500 text-sm text-center">{{ errors.general }}</p>

    </div>
  </div>
</template>

<script setup>
import Cookies from "js-cookie";

const toast = useToast();
const config = useRuntimeConfig();
const accessToken = Cookies.get("access_token");
const userData = ref({ has_password: Cookies.get("has_password") });

const showModal = ref(false);
const isHasPassword = ref(false);

const currentPass = ref("");
const newPass = ref("");
const confirmPass = ref("");

const show = ref({
  current: false,
  new: false,
  confirm: false,
});

const errors = ref({
  current: "",
  confirm: "",
  general: "",
});

const openPasswordModal = () => {
  isHasPassword.value = userData.value.has_password === "true";
  showModal.value = true;
  errors.value = { current: "", new: "", confirm: "", general: "" };
};
const submitPassword = async () => {
  if (!newPass.value) {
    errors.value.new = "New password required.";
    return;
  }
  if (!confirmPass.value) {
    errors.value.confirm = "Confirm password required.";
    return;
  }
  if (newPass.value && confirmPass.value && newPass.value !== confirmPass.value) {
    errors.value.confirm = "Passwords do not match.";
    return;
  }
  if (isHasPassword.value && !currentPass.value) {
    errors.value.current = "Current password required.";
    return;
  }

  try {
    await $fetch(`${config.public.backend}/api/user/me`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: isHasPassword.value
        ? { current_password: currentPass.value, new_password: newPass.value }
        : { new_password: newPass.value },
    });
    toast.add({title: 'Password berhasil diubah.', color: 'green' });
    userData.value.has_password = "true";
    Cookies.set("has_password", "true");
    showModal.value = false;
  } catch (e) {
    if (e.response && e.response.status === 400) {
      errors.value.current = "Incorrect current password.";
    } else {
      errors.value.general = "Failed to update password.";
    }
  }
};
</script>
