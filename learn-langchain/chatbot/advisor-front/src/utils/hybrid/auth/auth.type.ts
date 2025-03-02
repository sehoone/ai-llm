import type { FlexRespone } from '../type/index';

// 인증정보 응답
export type AuthInfoResponse = {
  token: string /** 인증토큰 */;
  uuId: string /** uuid */;
  appCode: string /** app코드 */;
  osKnd: string /** os종류 */;
  osVer: string /** os버전 */;
  appVer: string /** app버전 */;
} & FlexRespone;
