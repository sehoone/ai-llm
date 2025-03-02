<template>
  <h1 ref="title"></h1>
</template>

<script>
import useUtility from '@/composables/useUtility';

export default {
  setup() {
    // === Composables ===
    const utility = useUtility(import.meta);

    return {
      utility
    };
  },
  mounted() {
    console.log(`[${this.utility.currentFileName}::mounted()] Starting...`);

    this.$refs.title.innerText = this.$options.__file.split('/').pop();
  }
};
</script>
