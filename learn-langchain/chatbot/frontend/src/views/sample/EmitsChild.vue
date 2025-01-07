<template>
  <div>
    <v-card>
      <v-btn color="primary" @click="handleClickPrev">click call parent method name: prev</v-btn>
    </v-card>
    <v-card> <v-btn color="primary" @click="handleClickNext">click call parent method name: next</v-btn></v-card>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits(['next', 'prev']);
// emits: ['next', 'prev'],

const handleClickPrev = () => {
  emit('prev');
};
const handleClickNext = () => {
  emit('next');
};
</script>

<script lang="ts">
export default {
  name: 'sampleEmitsChild',
  inheritAttrs: false,
  customOptions: {}
};
</script>
