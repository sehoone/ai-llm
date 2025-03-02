<template>
  <div>
    <h1>alert / confirm test</h1>
  </div>
</template>
<script lang="ts">
export default {
  name: 'confirmTest',
  inheritAttrs: false,
  customOptions: {},
  setup: () => setup
};

function setup() {
  console.log('setup');
}
</script>
