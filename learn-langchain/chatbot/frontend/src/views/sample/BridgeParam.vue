<template>
  <div>
    <slot></slot>
    <div v-for="(param, index) of props.params" :key="index">
      <v-text-field v-model="param.inputKey" :label="param.key" :placeholder="param.key"></v-text-field>
      <v-text-field v-model="param.inputValue" :label="param.value" :placeholder="param.value"></v-text-field>
    </div>
  </div>
</template>

<script setup lang="ts">
export type BridgeParams = {
  key: string;
  value: string;
  inputKey: string;
  inputValue: string;
};
const props = defineProps({
  params: {
    type: Array as () => BridgeParams[],
    defalut: () => [],
    required: true
  }
});

//let inputParams = reactive([]);
//return { inputParams };
</script>

<script lang="ts">
export default {
  name: 'sampleBrigdeParam',
  inheritAttrs: false,
  customOptions: {}
};
</script>
