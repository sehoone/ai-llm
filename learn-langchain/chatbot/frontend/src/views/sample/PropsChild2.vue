<template>
  <div class="home">
    {{ props.keyword }}
  </div>
</template>

<script setup lang="ts">
import { defineProps, watch } from 'vue';
import { logger } from '@/utils/logger';

const props = defineProps({
  keyword: {
    type: String,
    default: '검색어'
  }
});
watch(
  () => props.keyword,
  (newKeyword, oldKeyword) => {
    logger.debug('props changed ' + newKeyword + ' ' + oldKeyword);
  }
);
</script>

<script lang="ts">
export default {
  name: 'samplePropsChild2',
  inheritAttrs: false,
  customOptions: {}
};
</script>
