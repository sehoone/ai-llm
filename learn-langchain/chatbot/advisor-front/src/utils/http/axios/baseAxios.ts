import type { AxiosRequestConfig, AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { RequestOptions, Result } from './types/axios';
import type { CreateAxiosOptions } from './axiosTransform';
import axios from 'axios';
import qs from 'qs';
import { isFunction } from '@/utils/is';
import { cloneDeep } from 'lodash-es';
import { ContentTypeEnum, RequestEnum } from './enum/httpEnum';
import { logger } from '@/utils/logger';

/**
 * @description: axios module
 * 1. axios instance 생성(BaseAxios)
 * 2. beforeRequestHook: 요청보내기 전 처리
 * 3. requestInterceptors: 요청 인터셉터
 * 5. responseInterceptors: 응답 인터셉터
 * 6. responseInterceptorsCatch: 5번에서 실패시 처리. 애러메세지 처리
 * 7. transformResponseHook: 응답 데이터 처리
 */
export class BaseAxios {
  private axiosInstance: AxiosInstance;
  private readonly options: CreateAxiosOptions;

  constructor(options: CreateAxiosOptions) {
    this.options = options;
    this.axiosInstance = axios.create(options);
    this.setupInterceptors();
  }

  private getTransform() {
    const { transform } = this.options;
    return transform;
  }

  getAxios(): AxiosInstance {
    return this.axiosInstance;
  }

  /**
   * @description: interceptor SETUP
   */
  private setupInterceptors() {
    const transform = this.getTransform();
    if (!transform) {
      return;
    }
    const { requestInterceptors, responseInterceptors, responseInterceptorsCatch } = transform;

    // Request interceptor configuration processing
    this.axiosInstance.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
      if (requestInterceptors && isFunction(requestInterceptors)) {
        config = await requestInterceptors(config, this.options);
      }
      logger.debug('request interceptor');
      return config;
    }, undefined);

    // Response result interceptor processing
    this.axiosInstance.interceptors.response.use((res: AxiosResponse<unknown>) => {
      if (responseInterceptors && isFunction(responseInterceptors)) {
        res = responseInterceptors(res);
      }
      return res;
    }, undefined);

    // Response result interceptor error capture
    responseInterceptorsCatch &&
      isFunction(responseInterceptorsCatch) &&
      this.axiosInstance.interceptors.response.use(undefined, (error) => {
        return responseInterceptorsCatch(this.axiosInstance, error);
      });
  }

  // support form-data
  supportFormData(config: AxiosRequestConfig): CreateAxiosOptions {
    const headers = config.headers || this.options.headers;
    const contentType = headers?.['Content-Type'] || headers?.['content-type'];

    if (
      contentType !== ContentTypeEnum.FORM_URLENCODED ||
      !Reflect.has(config, 'data') ||
      config.method?.toUpperCase() === RequestEnum.GET
    ) {
      return config;
    }

    return {
      ...config,
      data: qs.stringify(config.data, { arrayFormat: 'brackets' })
    };
  }

  /**
   * @description: axios http 통신(GET)
   */
  get<T = unknown>(config: AxiosRequestConfig, options?: RequestOptions): Promise<T> {
    logger.debug('get');
    return this.request({ ...config, method: 'GET' }, options);
  }

  /**
   * @description: axios http 통신(POST)
   */
  post<T = unknown>(config: AxiosRequestConfig, options?: RequestOptions): Promise<T> {
    return this.request({ ...config, method: 'POST' }, options);
  }

  /**
   * @description: axios http 통신(PUT)
   */
  put<T = unknown>(config: AxiosRequestConfig, options?: RequestOptions): Promise<T> {
    return this.request({ ...config, method: 'PUT' }, options);
  }

  /**
   * @description: axios http 통신(DELETE)
   */
  delete<T = unknown>(config: AxiosRequestConfig, options?: RequestOptions): Promise<T> {
    return this.request({ ...config, method: 'DELETE' }, options);
  }

  /**
   * @description: axios common http 통신
   */
  request<T = unknown>(config: AxiosRequestConfig, options?: RequestOptions): Promise<T> {
    // 1. axios config 설정
    let conf: CreateAxiosOptions = cloneDeep(config);
    const transform = this.getTransform();
    const { requestOptions } = this.options;
    const opt: RequestOptions = Object.assign({}, requestOptions, options);

    const { beforeRequestHook = (conf: AxiosRequestConfig) => conf, transformResponseHook } = transform || {};

    conf = beforeRequestHook(conf, opt);
    conf.requestOptions = opt;
    conf = this.supportFormData(conf);

    // 2. axios request 처리
    return new Promise((resolve, reject) => {
      this.axiosInstance
        .request<unknown, AxiosResponse<Result>>(conf)
        .then((res: AxiosResponse<Result>) => {
          if (transformResponseHook && isFunction(transformResponseHook)) {
            try {
              // 2-1 axois request 성공 후 처리(응답 데이터 처리 및 실패 응답처리)
              const ret = transformResponseHook(res, opt);
              resolve(ret);
            } catch (err) {
              reject(err || new Error('request error!'));
            }
            return;
          }
          resolve(res as unknown as Promise<T>);
        })
        .catch((e: Error | AxiosError) => {
          // axois request 실패
          // if (requestCatchHook && isFunction(requestCatchHook)) {
          //   logger.debug('requestCatchHook2');
          //   reject(requestCatchHook(e, opt));
          //   return;
          // }
          reject(e);
        });
    });
  }
}
