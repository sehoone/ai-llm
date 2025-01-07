<template>
  <div class="home">
    <v-select :items="bridgeList" v-model="selectedBridge"></v-select>
    <v-text-field v-model="selectedBridge" label="interfaceName" placeholder="interfaceName"></v-text-field>
    <v-radio-group v-model="paramType" @change="changeParamType" row>
      <v-radio label="JSON type" value="json"></v-radio>
      <v-radio label="String type" value="string"></v-radio>
      <v-radio label="Number type" value="number"></v-radio>
    </v-radio-group>
    <v-text-field
      v-model="paramString"
      label="parameterString"
      placeholder="parameterString"
      v-show="isParamString"
    ></v-text-field>
    <BridgeParam :params="paramJson" v-show="!isParamString">
      <v-btn color="primary" @click="addParam()"> + </v-btn>
      <v-btn color="primary" @click="delParam()"> - </v-btn>
    </BridgeParam>
    <v-btn color="primary" @click="callBridge()"> call bridge </v-btn>
    <p>응답값:{{ result }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import BridgeParam, { type BridgeParams } from '@/views/sample/BridgeParam.vue';
// import flex from '@/utils/hybrid/index';
// import { DataTableHeader } from 'vuetify';
//import { FlexFunc } from 'flex-hybrid-app-scripts';

const defaultParam: BridgeParams = {
  key: 'key',
  value: 'value',
  inputKey: '',
  inputValue: ''
};

type DataTableHeader = {
  text: string;
  value: string;
  align?: 'start' | 'center' | 'end';
  sortable?: boolean;
  filterable?: boolean;
  groupable?: boolean;
  divider?: boolean;
  class?: string | string[];
  cellClass?: string | string[];
  width?: string | number;
  filter?: (value: any, search: string | null, item: any) => boolean;
};

let bridgeList: Array<DataTableHeader> = reactive([]);
let selectedBridge = ref('');
let paramType = ref('json');
let paramString = ref('');
let result = ref('');
let isParamString = ref(false);
let paramJson = reactive([defaultParam]);
// eslint-disable-next-line
    let bridge: any; 

// onMounted(async () => {
//   bridge = await flex;
//   let keys = Object.getOwnPropertyNames(bridge);
//   keys.forEach((key: string) => {
//     if (
//       key != 'version' &&
//       key != 'isMobile' &&
//       key != 'isAndroid' &&
//       key != 'isiOS' &&
//       key != 'isScript' &&
//       key != 'device' &&
//       key != 'addEventListener' &&
//       key != 'option' &&
//       key != 'web'
//     ) {
//       bridgeList.push({ text: key, value: key });
//     }
//   });
// });

/**
 * 브릿지 호출
 */
async function callBridge() {
  let key = selectedBridge.value;
  let param: string | number | { [key: string]: string };
  //let flex = $flex() as any;

  if (paramType.value == 'json') {
    let paramTemp: { [key: string]: string } = {};
    paramJson.forEach((value) => {
      paramTemp[value.inputKey] = value.inputValue;
    });

    param = paramTemp;
  } else if (paramType.value == 'number') {
    param = Number(paramString.value);
  } else {
    param = paramString.value;
  }

  try {
    result.value = await bridge[key](param);
  } catch (e) {
    alert('interface: ' + key + 'param: ' + param + '\n' + e);
  }
}

/**
 * radio 변경
 */
function changeParamType() {
  if (paramType.value == 'json') {
    isParamString.value = false;
  } else {
    isParamString.value = true;
  }
}

/**
 * 파라미터 추가
 */
function addParam() {
  const addParams: BridgeParams = {
    key: 'key',
    value: 'value',
    inputKey: '',
    inputValue: ''
  };
  paramJson.push(addParams);
}

/**
 * 파라미터 삭제
 */
function delParam() {
  if (paramJson.length == 1) {
    return;
  }

  paramJson.pop();
}
</script>

<script lang="ts">
export default {
  name: 'sampleBrigde',
  inheritAttrs: false,
  customOptions: {}
};
</script>
