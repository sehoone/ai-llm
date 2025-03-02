<template>
  <div>
    <NavigationLayoutVue></NavigationLayoutVue>
    <v-main>
      <v-container class="fill-height" fluid>
        <router-view></router-view>
      </v-container>
    </v-main>
  </div>
</template>

<script setup lang="ts">
import NavigationLayoutVue from '@/layouts/sample/NavigationLayout.vue';
</script>
