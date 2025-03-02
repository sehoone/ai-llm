import type { FlexRespone } from '../type';
import type { DeviceInfoRequest, DeviceInfoResponse } from './device.type';

// WebToNative interface 정의
export default interface FlexDevice {
  deviceInfo: (param: DeviceInfoRequest) => Promise<DeviceInfoResponse>;
  exit: () => Promise<FlexRespone>;
}
