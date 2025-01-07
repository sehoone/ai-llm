/**
 * @description: 인증 API
 * AuthInterface
 */
export interface AuthInfoInterface {
  token: string; // 인증토큰
  uuId: string; // UUID
  appCode: string; // app코드. MIC
  osKnd: string; // os종류. A: Android, I: iOS
  osVer: string; // os버전
  appVer: string; // app버젼
}

/**
 * @description: 토큰 API 응답
 * AuthResponseInterface
 */
// export interface AuthResponseInterface extends HttpResponseInterface {
//   result: AuthInterface;
// }
