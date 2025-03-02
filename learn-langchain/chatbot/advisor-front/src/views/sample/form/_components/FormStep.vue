<template>
  <div v-if="shouldShow">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue';

// FormWizard에서 주입된 ref
const currentIdx = (inject('STEP_COUNTER') as { value: number }).value++;
// 현재 활성화된 폼 스텝의 라이브 ref를 가져옴
const formStepIdx = inject<{ value: number }>('CURRENT_STEP_INDEX');

// 이 스텝이 표시되어야 하는지 여부
const shouldShow = computed(() => {
  return formStepIdx ? currentIdx === formStepIdx.value : false;
});
</script>
