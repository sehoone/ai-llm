// import type { CallBackFunction } from '.';
import type { InputEncKeypadRequest } from './nativeToWeb.type';

// NativeToWeb interFace 구현부
export const UtilNativeToWeb = {
  webViewBack: () => {
    window.dispatchEvent(new CustomEvent('webViewBack'));
    return {
      response: {
        code: 0,
        message: 'OK'
      }
    };
  },
  inputEncKeypad: (inputEncKeypadRequest: InputEncKeypadRequest) => {
    window.dispatchEvent(new CustomEvent('inputEncKeypad', { detail: inputEncKeypadRequest }));
    return {
      response: {
        code: 0,
        message: 'OK'
      }
    };
  }
  /* add function */
};
