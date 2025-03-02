// import type { FlexRespone } from '../type/index';
import type { AlertRequest, AlertResponse } from './etc.type';

// WebToNative interface 정의
export default interface FlexEtc {
  // alert
  alert: (param: AlertRequest) => Promise<AlertResponse>;
}
