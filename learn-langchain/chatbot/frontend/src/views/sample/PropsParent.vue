<template>
  <div class="home">
    <v-card>
      <v-card-text>
        <p><b>Im parent</b></p>
        <p>Im parent person1.name: {{ person3.name }}</p></v-card-text
      >
    </v-card>
    <props-child :person1="person3" :title></props-child>
    <v-btn color="primary" @click="handleClick">click parent btn</v-btn>
    <br />
    <!-- v-model 양방향 바인딩된 model은 한글의 경우 글자가 완성 model이 업데이트됨. 
      한글의 경우 IME가 필요한 언어(입력된 문자가 계산되어서 글자를 만드는 언어)
    그래서 @input을 사용하여 이벤트를 model에 넣어줘야함-->
    <!-- <input type="text" v-model="keyword" @input="debouncedUpdateKeyword" /> -->
    <input type="text" @input="debouncedUpdateKeyword" />
    <PropsChild2 :keyword="keyword"></PropsChild2>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, ref } from 'vue';
import PropsChild from '@/views/sample/PropsChild.vue';
import PropsChild2 from '@/views/sample/PropsChild2.vue';
import { type person1Model } from '@/service/sample/model/compositionModel';
import { debounce } from 'lodash-es';

const title = ref('제목!');
const keyword = ref('');
const person3: person1Model = reactive({
  name: 'sehoone1',
  age: 33,
  computedNameLength: computed((): number => person3.name.length) // computed예시.
});

const handleClick = () => {
  person3.name = person3.name + '!';
};

const updateKeyword = (e: Event) => {
  keyword.value = (e.target as HTMLInputElement).value;
};

const debouncedUpdateKeyword = debounce(updateKeyword, 300);
</script>

<script lang="ts">
export default {
  name: 'samplePropsParent',
  inheritAttrs: false,
  customOptions: {}
};
</script>
