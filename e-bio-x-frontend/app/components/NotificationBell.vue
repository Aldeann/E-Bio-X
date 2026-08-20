<template>
  <div class="relative">
    <button @click.stop="togglePanel" class="relative p-1.5 rounded-lg hover:bg-white/15 transition flex items-center" title="Notifikasi">
      <Icon name="material-symbols:notifications-outline" class="w-5 h-5" />
      <span v-if="unread > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
        {{ unread > 99 ? "99+" : unread }}
      </span>
    </button>

    <div
      v-if="open"
      @click.stop
      class="absolute right-0 top-full mt-2 w-80 max-w-[90vw] bg-white dark:bg-gray-800 text-black dark:text-gray-100 rounded-xl shadow-xl z-50 overflow-hidden border border-gray-200 dark:border-gray-700"
    >
      <div class="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <h3 class="font-semibold text-sm">Notifikasi</h3>
        <button v-if="unread > 0" @click="markAllRead" class="text-xs text-green-600 dark:text-green-400 hover:underline">
          Tandai semua dibaca
        </button>
      </div>

      <div class="max-h-80 overflow-y-auto">
        <div v-if="loading" class="p-4 space-y-2">
          <div v-for="i in 3" :key="i" class="h-10 bg-green-100 dark:bg-gray-700 rounded-lg animate-pulse"></div>
        </div>
        <div v-else-if="items.length === 0" class="p-6 text-center text-gray-400 text-sm">
          <Icon name="material-symbols:notifications-off-outlined" class="text-3xl mx-auto mb-2 text-gray-300 dark:text-gray-600" />
          Belum ada notifikasi.
        </div>
        <button
          v-for="n in items"
          :key="n.id"
          @click="openNotification(n)"
          class="w-full text-left px-4 py-3 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
          :class="n.is_read ? 'opacity-60' : 'bg-green-50/50 dark:bg-green-950/20'">
          <div class="flex items-start gap-2">
            <span v-if="!n.is_read" class="w-2 h-2 mt-1.5 rounded-full bg-green-500 shrink-0"></span>
            <div class="min-w-0">
              <p class="text-sm text-gray-800 dark:text-gray-200 leading-snug">{{ n.message }}</p>
              <p class="text-xs text-gray-400 mt-0.5">
                <template v-if="n.actor_name"><span class="font-medium text-green-600 dark:text-green-400">{{ n.actor_name }}</span> • </template>
                {{ formatDate(n.created_at) }}
              </p>
            </div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const role = useCookie("role").value;
const router = useRouter();

const items = ref([]);
const unread = ref(0);
const open = ref(false);
const loading = ref(false);
let timer = null;

const fetchNotifications = async () => {
  if (!token) return;
  loading.value = true;
  try {
    const res = await $fetch(`${config.public.backend}/api/notifications?limit=30`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    items.value = res.notifications || [];
    unread.value = res.unread || 0;
  } catch (err) {
    console.error(err);
  } finally {
    loading.value = false;
  }
};

const togglePanel = () => {
  open.value = !open.value;
  if (open.value) fetchNotifications();
};

const openNotification = async (n) => {
  if (!n.is_read) {
    try {
      await $fetch(`${config.public.backend}/api/notifications/${n.id}/read`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
      });
      n.is_read = true;
      unread.value = Math.max(0, unread.value - 1);
    } catch (err) {
      console.error(err);
    }
  }
  open.value = false;
  if (n.forum_id) {
    router.push(`/${role.value}/forum/${n.forum_id}`);
  }
};

const markAllRead = async () => {
  try {
    await $fetch(`${config.public.backend}/api/notifications/read-all`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    });
    items.value = items.value.map((n) => ({ ...n, is_read: true }));
    unread.value = 0;
  } catch (err) {
    console.error(err);
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
};

onMounted(() => {
  fetchNotifications();
  timer = setInterval(fetchNotifications, 30000);
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
</script>