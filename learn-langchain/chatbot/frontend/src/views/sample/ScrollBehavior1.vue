<template>
  <div>
    <v-list-item v-for="item in items" :key="item.id">
      <template #title
        ><a>{{ item.title }}</a>
        <v-btn icon @click="onClickGoNextPage()">
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </template>
    </v-list-item>
  </div>
</template>

<script setup lang="ts">
import { logger } from '@/utils/logger';
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
interface ItemType {
  id: number;
  title: string;
}

const items = ref([] as ItemType[]);
onMounted(() => {
  logger.debug('mounted sampleScrollBehavior1');
  initItems();
});

const initItems = () => {
  for (let i = 0; i < 50; i++) {
    items.value.push({ id: i, title: `title${i}` });
  }
};

const onClickGoNextPage = () => {
  router.push({ path: '/sample/scroll-behavior2' });
};
</script>

<style scoped></style>
