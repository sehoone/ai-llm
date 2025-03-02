<template>
  <div>
    <v-card>
      <div @click="onClickCallKeypad">
        <v-text-field
          label="Label1"
          v-model="inputValue"
          @blur="onClickCloseKeypad()"
          @input="handleInput(1)"
          @focus="handleFocus($event)"
          ref="input1"
        ></v-text-field>
        <v-text-field
          label="Label2"
          v-model="inputValue"
          @blur="onClickCloseKeypad()"
          @input="handleInput(2)"
          @focus="handleFocus($event)"
          ref="input2"
        ></v-text-field>
        <v-text-field
          label="Label3"
          v-model="inputValue"
          @blur="onClickCloseKeypad()"
          @input="handleInput(3)"
          @focus="handleFocus($event)"
          ref="input3"
        ></v-text-field>
      </div>
    </v-card>
    <v-card>
      <!-- 유효한숫자만 입력 가능하도록 설정. 
       input type number로 해도 되지만 0001 과 같은 유효하지 않는 숫자는 그대로 노출됨 -->
      <input type="text" v-model="inputNum" @input="validateInputNumber" />
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue';

const inputValue = ref('');
const input1 = ref();
const input2 = ref();
const input3 = ref();
const onClickCallKeypad = () => {
  // console.log('Keypad is Call');
};
const inputNum = ref('0');

const programmaticFocusChange = ref(false);

const onClickCloseKeypad = () => {
  // 포커스 변경이 프로그래밍 방식으로 발생하는 경우를 처리
  if (programmaticFocusChange.value) {
    programmaticFocusChange.value = false; // 상태를 초기화하고 핸들러 실행을 건너뜁니다.
    return;
  }
  // console.log('Keypad is close');
};
const handleInput = (inputNumber: number) => {
  // 입력 값에 따라 다음 입력 필드로 포커스 이동
  if (inputValue.value.length >= 3 && inputNumber === 1) {
    programmaticFocusChange.value = true;
    input2.value.focus();
  } else if (inputValue.value.length >= 6 && inputNumber === 2) {
    programmaticFocusChange.value = true;
    input3.value.focus();
  }
};
const handleFocus = async (event: FocusEvent) => {
  // 포커스 이동이 프로그래밍 방식으로 발생하는 경우를 처리
  await nextTick(); // DOM 업데이트를 기다림. 이 부분이 없으면 포커스가 변경되지 않음
  if (event.target instanceof HTMLElement) {
    event.target.blur();
  }
};

/**
 * 입력 값이 숫자인지 확인하고, 숫자가 아닌 문자는 제거.
 * watch를 사용하면 model만 업데이트 되고 사용자한테는 0001과 같은 유효하지 않은 숫자가 그대로 보임
 * @param event
 */
const validateInputNumber = (event: Event) => {
  const input = event.target as HTMLInputElement;
  // 숫자만 포함된 문자열로 입력 값을 대체합니다.
  let value = input.value.replace(/\D/g, '');
  // 입력 값이 숫자인 경우, parseInt를 사용하여 앞에 붙은 0을 제거합니다.
  // 그리고 다시 문자열로 변환하여 v-model에 반영합니다.
  if (value) {
    value = String(parseInt(value, 10));
  }
  inputNum.value = value;
};
</script>

<style scoped></style>
