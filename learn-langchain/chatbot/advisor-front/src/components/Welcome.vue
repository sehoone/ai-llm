<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <div class="text-center">
          <h2 class="text-h2">
            {{ $t('welcomeTo') }} <span class="text-primary">{{ runtimeConfig.public.appName }}</span>
          </h2>
          <p class="text-caption my-5">
            {{ runtimeConfig.public.appName }} {{ $t('routes.basic.welcomeScreen.introduction1') }}
            <br />
          </p>
        </div>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12" md="10" offset-md="1">
        <v-row>
          <v-col cols="12" md="4">
            <v-row>
              <v-col>
                <div class="d-flex flex-column align-center">
                  <v-icon icon="sunny"></v-icon>
                  <h3 class="text-h6">{{ $t('routes.basic.welcomeScreen.examples.title') }}</h3>
                </div>
              </v-col>
            </v-row>
            <WelcomeCard v-for="example in examples" :content="example" />
          </v-col>
          <v-col cols="12" md="4">
            <v-row>
              <v-col>
                <div class="d-flex flex-column align-center">
                  <v-icon icon="bolt"></v-icon>
                  <h3 class="text-h6">{{ $t('routes.basic.welcomeScreen.capabilities.title') }}</h3>
                </div>
              </v-col>
            </v-row>
            <WelcomeCard v-for="capabilitie in capabilities" :content="capabilitie" />
          </v-col>
          <v-col cols="12" md="4">
            <v-row>
              <v-col>
                <div class="d-flex flex-column align-center">
                  <v-icon icon="warning_amber"></v-icon>
                  <h3 class="text-h6">{{ $t('routes.basic.welcomeScreen.limitations.title') }}</h3>
                </div>
              </v-col>
            </v-row>
            <WelcomeCard v-for="limitation in limitations" :content="limitation" />
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue';
import WelcomeCard from '@/components/WelcomeCard.vue';
import { useRuntimeConfig } from '@/composables/useRuntimeConfig';
import { useI18n } from '@/composables/useI18n';
const { t } = useI18n();
const runtimeConfig = useRuntimeConfig();
const examples = ref([
  t('routes.basic.welcomeScreen.examples.item1'),
  t('routes.basic.welcomeScreen.examples.item2'),
  t('routes.basic.welcomeScreen.examples.item3')
]);
const capabilities = ref([
  t('routes.basic.welcomeScreen.capabilities.item1'),
  t('routes.basic.welcomeScreen.capabilities.item2'),
  t('routes.basic.welcomeScreen.capabilities.item3')
]);
const limitations = ref([
  t('routes.basic.welcomeScreen.limitations.item1'),
  t('routes.basic.welcomeScreen.limitations.item2'),
  t('routes.basic.welcomeScreen.limitations.item3')
]);
</script>
