import type { LocaleSetting, LocaleType } from '@/service/locale/model/localeModel';
import { LocalStorageKey } from '@/utils/constants/globalConstants';
import { useStorage } from '@vueuse/core';

import { defineStore } from 'pinia';

export const localeStateInit = {
  locale: 'ko' as LocaleType,
  fallback: 'ko' as LocaleType,
  availableLocales: ['ko', 'en'] as LocaleType[]
};

const lsLocaleSetting = useStorage(LocalStorageKey.APP_LOCALE, localeStateInit).value;

interface LocaleState {
  localInfo: LocaleSetting;
}

export const useLocaleStore = defineStore({
  id: 'locale-store',
  state: (): LocaleState => ({
    localInfo: lsLocaleSetting
  }),
  getters: {
    getLocale(state): LocaleType {
      return state.localInfo?.locale ?? 'ko';
    }
  },
  actions: {
    /**
     * Set up setLocaleInfo
     * @param info multilingual info
     */
    setLocaleInfo(info: Partial<LocaleSetting>) {
      this.localInfo = { ...this.localInfo, ...info };
      const localStorageAppLocale = useStorage(LocalStorageKey.APP_LOCALE, localeStateInit);
      localStorageAppLocale.value = this.localInfo;
    },
    /**
     * Initialize multilingual information and load the existing configuration from the local cache
     */
    initLocale() {
      this.setLocaleInfo({
        ...this.localInfo
      });
    }
  }
});
