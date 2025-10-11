export default {
  darkMode: "class",
  content: [
    "./components/**/*.{vue,js,ts}",
    "./layouts/**/*.vue",
    "./pages/**/*.vue",
    "./plugins/**/*.{js,ts}",
    "./app.vue",
  ],
  theme: {
    extend: {
      transitionProperty: {
        "bg-color": "background-color, color",
      },
    },
  },
  plugins: [],
};
