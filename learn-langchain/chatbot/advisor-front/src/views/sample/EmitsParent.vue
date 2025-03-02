<template>
  <div class="home">
    <v-card>
      <v-card-text>
        <p><b>Im parent</b></p>
        <p>Im parent person1.name: {{ person1.name }}</p>
        <p>
          Im parent method handleStepPrev:
          {{ isCalledMethodPrev }}
        </p>

        <p>
          Im parent method handleStep2Next:
          {{ isCalledMethodNext }}
        </p>
        <p>
          Im child username:
          {{ username }}
        </p></v-card-text
      >
    </v-card>
    <emits-child @prev="handleStepPrev" @next="handleStepNext"></emits-child>
    <label-input v-model:username="username" label="name"></label-input>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed, ref } from 'vue';
import EmitsChild from '@/views/sample/EmitsChild.vue';
import { logger } from '@/utils/logger';
import LabelInput from '@/views/sample/LabelInput.vue';

let person1 = reactive({
  name: 'sehoone1',
  age: 33,
  computedNameLength: computed((): number => person1.name.length) // computed예시.
});

let isCalledMethodPrev = ref(false);
let isCalledMethodNext = ref(false);
const username = ref('');

const handleStepPrev = () => {
  logger.debug('call handleStepPrev');
  isCalledMethodPrev.value = !isCalledMethodPrev.value;
};
const handleStepNext = () => {
  logger.debug('call handleStepPrev');
  isCalledMethodNext.value = !isCalledMethodNext.value;
  logger.debug('call username', username);
};
</script>

<script lang="ts">
export default {
  name: 'sampleEmitsParent',
  inheritAttrs: false,
  customOptions: {}
};
</script>
