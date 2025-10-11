export default defineNuxtRouteMiddleware((to, from) => {
  const token = useCookie("access_token").value;
  const role = useCookie("role").value;

  if (!token) {
    return navigateTo("/login");
  }

  if (to.meta.role && to.meta.role !== role) {
    return navigateTo("/forbidden");
  }
});
