const toString = Object.prototype.toString;

export function is(val: unknown, type: string): boolean {
  return toString.call(val) === `[object ${type}]`;
}

export function isObject(val: unknown): val is Record<string | number | symbol, unknown> {
  return val !== null && is(val, 'Object');
}

export function isString(val: unknown): val is string {
  return is(val, 'String');
}

// eslint-disable-next-line @typescript-eslint/ban-types
export function isFunction(val: unknown): val is Function {
  return typeof val === 'function';
}

/**
 * 모바일APP 여부
 * @returns {boolean}
 */
export function isMobileApp(): boolean {
  const userAgent = window.navigator.userAgent.toLowerCase();
  if (/appName/i.test(userAgent)) {
    return true;
  }
  return false;
}
