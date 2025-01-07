/**
 * @description: 게시글 정보
 * PostInfoface
 */
export interface PostInfoModel {
  id: string;
  title: string;
  content: string;
  image: string;
  animals: string;
  author: string;
  createAt: Date | null;
}

export interface PostListModel {
  posts: Array<PostInfoModel>;
}
