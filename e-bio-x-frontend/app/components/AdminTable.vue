<template>
  <div class="p-4 bg-white dark:bg-gray-900">
    <div class="flex w-full mb-4 gap-4 justify-between items-center">
      <input
        v-model="searchTerm"
        type="text"
        placeholder="Search..."
        class="border border-gray-300 focus:outline-green-500 bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded p-2 w-full max-w-xs" />

      <div v-if="props.filters.length" class="flex gap-4 items-center">
        <div v-for="(filter, idx) in props.filters" :key="idx" class="flex items-center gap-0">
          <label class="border text-gray-900 dark:text-gray-100 rounded p-2"
            >{{ filter.title }}:</label
          >
          <select
            v-model="activeFilters[idx]"
            class="border bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded p-2">
            <option value="" selected>Semua</option>
            <option v-for="option in filter.options" :key="option" :value="option">
              {{ option }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <div class="overflow-x-auto border border-gray-300 rounded">
      <table class="table-auto w-full text-left">
        <thead class="bg-green-100 text-green-600 dark:text-green-200 dark:bg-green-900">
          <tr>
            <th class="p-3 border-b border-gray-300 w-12">#</th>
            <th v-for="(col, index) in columns" :key="index" class="p-3 border-b border-gray-300">
              {{ col.header }}
            </th>
            <th v-if="onUpdate || onDelete" class="p-3 border-b border-gray-300">Action</th>
          </tr>
        </thead>

        <tbody class="text-gray-900 dark:text-gray-100">
          <tr
            v-for="(item, rowIdx) in paginatedData"
            :key="rowIdx"
            class="border-b border-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600">
            <td class="p-3">{{ (currentPage - 1) * pageSize + rowIdx + 1 }}</td>

            <td v-for="(col, colIdx) in columns" :key="colIdx" class="p-3">
              <template v-if="col.cell">
                <div v-html="col.cell({ row: { original: item } })"></div>
              </template>
              <template v-else-if="typeof item[col.accessorKey] === 'string' && item[col.accessorKey].startsWith('http')">
                <a
                  :href="item[col.accessorKey]"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-blue-500 underline flex items-center gap-1"
                >
                  {{ item[col.accessorKey].length > 30 ? item[col.accessorKey].slice(0, 30) + '...' : item[col.accessorKey] }}
                  <Icon name="material-symbols:open-in-new" class="w-4 h-4 inline" />
                </a>
              </template>
              <template v-else>
                {{ item[col.accessorKey] }}
              </template>
            </td>

            <td v-if="onUpdate || onDelete" class="p-3 flex gap-2">
              <button
                v-if="onUpdate"
                @click="() => onUpdate(item)"
                class="text-yellow-400 hover:text-yellow-600"
                title="Edit"
                aria-label="Edit">
                <Icon name="material-symbols:box-edit-outline" class="w-5 h-5" />
              </button>

              <button
                v-if="onDelete"
                @click="() => onDelete(item)"
                class="text-red-500 hover:text-red-700"
                title="Hapus"
                aria-label="Hapus">
                <Icon name="material-symbols:delete-outline" class="w-5 h-5" />
              </button>
            </td>
          </tr>

          <tr v-if="filteredData.length === 0">
            <td :colspan="columns.length + 1" class="text-center text-gray-500 p-4">
              {{ emptyMessage }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="flex justify-between items-center mt-4 text-sm text-gray-600">
      <p>
        Menampilkan
        {{ Math.min((currentPage - 1) * pageSize + 1, totalItems) }} -
        {{ Math.min(currentPage * pageSize, totalItems) }} dari {{ totalItems }} data
      </p>
      <div class="flex gap-2">
        <button
          @click="currentPage = Math.max(currentPage - 1, 1)"
          :disabled="currentPage === 1"
          class="px-3 py-1 border rounded disabled:opacity-50">
          Prev
        </button>
        <button
          @click="currentPage = Math.min(currentPage + 1, totalPages)"
          :disabled="currentPage === totalPages || totalPages === 0"
          class="px-3 py-1 border rounded disabled:opacity-50">
          Next
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";

const props = defineProps({
  data: Array,
  columns: Array,
  pageSize: {
    type: Number,
    default: 10,
  },
  emptyMessage: {
    type: String,
    default: "Tidak ada data ditemukan.",
  },
  onUpdate: Function,
  onDelete: Function,
  filters: {
    type: Array,
    default: () => [],
  },
});

const searchTerm = ref("");
const currentPage = ref(1);
const activeFilters = ref([]);

const filteredData = computed(() => {
  let result = props.data;

  result = result.filter((item) =>
    Object.values(item).some((value) =>
      String(value).toLowerCase().includes(searchTerm.value.toLowerCase())
    )
  );

  props.filters.forEach((filter, idx) => {
    const filterValue = activeFilters.value[idx];
    if (filterValue) {
      result = result.filter((item) => item[filter.accessorKey] === filterValue);
    }
  });

  return result;
});

const totalPages = computed(() => Math.ceil(filteredData.value.length / props.pageSize));
const totalItems = computed(() => filteredData.value.length);

const paginatedData = computed(() =>
  filteredData.value.slice(
    (currentPage.value - 1) * props.pageSize,
    currentPage.value * props.pageSize
  )
);

watch(searchTerm, () => (currentPage.value = 1));
</script>
