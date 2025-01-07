<template>
  <div>
    <span>
      <!-- Important: Multiple elements must be wrapped by one root element for transition to work -->
      <h1 ref="title"></h1>

      <section>
        Page 2 Body
        <div key="note1" :ref="(el) => addElement(el as HTMLElement)" class="fade-in-left">
          <em>Note: This is enclosed in &lt;span&gt; to support transition</em>
        </div>
        <div key="note2" :ref="(el) => addElement(el as HTMLElement)" class="fade-in-left">
          <em>Note: This is enclosed in &lt;span&gt; to support transition</em>
        </div>
        <div key="note3" :ref="(el) => addElement(el as HTMLElement)" class="fade-in-left">
          <em>Note: This is enclosed in &lt;span&gt; to support transition</em>
        </div>
        <div key="note4" :ref="(el) => addElement(el as HTMLElement)" class="fade-in-left">
          <em>Note: This is enclosed in &lt;span&gt; to support transition</em>
        </div>
      </section>
    </span>
  </div>
</template>

<script setup lang="ts">
import useUtility from '@/composables/useUtility';
import { ref, onMounted } from 'vue';

// === Composables ===
const utility = useUtility(import.meta);

console.log('[: ' + utility.currentFileName + ':mounted()] Starting...');

const fadeElements = ref([] as HTMLElement[]);

const addElement = (el: HTMLElement) => {
  if (el) fadeElements.value.push(el as HTMLElement);
};

onMounted(() => {
  fadeElements.value.forEach((element, index) => {
    element.style.setProperty('--i', (index + 1).toString());
  });
});
</script>

<style scoped>
@keyframes slideInLeft {
  0% {
    transform: translateX(-20%);
    visibility: hidden;
  }
  1% {
    visibility: visible;
  }
  100% {
    transform: translateX(0);
    visibility: visible;
  }
}

.fade-in-left {
  animation: slideInLeft 0.3s cubic-bezier(0.39, 0.575, 0.565, 1) both;
  visibility: hidden;
}

.fade-in-left {
  animation-delay: calc(0.1s * (var(--i) - 1));
}
</style>
