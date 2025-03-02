import { createApp } from 'vue';
import { createPinia } from 'pinia';

import App from './App.vue';
import router from './router';

// Vuetify
import 'vuetify/styles';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import { aliases, mdi } from 'vuetify/iconsets/mdi';
import '@mdi/font/css/materialdesignicons.css';
import './assets/scss/guide.scss';
import './assets/scss/style.scss';

import { setupI18n } from '@/locales/setupI18n';

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi
    }
  }
});

const app = createApp(App);

async function bootstrap() {
  app.use(createPinia());
  app.use(router);
  app.use(vuetify);
  await setupI18n(app);

  app.mount('#app');
}
bootstrap();
// app.use(createPinia());
// app.use(router);
// app.use(vuetify);
// setupI18n

// app.mount('#app');
