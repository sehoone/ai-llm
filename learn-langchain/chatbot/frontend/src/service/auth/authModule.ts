import { defineStore } from 'pinia';

import type { AuthInfoInterface } from '@/service/auth/model/authModel';
import { getAppBridge } from '@/utils';

interface authState {
  authInfo: AuthInfoInterface;
}

export const AuthInfoInit = {
  token: '',
  uuId: '',
  appCode: '',
  osKnd: '',
  osVer: '',
  appVer: ''
};

export const useAuthStore = defineStore({
  id: 'auth-store',

  state: (): authState => ({
    authInfo: AuthInfoInit
  }),

  getters: {
    getIsLogin(): boolean {
      if (this.authInfo.token.length > 1) {
        return true;
      }
      return false;
    },
    getToken(): string {
      return this.authInfo.token;
    },
    getAuthInfo(): AuthInfoInterface {
      return this.authInfo;
    }
  },
  actions: {
    async getAuthTokenAction() {
      const appBridge = await getAppBridge();
      const resAuthInfo = await appBridge.authInfo();
      this.authInfo.token = resAuthInfo.token;
      this.authInfo.uuId = resAuthInfo.uuId;
      this.authInfo.appCode = resAuthInfo.appCode;
      this.authInfo.osKnd = resAuthInfo.osKnd;
      this.authInfo.osVer = resAuthInfo.osVer;
      this.authInfo.appVer = resAuthInfo.appVer;

      return resAuthInfo;
    }
  }
});
