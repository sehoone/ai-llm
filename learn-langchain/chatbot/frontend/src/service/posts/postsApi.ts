import { defHttp } from '@/utils/http/axios';
import type { PostInfoModel, PostListModel } from '@/service/posts/model/postModel';

enum Api {
  posts = '/posts',
  postInfo = '/postInfo'
}

/**
 * @description: httpPosts
 */
export const httpPosts = (): Promise<PostListModel> => {
  return defHttp.get({
    url: Api.posts
  });
};

/**
 * @description: httpPostInfo
 */
export const httpPostInfo = (): Promise<PostInfoModel> => {
  return defHttp.get({
    url: Api.postInfo
  });
};
