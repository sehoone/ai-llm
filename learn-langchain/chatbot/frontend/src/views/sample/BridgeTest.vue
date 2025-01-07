<template>
  <div>
    <h1>web to native</h1>
    <p>name: deviceInfo</p>
    <p>- request</p>
    <v-textarea rows="2" readonly value='{ "requstId": "requstId2" }'> </v-textarea>
    <p>- response</p>
    <v-textarea
      rows="3"
      readonly
      value='{"osCd":"A","uuId":"TEST_UUID","requstId":"requstId0","response":{"code":0,"message":"OK"}}'
    >
    </v-textarea>
    <v-btn color="primary" @click="callWebToNative">deviceInfo call</v-btn>
    <p>response</p>
    <v-textarea label="Description" placeholder="Enter some text..." v-model="responseBridge" rows="3"></v-textarea>

    <h1>native to web</h1>
    <p>name: webViewBack</p>
    <p>- request</p>
    <v-textarea auto-grow readonly value=""> </v-textarea>
    <p>- response</p>
    <v-textarea auto-grow readonly value='{"response":{"code":0,"message":"OK"}}'> </v-textarea>
    <br />
    <p>name: keypad</p>
    <p>- request</p>
    <v-textarea auto-grow readonly v-model="inputKey"> </v-textarea>
    <p>- response</p>
    <v-textarea auto-grow readonly value='{"response":{"code":0,"message":"OK"}}'> </v-textarea>
  </div>
</template>

<script setup lang="ts">
import { getAppBridge } from '@/utils';
import type AppBridge from '@/utils/hybrid';
import { onMounted, onUnmounted, ref } from 'vue';
import { type DeviceInfoRequest } from '@/utils/hybrid/device/device.type';
import { logger } from '@/utils/logger';
import type { InputEncKeypadRequest } from '@/utils/hybrid/util/nativeToWeb.type';

const responseBridge = ref('');
const requstCount = ref(0);
const createdRequstId = ref('');
const inputKey = ref('');

let appBridge: AppBridge;
onMounted(async () => {
  appBridge = await getAppBridge();
  console.log('appBridge ', appBridge);
  window.addEventListener('inputEncKeypad', inputEncKeypad as EventListener);
});

onUnmounted(() => {
  window.removeEventListener('inputEncKeypad', inputEncKeypad as EventListener);
});

const callWebToNative = async () => {
  const deviceInfoParam = {
    requstId: 'requstId' + requstCount.value
  } as DeviceInfoRequest;

  const data = await appBridge.deviceInfo(deviceInfoParam);
  responseBridge.value = JSON.stringify(data);
  requstCount.value = requstCount.value + 1;
  createdRequstId.value = deviceInfoParam.requstId;
};

/**
 * 테스트 방법: chrome console에서 아래와 같이 입력
 * const event = new CustomEvent('inputEncKeypad', { detail: { inputValue: '11' } });
 * window.dispatchEvent(event);
 */
const inputEncKeypad = (e: CustomEvent<InputEncKeypadRequest>): void => {
  logger.debug('call inputEncKeypad ' + e.detail.inputValue);
  inputKey.value = e.detail.inputValue;
};
</script>

<style scoped></style>
