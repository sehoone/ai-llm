/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Data processing class, can be configured according to the project
 */
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { RequestOptions, Result } from './types/axios';

export interface CreateAxiosOptions extends AxiosRequestConfig {
  authenticationScheme?: string;
  transform?: AxiosTransform;
  requestOptions?: RequestOptions;
}

export abstract class AxiosTransform {
  /**
   * @description: Request 보내기전 처리. axios 호출하기전(axios request 인터셉터 보다 이전상태)
   * Request 전에 파라메터 생성 및 axios설정
   */
  beforeRequestHook?: (config: AxiosRequestConfig, options: RequestOptions) => AxiosRequestConfig;

  /**
   * @description: Request 성공 후, 응답 데이터 처리.(axios response 인터셉터 호출된 이후 처리)
   * Request 성공 후, 공통 성공/실패 처리 및 데이터 포맷
   */
  transformResponseHook?: (res: AxiosResponse<Result>, options: RequestOptions) => any;

  /**
   * @description: Request 실패 처리. axios http 실패
   */
  requestCatchHook?: (e: Error, options: RequestOptions) => Promise<unknown>;

  /**
   * @description: Request 인터셉터
   */
  requestInterceptors?: (
    config: InternalAxiosRequestConfig,
    options: CreateAxiosOptions
  ) => Promise<InternalAxiosRequestConfig>;

  /**
   * @description: Response 인터셉터
   */
  responseInterceptors?: (res: AxiosResponse<unknown>) => AxiosResponse<unknown>;

  /**
   * @description: response InterceptorsCatch(인터셉터에서 exception이 발생했을때 처리)
   */
  responseInterceptorsCatch?: (axiosInstance: AxiosInstance, error: Error) => void;
}
