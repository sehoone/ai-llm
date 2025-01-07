<template>
  <div>
    <v-card>
      <v-card-text>
        <p>정적값 common.okText: {{ t('common.okText') }}</p></v-card-text
      >
      <v-card-text
        ><p>정적값 common.closeText: {{ t('common.closeText') }}</p></v-card-text
      >
      <v-card-text
        ><p>정적값 routes.login: {{ t('routes.basic.login') }}</p></v-card-text
      >
      <v-card-text
        ><p>동적값 Welcome, {name}!: {{ welcomeMessage }}</p></v-card-text
      >
    </v-card>

    <br />
    <v-col class="py-2" cols="12">
      <v-select
        :items="localeList"
        v-model="selectedLocale"
        label="Select Role"
        @update:modelValue="updateLocale"
      ></v-select>
    </v-col>
  </div>
</template>

<script setup lang="ts">
import type { LocaleType } from '@/service/locale/model/localeModel';
import { computed, ref, unref } from 'vue';
import { useI18n } from '@/composables/useI18n';
import { useLocale } from '@/locales/useLocale';
const { changeLocale, getLocale } = useLocale();
const { t } = useI18n();

const localeList = [
  {
    title: '한글',
    value: 'ko'
  },
  {
    title: '영어',
    value: 'en'
  }
];
const selectedLocale = ref('');
selectedLocale.value = unref(getLocale);
async function updateLocale(lang: LocaleType | string) {
  await changeLocale(lang as LocaleType);
}

const name = 'sehoone';
const welcomeMessage = computed((): string => t('common.welcomeMessageAndName', { name: name }));
</script>

<script lang="ts">
export default {
  name: 'multiLanguage',
  inheritAttrs: false,
  customOptions: {}
};
</script>
