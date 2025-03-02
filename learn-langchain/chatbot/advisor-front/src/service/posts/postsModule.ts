import { defineStore } from 'pinia';

import type { PostInfoModel } from '@/service/posts/model/postModel';
import { httpPostInfo, httpPosts } from '@/service/posts/postsApi';

interface postsState {
  posts: PostInfoModel[];
  isLodingPosts: boolean;
  isDonePosts: boolean;
  errorPosts: string | null;

  postInfo: PostInfoModel;
  isLodingPostInfo: boolean;
  isDonePostInfo: boolean;
  errorPostInfo: string | null;
}

export const postInfoInit = {
  id: '',
  title: '',
  content: '',
  image: '',
  animals: '',
  author: '',
  createAt: null
};

export const usePostStore = defineStore({
  id: 'post-store',

  state: (): postsState => ({
    posts: [],
    isLodingPosts: false,
    isDonePosts: false,
    errorPosts: null,

    postInfo: postInfoInit,
    isLodingPostInfo: false,
    isDonePostInfo: false,
    errorPostInfo: null
  }),

  getters: {
    getPosts(): PostInfoModel[] {
      // 데이터 가공
      return this.posts;
    },
    getPostInfo(): PostInfoModel {
      // 데이터 가공
      return this.postInfo;
    }
  },
  actions: {
    async setHttpPostsAction() {
      this.posts = [];
      this.isLodingPosts = true;
      this.isDonePosts = false;
      this.errorPosts = null;
      try {
        const res = await httpPosts();
        if (res) {
          if (res.posts) {
            this.posts = res.posts;
          }
        }
        this.isLodingPosts = false;
        this.isDonePosts = true;
        return res;
      } catch (error) {
        this.isLodingPosts = false;
        this.isDonePosts = false;
        this.errorPosts = '에러가 발생했습니다. #1';
        return Promise.reject(error);
      }
    },

    async setHttpPostInfoAction() {
      this.postInfo = postInfoInit;
      this.isLodingPostInfo = true;
      this.isDonePostInfo = false;
      this.errorPostInfo = null;
      try {
        const res = await httpPostInfo();
        if (res) {
          this.postInfo = res;
        }
        this.isLodingPostInfo = false;
        this.isDonePostInfo = true;
        return res;
      } catch (error) {
        this.isLodingPostInfo = false;
        this.isDonePostInfo = false;
        this.errorPostInfo = '에러가 발생했습니다. #1';
        return Promise.reject(error);
      }
    }
  }
});
