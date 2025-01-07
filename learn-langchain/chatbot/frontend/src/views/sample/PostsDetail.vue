<template>hi</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { logger } from '@/utils/logger';

// const props = defineProps({
//   item: {
//     type: Object,
//     required: true
//   },
//   isLoadingPostRead: {
//     type: Boolean,
//     required: true
//   },
//   donePostRead: {
//     type: Boolean,
//     required: true
//   },
//   onClickBackBtn_: {
//     type: Function,
//     required: true
//   },
//   onClickEditBtn_: {
//     type: Function,
//     required: true
//   }
// });

// function onClickBackBtn() {
//   props.onClickBackBtn_();
// }
// function onClickEditBtn(id: string) {
//   props.onClickEditBtn_(id);
// }
onMounted(() => {
  logger.debug('mounted viewRead');
});
onUnmounted(() => {
  logger.debug('unmounted viewRead');
});
</script>
