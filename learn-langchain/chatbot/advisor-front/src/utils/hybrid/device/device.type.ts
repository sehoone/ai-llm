import type { FlexRespone } from '../type/index';

// WebToNative request, reponse type 정의
export type DeviceInfoResponse = {
  osCd: string /** OS 종류	A: 안드로이드, I: 아이폰 */;
  uuId: string /** uuid */;
  requstId: string /** 요청id */;
} & FlexRespone;

export type DeviceInfoRequest = {
  requstId: string;
};
