import type { FlexRespone } from '../type/index';

/** fileDownloadRequest */
export type FileDownloadRequest = {
  url: string;
  filename: string;
};
/** iframeOpenRequest */
export type IFrameOpenRequest = {
  url: string;
  title: string;
};
/** alertRequest */
export type AlertRequest = {
  title: string;
  message: string;
  buttons: Array<string>;
};
/** fileDownload */
export type FileDownloadResponse = {
  isSuccess: boolean;
} & FlexRespone;
/** alert */
export type AlertResponse = {
  selected: number;
} & FlexRespone;

export type PushMessageResponse = {
  messageTargetId: number;
  noticeParam: string;
  categoryName: string;
} & FlexRespone;
