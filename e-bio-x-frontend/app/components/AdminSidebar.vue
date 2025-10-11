<template>
  <button
    @click="toggleSidebar"
    type="button"
    class="fixed top-0 left-0 items-center p-2 mt-2 ms-3 text-sm text-white rounded-lg sm:hidden hover:bg-green-500 focus:outline-none focus:ring-2 focus:ring-green-500">
    <span class="sr-only">Open sidebar</span>
    <Icon name="material-symbols:menu-rounded" />
  </button>

  <div
    v-if="isSidebarOpen"
    @click="toggleSidebar"
    class="fixed inset-0 bg-black bg-opacity-50 z-30 sm:hidden"></div>

  <aside
    id="default-sidebar"
    ref="sidebar"
    :class="[
      'fixed top-0 left-0 z-40 w-64 h-screen transition-transform text-white',
      isSidebarOpen ? 'translate-x-0' : '-translate-x-full',
      'sm:translate-x-0',
    ]"
    aria-label="Sidebar">
    <div class="h-full px-3 py-4 overflow-y-auto bg-green-700">
      <div class="mb-2">
        <ToggleDark/>
      </div>
      <ul class="space-y-2 font-medium">
        <li v-for="(item, index) in navbarMenu" :key="index">
          <RouterLink
            :to="item.path"
            :class="[
              'flex items-center p-2 rounded-lg group',
              route.path === item.path ? 'bg-green-500' : 'hover:bg-green-600',
            ]">
            <Icon :name="item.icon" />
            <span class="ms-3">{{ item.name }}</span>
          </RouterLink>
        </li>
      </ul>
      
      <hr class="my-3">
      <RouterLink
        to="/account"
        :class="[
          'flex items-center p-2 rounded-lg group',
          route.path === '/account' ? 'bg-green-600' : 'hover:bg-green-500',
        ]">
        <Icon name="mdi:cog" />
        <span class="ms-3">Setting</span>
      </RouterLink>
      <div class="flex bottom-0 mt-3 font-medium">
        <button 
          @click="handleLogout" 
          class="flex w-full items-center p-2 rounded-lg group hover:bg-red-500">
          <Icon name="ic:baseline-log-out" />
          <span class="ms-3">Logout</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from "vue";
import { useRoute } from "vue-router";
import { useSwal } from "~/utils/swal";
import { useRouter } from "vue-router";
import Cookies from "js-cookie";

const isSidebarOpen = ref(false);
const router = useRouter();
const route = useRoute();
const swal = useSwal();

function toggleSidebar() {
  isSidebarOpen.value = !isSidebarOpen.value;
}

const navbarMenu = [
  {
    name: "Dashbaord",
    icon: "mdi:home",
    path: "/admin",
  },
  {
    name: "User",
    icon: "mdi:user",
    path: "/admin/users",
  },
  {
    name: "Kelas",
    icon: "arcticons:classchartsstudents",
    path: "/admin/courses",
  },
  {
    name: "Materi",
    icon: "simple-icons:bookstack",
    path: "/admin/materials",
  },
];

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
