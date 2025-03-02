import { genMessage } from '../helper';

const modules = import.meta.glob('./en/**/*.{json,ts,js}', { eager: true });
export default {
  message: {
    ...genMessage(modules as Record<string, Record<string, any>>, 'en')
  },
  dateLocale: null,
  dateLocaleName: 'en'
};
