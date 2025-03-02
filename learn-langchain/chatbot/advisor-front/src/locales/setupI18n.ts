import type { App } from 'vue';
import type { I18nOptions } from 'vue-i18n';

import { createI18n } from 'vue-i18n';
import { useLocaleStore } from '@/service/locale/localeModule';
import type { LocaleSetting, LocaleType } from '@/service/locale/model/localeModel';

const LOCALE: { [key: string]: LocaleType } = {
  KO: 'ko',
  EN: 'en'
};

const localeSetting: LocaleSetting = {
  // Locale
  locale: LOCALE.KO,
  // Default locale
  fallback: LOCALE.KO,
  // available Locales
  availableLocales: [LOCALE.KO, LOCALE.EN]
};

export let i18n: ReturnType<typeof createI18n>;

async function createI18nOptions(): Promise<I18nOptions> {
  const localeStore = useLocaleStore();
  const locale = localeStore.getLocale;
  const defaultLocal = await import(`./lang/${locale}.ts`);
  const message = defaultLocal.default?.message ?? {};

  return {
    legacy: false,
    locale,
    fallbackLocale: localeSetting.fallback,
    messages: {
      [locale]: message
    },
    availableLocales: localeSetting.availableLocales,
    sync: true, //If you don’t want to inherit locale from global scope, you need to set sync of i18n component option to false.
    silentTranslationWarn: true, // true - warning off
    missingWarn: false,
    silentFallbackWarn: true
  };
}

// setup i18n instance with glob
export async function setupI18n(app: App) {
  const options = await createI18nOptions();
  i18n = createI18n(options);
  app.use(i18n);
}
