<template>
  <div>
    <h3>로그인 페이지</h3>

    <div>
      <p>sampleAuthStore.authInfo : {{ sampleAuthStore.authInfo }}</p>
      <p>authStore.isLodingAuthInfo: {{ sampleAuthStore.isLodingAuthInfo }}</p>
      <p>authStore.isDoneAuthInfo : {{ sampleAuthStore.isDoneAuthInfo }}</p>
      <p>authStore.errorAuthInfo : {{ sampleAuthStore.errorAuthInfo }}</p>

      <div v-if="sampleAuthStore.getIsLogin && sampleAuthStore.getToken !== ''">
        <p>로그인 되었습니다.</p>

        <p>userId : {{ sampleAuthStore.authInfo.userId }}</p>
        <p>name : {{ sampleAuthStore.authInfo.name }}</p>
        <p>lv : {{ sampleAuthStore.authInfo.lv }}</p>
        <div>
          <input type="button" value="LOGOUT" @click="onClickLogout" />
        </div>
      </div>

      <div v-else>
        <form name="normal-form" @submit.prevent="onClickLogin">
          <v-text-field :counter="10" label="UserId" hide-details required></v-text-field>

          <v-text-field label="Password" persistent-hint type="input"></v-text-field>
          <p>
            <input type="submit" value="LOGIN" :disabled="sampleAuthStore.isLodingAuthInfo" />
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSampleAuthStore } from '@/service/sample/sampleAuthModule';
import { onMounted, onUnmounted } from 'vue';
import { logger } from '@/utils/logger';

/* request, prepare, on, cb, action */

const sampleAuthStore = useSampleAuthStore();

async function requestApiHttpAuth(): Promise<void> {
  await sampleAuthStore.actionHttpAuth({});
}

function onClickLogin(): void {
  requestApiHttpAuth()
    .then(() => {
      console.log('ok');
    })
    .catch((err) => {
      console.log(err);
    });
}
function onClickLogout(): void {
  logger.debug('log out!!');
  sampleAuthStore.actionLogout();
}

onMounted(() => {
  logger.debug('mounted memberMain');
});
onUnmounted(() => {
  logger.debug('unmounted memberMain');
});
</script>

<script lang="ts">
export default {
  name: 'loginPage',
  inheritAttrs: false,
  customOptions: {}
};
</script>
