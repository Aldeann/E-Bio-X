// Konfigurasi tema Nuxt UI.
// Palet lengkap ada di app/assets/css/main.css (@theme).
// `primary` memakai skala brand-* buatan sendiri; `neutral` digeser dari
// gray ke slate agar selaras dengan permukaan canvas/surface.
export default defineAppConfig({
  ui: {
    colors: {
      primary: "brand",
      neutral: "slate",
    },
  },
});
