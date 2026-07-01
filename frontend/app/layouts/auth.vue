<template>
  <div class="auth-shell">
    <div class="auth-bg-blobs">
      <span class="blob blob-1" />
      <span class="blob blob-2" />
    </div>
    <slot />
  </div>
</template>

<style scoped>
.auth-shell {
  min-height: 100vh;
  background: #0d0f12;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.auth-bg-blobs { pointer-events: none; }
.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.18;
}
.blob-1 {
  width: 420px; height: 420px;
  background: #10b981;
  top: -100px; left: -120px;
}
.blob-2 {
  width: 340px; height: 340px;
  background: #6366f1;
  bottom: -80px; right: -60px;
}
</style>
