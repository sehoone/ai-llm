<template>
  <form @submit="onSubmit">
    <slot />

    <div>
      <button v-if="hasPrevious" type="button" @click="goToPrev">Previous</button>
      <button type="submit">{{ isLastStep ? 'Submit' : 'Next' }}</button>
    </div>

    <pre>{{ values }}</pre>
  </form>
</template>

<script setup lang="ts">
import { useForm } from 'vee-validate';
import { ref, computed, provide } from 'vue';

const props = defineProps({
  validationSchema: {
    type: Array,
    required: true
  }
});
// 이벤트를 부모 컴포넌트로 전달하기 위한 emit 정의
const emit = defineEmits(['submit']);
const currentStepIdx = ref(0);

// 시작 스텝을 자식 <form-steps> 컴포넌트에 주입
const stepCounter = ref(0);
provide('STEP_COUNTER', stepCounter);

// 현재 스텝 인덱스를 자식 컴포넌트에 주입
// 각 form-step의 가시성을 토글하는 데 사용됨
provide('CURRENT_STEP_INDEX', currentStepIdx);

// 마지막 스텝인지 확인
const isLastStep = computed(() => {
  return currentStepIdx.value === stepCounter.value - 1;
});

// 'previous' 버튼이 나타나야 하는지 확인
const hasPrevious = computed(() => {
  return currentStepIdx.value > 0;
});

// 개별 스텝의 검증 스키마 추출
const currentSchema = computed(() => {
  return props.validationSchema[currentStepIdx.value];
});

// vee-validate의 useForm 훅 사용
const { values, handleSubmit } = useForm({
  // vee-validate가 computed 스키마 변경을 인식하도록 설정
  validationSchema: currentSchema,
  // 다음 스텝으로 이동하거나 이전 스텝으로 돌아갈 때 각 스텝의 값을 유지하도록 설정
  keepValuesOnUnmount: true
});

// 'submit' 핸들러를 사용하여 다음 스텝으로 진행하거나 마지막 스텝일 경우 폼 제출
const onSubmit = handleSubmit((values) => {
  if (!isLastStep.value) {
    currentStepIdx.value++;
    return;
  }

  // 모든 스텝이 완료되었음을 부모에게 알림
  emit('submit', values);
});

// 이전 단계로 이동
function goToPrev() {
  if (currentStepIdx.value === 0) {
    return;
  }

  currentStepIdx.value--;
}
</script>
