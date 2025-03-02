<template>
  <div class="home">
    <v-card>
      <v-card-text>
        <p>
          <b>Im child {{ title }}</b>
        </p>
        <p><b>props person1.name:</b>{{ person1.name }}</p>
        <p><b>props person1.age:</b>{{ person1.age }}</p>
        <p><b>props person1.computedNameLength:</b>{{ person1.computedNameLength }}</p></v-card-text
      >
      <v-btn color="primary" @click="handleClick">click child btn(print props data)</v-btn>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';
import { logger } from '@/utils/logger';
import { type person1Model } from '@/service/sample/model/compositionModel';
/*
type person1Type = {
  name: string;
  age: number;
  computedNameLength: number;
};
interface person1Type {
  name: string;
  age: number;
  computedNameLength: number;
}*/
const props = defineProps({
  person1: {
    type: Object as () => person1Model,
    required: true
  },
  title: {
    type: String,
    default: '제목'
  }
});

const handleClick = () => {
  logger.debug('print props data ' + JSON.stringify(props.person1));
};
</script>

<script lang="ts">
export default {
  name: 'samplePropsChild',
  inheritAttrs: false,
  customOptions: {}
};
</script>
