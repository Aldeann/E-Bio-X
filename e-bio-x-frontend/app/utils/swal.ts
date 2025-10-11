import Swal from "sweetalert2";

export const useSwal = () => {
  const isDark =
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark");

  return Swal.mixin({
    customClass: {
      confirmButton: "bg-green-600 text-white px-4 py-2 mx-4 rounded hover:bg-green-700",
      cancelButton: isDark
        ? "bg-gray-700 text-white px-4 py-2 mx-4 rounded hover:bg-gray-600"
        : "bg-gray-300 text-gray-700 px-4 py-2 mx-4 rounded hover:bg-gray-400",
      popup: isDark
        ? "p-6 bg-gray-700 text-white"
        : "p-6 bg-white text-gray-800",
      title: "text-xl font-semibold mb-4",
      input: isDark
        ? "border rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-700 text-white"
        : "border rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-800",
    },
    buttonsStyling: false,
  });
};
