export type LocaleType = 'ko' | 'en';

export interface LocaleSetting {
  // Current language
  locale: LocaleType;
  // default language
  fallback: LocaleType;
  // available Locales
  availableLocales: LocaleType[];
}
