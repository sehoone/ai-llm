<template>
  <v-app>
    <sample-app-bar-layout />
    <v-main>
      <v-container>
        <!-- vue transition 효과는 부모에 router view에 넣어야됨. 부모의 부모면은 동작안함. 그리고 적용될 화면은 하나의 root div가 필요함-->
        <router-view v-slot="{ Component }">
          <transition :name="transitionName" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue';
import SampleAppBarLayout from './SampleAppBarLayout.vue';
import { isBack } from '@/router/routerGuardConfig';

const transitionName = ref('slide-left');

watch(isBack, () => {
  nextTick(() => {
    if (isBack.value) {
      transitionName.value = 'slide-right';
    } else {
      transitionName.value = 'slide-left';
    }
  });
});
</script>

<style scoped>
/* .slide-fade-enter-active {
  transition: all 0.1s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.1s cubic-bezier(1, 0.5, 0.8, 1);
}
.slide-fade-leave-to {
  transform: translateX(50px);
  opacity: 0;
}
.slide-fade-enter-from {
  transform: translateX(20px);
  opacity: 0;
} */
/* .fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter,
.fade-leave-to {
  opacity: 0;
} */
.slide-left-enter-active,
.slide-right-leave-active {
  transition: all 0.3s ease;
}

.slide-left-leave-active,
.slide-right-enter-active {
  transition: all 0.3s ease;
}

.slide-left-enter,
.slide-right-leave-to {
  transform: translateX(100%);
}

.slide-left-leave-to,
.slide-right-enter {
  transform: translateX(-100%);
}
</style>
