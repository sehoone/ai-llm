import type { FlexRespone } from '../type';
import type { AuthInfoResponse } from './auth.type';

// auth interface 정의
export default interface FlexAuth {
  authInfo: () => Promise<AuthInfoResponse>;
  exit: () => Promise<FlexRespone>;
}
