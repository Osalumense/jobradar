<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<style>
*, *::before, *::after {
  box-sizing: border-box;
}
button, [role="button"], label[for], a {
  cursor: pointer;
}
button:disabled {
  cursor: not-allowed;
}
</style>
