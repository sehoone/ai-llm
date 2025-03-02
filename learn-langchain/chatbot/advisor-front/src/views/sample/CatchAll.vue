<script setup>
import { onMounted, toRaw } from 'vue';
import { useRoute } from 'vue-router';
import useUtility from '@/composables/useUtility';

// === Composables ===
const route = useRoute();
const utility = useUtility(import.meta);

// === Life Cycle Hooks ===
onMounted(() => {
  console.log(`[${utility.currentFileName}::onMounted()] route: `, toRaw(route));
});
</script>

<template>
  <div>
    <span>
      <h1>Page: Catch All</h1>

      <div class="route-attributes" v-for="routeKey in Object.keys(toRaw(route))" :key="routeKey">
        <strong>{{ routeKey }}</strong
        >: {{ route[routeKey] }}
      </div>
    </span>
  </div>
</template>

<style scoped>
.route-attributes {
  background: lightgray;
  border-radius: 5px;
  color: black;
  display: block;
  font-family: Verdana, Geneva, Tahoma, sans-serif;
  margin: 10px 0px;
  padding: 10px;
  text-align: left;
}
</style>
