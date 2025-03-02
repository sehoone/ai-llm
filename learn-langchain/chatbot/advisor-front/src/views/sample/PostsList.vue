<template>
  <div>
    <div>
      <h4>
        POSTS 목록 페이지
        <button @click="onClcikRefresh">새로고침</button>
        &nbsp;&nbsp;
        <button @click="onClickCreate">새글작성</button>
      </h4>
    </div>

    <!-- -->
    <viewList
      :items="state.posts"
      :isLoadingPostItems="postStore.isLodingPosts"
      :donePostItems="postStore.isDonePosts"
      :onClickMoreBtn_="actionMore"
      :onClickEditBtn_="actionEdit"
      :onClickReadBtn_="actionRead"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { cloneDeep } from 'lodash-es';

import viewList from '@/views/sample/components/ViewList.vue';
import { usePostStore } from '@/service/posts/postsModule';
import { logger } from '@/utils/logger';
import type { PostInfoModel } from '@/service/posts/model/postModel';

interface stateType {
  posts: PostInfoModel[];
}

/* request, prepare, on, cb, action */
const router = useRouter();
const route = useRoute();
const postStore = usePostStore();
const state: stateType = reactive({ posts: [] });

async function requestApiHttpPosts() {
  const resResult = await postStore.setHttpPostsAction();
  if (resResult) {
    prepareData();
  }
}

function prepareData() {
  const items = postStore.getPosts;
  if (items.length > 0) {
    const posts_ = cloneDeep(items);
    /*
          데이터 가공 영역
        */
    state.posts = posts_;
  }
}

async function actionMore() {
  logger.debug('postsList actionMore');
}
function actionEdit() {
  logger.debug('postsList actionEdit');
}
function actionRead(id: string) {
  alert('read ' + id);
  router.push({
    path: `/sample/postsDetail/${id}`,
    query: { ...route.query }
  });
}

function onClcikRefresh() {
  requestApiHttpPosts();
}
function onClickCreate() {
  router.push({
    path: '/posts-create',
    query: { ...route.query }
  });
}

onMounted(() => {
  logger.debug('mounted postsList');
  requestApiHttpPosts();
  logger.debug('process.env.TEST_VALUE1', import.meta.env.VITE_TEST_VALUE1);
});
onUnmounted(() => {
  logger.debug('unmounted postsList');
});
</script>
