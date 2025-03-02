<template>
  <h1>
    {{ name }}
    <small>v.{{ version }}</small>
  </h1>
  <RouterLink v-for="pageNo in [0, 1, 2, 3, 4]" :key="pageNo" :to="getLink(pageNo)" class="link">
    {{ pageNo ? `Page ${pageNo}` : '/' }}
  </RouterLink>
  <router-view v-slot="{ Component }">
    <transition name="slide-fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { name, version } from '@/utils/constants/constants';

const getLink = (pageNo) => {
  // Note: pageNo 0 is the root page /
  return pageNo ? `/transition/page${pageNo}` : '/';
};
</script>

<style scoped>
h1 {
  /* Dynamically adjust font based on screen width */
  font-size: clamp(3rem, 5.3cqi, 7.5rem);
}

small {
  /* Font size base on parent's font size */
  font-size: 30%;
  font-style: italic;
}

.link {
  background-color: darkgreen;
  border: solid 1px darkgray;
  border-radius: 5px;
  color: white;
  cursor: pointer;
  padding: 10px;
  margin-right: 10px;
}

.link:hover {
  background-color: lightgreen;
  color: darkgreen;
}

/* Transition */
/* .fade-enter-active,
.fade-leave-active,
.slide-enter-active,
.slide-leave-active {
  transition:
    opacity 1s,
    transform 1s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateX(-30%);
} */
/* .slide-enter-active,
.slide-leave-active {
  transition: transform 0.5s;
}

.slide-enter {
  transform: translateX(100%);
}

.slide-leave-to {
  transform: translateX(-100%);
} */
.slide-fade-enter-active {
  transition: all 0.2s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.4s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-leave-to {
  transform: translateX(50px);
  opacity: 0;
}
.slide-fade-enter-from {
  transform: translateX(20px);
  opacity: 0;
}
</style>
