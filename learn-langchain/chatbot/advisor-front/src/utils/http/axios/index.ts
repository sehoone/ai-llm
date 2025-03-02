/* eslint-disable @typescript-eslint/no-explicit-any */
import type { AxiosResponse } from 'axios';
import type { RequestOptions, Result } from './types/axios';
import type { AxiosTransform, CreateAxiosOptions } from './axiosTransform';
import { BaseAxios } from './baseAxios';
import { RequestEnum, ContentTypeEnum, ResultEnum } from './enum/httpEnum';
import { isString } from '@/utils/is';
import { deepMerge } from '@/utils';
import { formatRequestDate } from './helper';
import { useAuthStore } from '@/service/auth/authModule';
import { logger } from '@/utils/logger';
import { useI18n } from '@/composables/useI18n';
// import { useMessageModal } from '@/composables/useMessageModal';

/**
 * @description: AxiosTransform
 */
const transform: AxiosTransform = {
  /**
   * @description: transformResponseHook
   */
  transformResponseHook: (res: AxiosResponse<Result>, options: RequestOptions) => {
    logger.debug('transformResponseHook start');
    const { t } = useI18n();
    const { isReturnNativeResponse } = options;
    logger.debug('transformResponseHook ' + res);
    // 서버응답 그대로 처리(axios 응답을 포함한 응답)
    if (isReturnNativeResponse) {
      return res;
    }
    if (!res) {
      // logger.debug(t('system.api.networkException'));
      throw new Error(t('system.api.networkException'));
    }
    const data = res.data;
    const { rstCd, dta } = data;
    const hasSuccess = data && rstCd === ResultEnum.SUCCESS;

    if (hasSuccess) {
      return dta;
    }

    // const { createErrorModal } = useMessageModal();
    // createErrorModal(
    //   {
    //     title: t('system.api.errorMessage'),
    //     footer: [
    //       {
    //         name: 'close',
    //         label: 'Close',
    //         disabled: false
    //       }
    //     ]
    //   },
    //   errMsg || t('system.api.networkException')
    // );
    // TODO 실패 코드 응답 처리
    logger.debug('rstCd' + rstCd);
    logger.debug('transformResponseHook end');
    return data;
  },

  /**
   * @description: beforeRequestHook
   * 요청보내기 전 처리.
   */
  beforeRequestHook: (config, options) => {
    logger.debug('beforeRequestHook start');
    const { apiUrl, joinPrefix, joinParamsToUrl, formatDate, urlPrefix } = options;

    if (joinPrefix) {
      config.url = `${urlPrefix}${config.url}`;
    }
    if (apiUrl && isString(apiUrl)) {
      config.url = `${apiUrl}${config.url}`;
    }
    const params = config.params || {};
    const data = config.data || false;
    formatDate && data && !isString(data) && formatRequestDate(data);
    if (config.method?.toUpperCase() === RequestEnum.GET) {
      if (!isString(params)) {
        config.params = Object.assign(params || {});
      } else {
        config.url = config.url + params;
        config.params = undefined;
      }
    } else {
      if (!isString(params)) {
        formatDate && formatRequestDate(params);
        if (Reflect.has(config, 'data') && config.data && Object.keys(config.data).length > 0) {
          config.data = data;
          config.params = params;
        } else {
          config.data = params;
          config.params = undefined;
        }
        if (joinParamsToUrl) {
          /*
          config.url = setObjToUrlParams(
            config.url as string,
            Object.assign({}, config.params, config.data)
          );*/
        }
      } else {
        config.url = config.url + params;
        config.params = undefined;
      }
    }

    logger.debug('beforeRequestHook end');
    return config;
  },

  /**
   * @description: requestInterceptors
   */
  requestInterceptors: async (config, options) => {
    logger.debug('requestInterceptors start');

    // API인증정보 세팅. 인증정보는 브릿지를 통해서 가져옴
    const authStore = useAuthStore();
    let authInfo = authStore.getAuthInfo;
    if ((config as any).requestOptions?.withToken == true) {
      if (authInfo.token == '') {
        const resAuthInfo = await authStore.getAuthTokenAction();
        authInfo = resAuthInfo;
      }
      config.headers.Authorization = options.authenticationScheme
        ? `${options.authenticationScheme} ${authInfo.token}`
        : authInfo.token;

      // TODO 인터페이스 정의서 보고 수정
      config.headers['appCode'] = authInfo.appCode;
      config.headers['UUID'] = authInfo.uuId;
      config.headers['osKnd'] = authInfo.osKnd;
      config.headers['osVer'] = authInfo.osVer;
      config.headers['appVer'] = authInfo.appVer;
    }

    logger.debug('requestInterceptors end');
    return config;
  },

  /**
   * @description: responseInterceptors
   */
  responseInterceptors: (res: AxiosResponse<any>) => {
    logger.debug('responseInterceptors start');
    logger.debug('responseInterceptors end');
    return res;
  },

  /**
   * @description: responseInterceptorsCatch
   */
  responseInterceptorsCatch: (error: any) => {
    logger.debug('responseInterceptorsCatch start' + error);
    // TODO 실패응답 처리. ex. http 실패응답. 401, 403, 404, 500 등
    // const { t } = useI18n();
    const { code, message } = error || {};
    const err: string = error?.toString?.() ?? '';
    // let errMessage = '';

    try {
      if (code === 'ECONNABORTED' && message.indexOf('timeout') !== -1) {
        // errMessage = t('system.api.apiTimeoutMessage');
      }
      if (err?.includes('Network Error')) {
        // errMessage = t('system.api.networkExceptionMsg');
      }

      // TODO statue 별로 애러메세지 처리
      // const { createErrorModal } = useMessageModal();
      // createErrorModal(
      //   {
      //     title: t('system.api.errorMessage'),
      //     footer: [
      //       {
      //         name: 'close',
      //         label: 'Close',
      //         disabled: false
      //       }
      //     ]
      //   },
      //   errMessage || t('system.api.networkException')
      // );
    } catch (error) {
      throw new Error(error as unknown as string);
    }
    // alert('네트워크 오류 ' + error.message);
    logger.debug('responseInterceptorsCatch end');
    return Promise.reject(error);
  },

  requestCatchHook: (error: Error) => {
    logger.debug('requestCatchHook start');
    logger.debug('requestCatchHook end');
    // alert('네트워크 오류 ' + error.message);
    return Promise.reject(error);
    // }(e: Error, options: RequestOptions) => Promise<unknown>;
  }
};

/**
 * @description: axios 생성
 */
function createAxios(opt?: Partial<CreateAxiosOptions>) {
  return new BaseAxios(
    deepMerge(
      {
        authenticationScheme: 'Bearer',
        timeout: 10 * 1000,
        headers: { 'Content-Type': ContentTypeEnum.JSON },
        transform,
        baseURL: '/api',
        requestOptions: {
          joinPrefix: false,
          isReturnNativeResponse: false,
          isTransformResponse: true,
          joinParamsToUrl: false,
          formatDate: true,
          errorMessageMode: 'message',
          urlPrefix: 'api',
          joinTime: true,
          withToken: true
        }
      },
      opt || {}
    )
  );
}
/**
 * @description: defHttp
 * axios 디폴트 옵션으로 생성
 * ex. defHttp.get<HellowModel>({ url: Api.GetHellowWorld });
 */
export const defHttp = createAxios();

/**
 * @description: defHttpOpt
 * axios 커스텀 옵션으로 생성. 디폴트 설정에서 커스텀이 필요한 필드와 merge
 * ex. defHttpOpt({ timeout: 200 * 1000 }).get<HellowModel>({url: Api.GetHellowWorld,});
 */
export const defHttpOpt = (opt?: Partial<CreateAxiosOptions>): BaseAxios => createAxios(opt);
