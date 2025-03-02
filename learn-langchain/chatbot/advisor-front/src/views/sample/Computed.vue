<template>
  <div class="home">
    <v-card>
      <v-card-text>
        <p><b>ref:</b> name: {{ person1.name }}</p>
        <p><b>ref:</b> age: {{ person1.age }}</p>
        <p><b>ref:</b> computedNameLength: {{ person1.computedNameLength }}</p></v-card-text
      >
      <v-card-text>
        <p><b>reactive:</b> name: {{ person2.name }}</p>
        <p><b>reactive:</b> age: {{ person2.age }}</p>
        <p><b>reactive:</b> computedNameLength: {{ person2.computedNameLength }}</p>
        <p><b>computedAgePulusFive:</b> {{ computedAgePulusFive }}</p></v-card-text
      >
    </v-card>

    <v-btn color="primary" @click="handleClick">click add name string</v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue';

// computed 를 ref/reactive 선언할때 사용가능하고, 반응형 데이터와 별도로 외부에서도 사용가능
const person1 = ref({
  name: 'sehoone',
  age: 33,
  computedNameLength: computed((): number => person1.value.name.length) // computed예시. ref는 .value를 통해서 접근
});
let person2 = reactive({
  name: 'sehoone2',
  age: 33,
  computedNameLength: computed((): number => person2.name.length) // computed예시.
});

// computed용 변수 선언.
let computedAgePulusFive = computed((): number => person2.age + 5);

const handleClick = () => {
  person2.name = person2.name + '!';
  person2.age = ++person2.age;
  person1.value.name = person1.value.name + '!!';
};
</script>

<script lang="ts">
export default {
  name: 'sampleHelloWorld',
  inheritAttrs: false,
  customOptions: {}
};
</script>
