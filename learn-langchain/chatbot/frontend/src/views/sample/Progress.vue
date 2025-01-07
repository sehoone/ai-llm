<template>
  <div>
    <v-card>
      <v-card-text>
        <p>ref: {{ person1.name }} {{ person1.age }}</p></v-card-text
      >
      <v-card-text
        ><p>reactive: {{ person2.name }} {{ person2.age }}</p></v-card-text
      >
      <v-card-text
        ><p>ref, reactive: {{ company1 }} {{ company2.company }}</p></v-card-text
      >
    </v-card>

    <v-btn color="primary" @click="handleClick">click next year</v-btn>
    <div class="center">
      <v-progress-circular color="primary" indeterminate></v-progress-circular>
    </div>
  </div>
</template>

<script setup lang="ts">
import { logger } from '@/utils/logger';
import { onMounted, onUnmounted, reactive, ref } from 'vue';

onMounted(() => {
  logger.debug('mounted sampleReactive');
});
onUnmounted(() => {
  logger.debug('unmounted sampleReactive');
});

// composition api는 vue2에서 option api의 data option에 정의하는 반응형 데이터를 ref/reactive 로 정의하여 사용
const person1 = ref({ name: 'sehoone1', age: 30 });
const person2 = reactive({ name: 'sehoone2', age: 33 });

let company1 = ref('openobject'); //ref는 원시객체에 사용. ref도 object를 사용할 수 있지만 .value를 통해서 접근필요
let company2 = reactive({ company: 'openobject' }); //reactive는 object에 사용. 원시속성을 사용할 수 없음. 개체의 반응 복사본을 반환

const handleClick = () => {
  // ref는 function에서 값을 변경할 때 ref.value를 넣어값을 바꿈
  person1.value.age = ++person1.value.age;
  //reactive는 바로 값을 바꿈
  person2.age = ++person2.age;

  company1.value = 'openobject!!';
  company2.company = 'openobject!@';
};
</script>

<script lang="ts">
export default {
  name: 'sampleReactive',
  inheritAttrs: false,
  customOptions: {}
};
</script>

<style scoped>
.center {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
</style>
