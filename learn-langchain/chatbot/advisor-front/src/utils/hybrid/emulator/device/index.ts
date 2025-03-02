// import type { CallBackFunction } from '.';

// NativeToWeb interFace 구현부
export const EmulatorDevice = {
  // deviceInfo: {
  //   value: function (param: any) {
  //     return BrowserTest.deviceInfo(param);
  //   }
  // }
  deviceInfo: function (param: any) {
    return BrowserTest.deviceInfo(param);
  },
  authInfo: function () {
    return BrowserTest.authInfo();
  }
  /* add function */
};
const BrowserTest = {
  deviceInfo: async (param: any) => {
    return {
      osCd: 'A',
      uuId: 'TEST_UUID',
      requstId: param.requstId,
      response: {
        code: 0,
        message: 'OK'
      }
    };
  },
  authInfo: async () => {
    return {
      token: 'tokendkdkdkdkdkdk',
      uuId: 'TEST_UUID',
      appCode: 'MIC',
      osKnd: 'A',
      osVer: '11.0.0',
      appVer: '1.0.0',
      response: {
        code: 0,
        message: 'OK'
      }
    };
  }
};
