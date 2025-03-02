<template>
  <div>
    <div>안드로이드 물리키 뒤로가기 모달 테스트11</div>
    <div>안드로이드 물리키 뒤로가기 모달 테스트11</div>
    <div>modal state: {{ isShowModal }}</div>
    <VBtn @click="onClickShowModal">모달 열기</VBtn>
    <VBtn @click="onClickShowInModal2">모달 열기</VBtn>
    <custom-modal
      v-model="isShowModal"
      :footer="[
        { name: 'close', label: '아니요', click: onClose },
        { name: 'ok', label: '예', click: onOk }
      ]"
    ></custom-modal>
    <custom-modal v-model="isShowModal2" :type="'bottom'">
      <template #modal-body>
        <div>모달 안에 모달</div>
        <VBtn @click="onClickShowInModal2">모달 열기</VBtn>
        <custom-modal v-model="isShowInModal2"></custom-modal>
      </template>
    </custom-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { VBtn } from 'vuetify/lib/components/index.mjs';
import CustomModal from '@/views/sample/components/CustomModal.vue';

const isShowModal = ref(true);
const isShowModal2 = ref(false);
const isShowInModal2 = ref(false);

const onClickShowModal = () => {
  isShowModal.value = !isShowModal.value;
};

const onClickShowInModal2 = () => {
  isShowModal2.value = !isShowModal2.value;
};

const onClose = () => {
  isShowModal.value = false;
};

const onOk = () => {
  isShowModal.value = false;
};
</script>

<style scoped></style>
