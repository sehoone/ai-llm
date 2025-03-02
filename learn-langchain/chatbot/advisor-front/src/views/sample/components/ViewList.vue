<template>
  <v-list>
    <!-- <v-list-item v-for="item in items" :key="item.id">
      <p>{{ item.title }}</p>
      
    </v-list-item> -->

    <v-list-item v-for="item in items" :key="item.id">
      <template #title
        ><a @click="readItem(item.id)">{{ item.title }}</a>
        <v-btn icon @click="onClickEditBtn(item.id)">
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
        <v-btn icon @click="onClickReadBtn(item.id)">
          <v-icon>mdi-home</v-icon>
        </v-btn></template
      >
      <template #subtitle>
        <div v-text="item.content"></div>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';

import { logger } from '@/utils/logger';
import type { PostInfoModel } from '@/service/posts/model/postModel';

const props = defineProps({
  items: {
    type: Array as () => PostInfoModel[],
    required: true
  },
  isLoadingPostItems: {
    type: Boolean,
    required: true
  },
  donePostItems: {
    type: Boolean,
    required: true
  },
  onClickMoreBtn_: {
    type: Function,
    required: true
  },
  onClickEditBtn_: {
    type: Function,
    required: true
  },
  onClickReadBtn_: {
    type: Function,
    required: true
  }
});

const readItem = (id: string) => {
  return props.onClickReadBtn_(id);
};

// async function onClickMoreBtn() {
//   props.onClickMoreBtn_();
// }
function onClickEditBtn(id: string) {
  props.onClickEditBtn_(id);
}
function onClickReadBtn(id: string) {
  props.onClickReadBtn_(id);
}

onMounted(() => {
  logger.debug('mounted viewList');
});
onUnmounted(() => {
  logger.debug('unmounted viewList');
});
</script>
