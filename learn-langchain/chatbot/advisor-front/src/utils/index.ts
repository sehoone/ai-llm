import { isMobileApp, isObject } from '@/utils/is';
import type AppBridge from '@/utils/hybrid/index';
import { UtilNativeToWeb } from './hybrid/util/nativeToWeb';
import { EmulatorDevice } from './hybrid/emulator/device';
/**
 * Add the object as a parameter to the URL
 * @param baseUrl url
 * @param obj
 * @returns {string}
 * eg:
 *  let obj = {a: '3', b: '4'}
 *  setObjToUrlParams('www.baidu.com', obj)
 *  ==>www.baidu.com?a=3&b=4
 */
export function setObjToUrlParams(baseUrl: string, obj: Record<string, string>): string {
  let parameters = '';
  for (const key in obj) {
    parameters += key + '=' + encodeURIComponent(obj[key]) + '&';
  }
  parameters = parameters.replace(/&$/, '');
  return /\?$/.test(baseUrl) ? baseUrl + parameters : baseUrl.replace(/\/?$/, '?') + parameters;
}

export function deepMerge<T = any>(src: any = {}, target: any = {}): T {
  let key: string;
  for (key in target) {
    src[key] = isObject(src[key]) ? deepMerge(src[key], target[key]) : (src[key] = target[key]);
  }
  return src;
}

/**
 * get WebToNative 객체
 * @returns {Promise<AppBridge>}
 */
export async function getAppBridge(): Promise<AppBridge> {
  return new Promise((resolve) => {
    if (typeof (window as any)['$flex'] === 'object') {
      resolve((window as any)['$flex']);
    } else {
      const tm = window.setInterval(() => {
        if (typeof (window as any)['$flex'] === 'object') {
          window.clearInterval(tm);
          resolve((window as any)['$flex']);
        }
      }, 100);
    }
  });
}

/**
 * load NativeToWeb 객체
 * */
export function loadNativeToWebBridge() {
  const nativeToWeb = { ...UtilNativeToWeb };

  if (!(window as any)['$flex'].web) {
    (window as any)['$flex'].web = {};
  }

  if (typeof nativeToWeb === 'object') {
    // console.log('nativeToWeb', nativeToWeb);
    // console.log('nativeToWeb window', window);
    Object.assign((window as any)['$flex'].web, nativeToWeb);
  }

  return (window as any)['$flex'].web;
}

/**
 * Get Random Id
 * @returns {string}
 */
export function getRandomId() {
  const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz';
  const stringLength = 15;
  let randomstring = '';
  for (let i = 0; i < stringLength; i++) {
    const rnum = Math.floor(Math.random() * chars.length);
    randomstring += chars.substring(rnum, rnum + 1);
  }
  return randomstring;
}

/**
 * 개발용 브릿지 애뮬레이터 로드
 * PC환경일때만 로드. PC로 개발을 진행할때 브릿지를 사용하기 위함
 * @returns (window as any)['$flex']
 */
export function loadEmulWebToNativeBridge() {
  // mobile app이 아닌 pc환경에서만 로드
  if (!isMobileApp()) {
    const emulatorBridge = { ...EmulatorDevice };
    Object.defineProperty(window, '$flex', { value: {}, writable: true, enumerable: true, configurable: true });
    if (typeof emulatorBridge === 'object') {
      Object.assign((window as any)['$flex'], emulatorBridge);
    }
    return (window as any)['$flex'];
  }
}
