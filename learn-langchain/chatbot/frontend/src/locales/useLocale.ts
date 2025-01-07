/**
 * Multi-language related operations
 */
import type { LocaleType } from '@/service/locale/model/localeModel';

import { i18n } from './setupI18n';
import { useLocaleStore } from '@/service/locale/localeModule';
import { unref, computed } from 'vue';

interface LangModule {
  message: String;
}

function setI18nLanguage(locale: LocaleType) {
  const localeStore = useLocaleStore();

  if (i18n.mode === 'legacy') {
    i18n.global.locale = locale;
  } else {
    (i18n.global.locale as any).value = locale;
  }

  localeStore.setLocaleInfo({ locale });
}

export function useLocale() {
  const localeStore = useLocaleStore();
  const getLocale = computed(() => localeStore.getLocale);

  // Switching the language will change the locale of useI18n
  // And submit to configuration modification
  async function changeLocale(locale: LocaleType) {
    const globalI18n = i18n.global;
    const currentLocale = unref(globalI18n.locale);
    if (currentLocale === locale) {
      return locale;
    }

    const langModule = ((await import(`./lang/${locale}.ts`)) as any).default as LangModule;
    if (!langModule) return;

    const { message } = langModule;

    globalI18n.setLocaleMessage(locale, message);

    setI18nLanguage(locale);
    return locale;
  }

  return {
    getLocale,
    changeLocale
  };
}
