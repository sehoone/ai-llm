export type ErrorMessageMode = 'none' | 'modal' | 'message' | undefined;

// 요청 처리 옵션
export interface RequestOptions {
  // Splicing request parameters to url
  joinParamsToUrl?: boolean;
  // Format request parameter time
  formatDate?: boolean;
  // Whether to process the request result
  isTransformResponse?: boolean;
  // Whether to return native response headers
  // For example: use this attribute when you need to get the response headers
  isReturnNativeResponse?: boolean;
  // Whether to join url
  joinPrefix?: boolean;
  // Interface address, use the default apiUrl if you leave it blank
  apiUrl?: string;
  // URL prefix
  urlPrefix?: string;
  // Error message prompt type
  errorMessageMode?: ErrorMessageMode;
  // Whether to add a timestamp
  joinTime?: boolean;
  // Whether to send token in header
  withToken?: boolean;
}

// API response
export interface Result<T = unknown> {
  rstCd: string;
  dta: T;
  errMsg: string;
}
