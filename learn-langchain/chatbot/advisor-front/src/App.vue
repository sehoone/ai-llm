<template>
  <router-view></router-view>
</template>
<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { loadEmulWebToNativeBridge, loadNativeToWebBridge } from './utils';
import { loadGlobalEventListner, removeGlobalEventListner } from './bootstraps/globalEventHandler';

onMounted(() => {
  loadEmulWebToNativeBridge(); // 개발용 브릿지 애뮬레이터 로드
  loadNativeToWebBridge(); // 네이티브 브릿지 로드
  loadGlobalEventListner(); // 전역 이벤트 리스너 등록
});
onUnmounted(() => {
  removeGlobalEventListner(); // 전역 이벤트 리스너 제거
});
</script>

<style scoped></style>
