<template>
  <label class="form-label" id="child-id">
    {{ label }}
  </label>
  <input v-model="labelValue" type="text" class="form-control" />
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps({
  username: {
    type: String,
    required: true
  },
  label: {
    type: String,
    required: false
  }
});
const emit = defineEmits(['update:username']);

const labelValue = computed({
  get() {
    return props.username;
  },
  set(labelValue) {
    emit('update:username', labelValue);
  }
});
</script>

<style lang="scss" scoped></style>
