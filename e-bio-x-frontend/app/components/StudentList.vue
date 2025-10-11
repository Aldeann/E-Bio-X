<template>
  <div class="p-6 bg-white dark:bg-gray-900 rounded-xl dark:shadow-green-400 dark:border-none border shadow-lg border-green-200">
    <h2 class="text-xl font-semibold text-green-700 dark:text-green-500 flex items-center gap-2">
      <Icon name="arcticons:classchartsstudents" class="text-green-500" /> 
      Daftar Siswa
      <small>({{ props.students.length }})</small>
    </h2>

    <div class="overflow-x-auto max-w-full">
      <AdminTable
        :data="props.students"
        :columns="columns"
        :pageSize="10"
        :onDelete="isTeacher ? handleRemoveStudent : undefined"
      />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  students: Array,
  courseId: [String, Number],
});

const toast = useToast();
const swal = useSwal();
const config = useRuntimeConfig();
const token = useCookie("access_token").value;
const role = useCookie("role").value;

const isTeacher = computed(() => role === "teacher");
const handleRemoveStudent = async (student) => {
  const result = await swal.fire({
    title: `Keluarkan ${student.name}?`,
    text: "Apakah Anda yakin ingin mengeluarkan siswa ini dari kelas?",
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Ya, keluarkan",
    cancelButtonText: "Batal",
    reverseButtons: true,
  });

  if (!result.isConfirmed) {
    return;
  }

  try {
    await $fetch(`${config.public.backend}/api/courses/${props.courseId}/students/${student.id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    toast.add({
      title: `${student.name} berhasil dikeluarkan dari kelas`,
      color: "green"
    });

    emit('studentRemoved', student.id);
  } catch (error) {
    toast.add({
      title: "Gagal mengeluarkan siswa dari kelas",
      color: "red"
    });
  }
};

const emit = defineEmits(['studentRemoved']);

const columns = [
  { header: "Username", accessorKey: "name" },
  { header: "Email", accessorKey: "email" },
  {
    header: "Quiz Scores",
    accessorKey: "quizes",
    cell: ({ row }) => {
      const quizes = row.original.quizes;
      if (!quizes || quizes.length === 0) return "Belum ada kuis dikerjakan";
      return `
        <div class="flex flex-col gap-2">
          ${quizes
            .map(
              (q) => `
                <div class="bg-green-50 dark:bg-green-800 border border-green-200 dark:border-green-600 rounded-lg p-2">
                  <div class="font-semibold text-green-700 dark:text-green-300">${q.title}</div>
                  <div class="text-gray-900 dark:text-gray-100">Skor: ${q.score.toFixed(2)}</div>
                  <div class="text-gray-900 dark:text-gray-100">Cluster: ${q.cluster}</div>
                </div>
              `
            )
            .join("")}
        </div>
      `;
    },
  },
];
</script>