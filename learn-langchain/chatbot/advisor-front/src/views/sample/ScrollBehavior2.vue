<template>
  <div>
    <v-btn color="primary" @click="onClickGoBack">click go back</v-btn>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';

const router = useRouter();

const onClickGoBack = () => {
  router.back();
};
</script>

<style scoped></style>
