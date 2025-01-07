import { genMessage } from '../helper';

const modules = import.meta.glob('./ko/**/*.{json,ts,js}', { eager: true });
export default {
  message: {
    ...genMessage(modules as Record<string, Record<string, any>>, 'ko')
  },
  dateLocale: null,
  dateLocaleName: 'ko'
};
