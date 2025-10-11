export default defineNuxtRouteMiddleware((to, from) => {
  const token = useCookie("access_token").value;
  const role = useCookie("role").value;

  if (token && role) {
    return navigateTo(`/${role}`);
  }
});