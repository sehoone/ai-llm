import { Screen } from 'vuetify';

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $screen: Screen;
  }
}
