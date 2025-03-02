<template>
  <div class="home">
    <v-btn color="primary" @click="haldleHelloText()"> call helloworld1 </v-btn>
    <br /><br />

    <p>응답값:{{ helloworldText1 }}</p>
  </div>
</template>

<script setup lang="ts">
import { logger } from '@/utils/logger';
import { useHelloWorldStore } from '@/service/sample/helloWorldModule';
import { ref } from 'vue';

const helloWorldStore = useHelloWorldStore();

let helloworldText1 = ref('');

async function haldleHelloText() {
  logger.debug('log test debug');
  logger.error('log test error');
  logger.warn('log test warn');
  logger.info('log test info');
  console.warn('console test warn');
  console.error('console test error');

  const data = await helloWorldStore.reqHelloText();
  console.log('haldleHelloText data' + helloWorldStore.getHelloText);
  helloworldText1.value = data.helloText;
}
</script>
<script lang="ts">
export default {
  name: 'helloworld',
  inheritAttrs: false,
  customOptions: {}
};
</script>
