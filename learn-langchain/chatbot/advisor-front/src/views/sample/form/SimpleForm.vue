<template>
  <Form @submit="handleSubmit" :validation-schema="schema" :initial-values="formValues">
    email: <Field name="email" type="email" />
    <ErrorMessage name="email" />
    password: <Field name="password" type="password" />
    <ErrorMessage name="password" />
    <button>Submit</button>
  </Form>
</template>
<script setup>
import { Form, Field, ErrorMessage } from 'vee-validate';
import * as yup from 'yup';

const schema = yup.object({
  email: yup.string().required().email(),
  password: yup.string().required().min(8)
});

// 초기값 설정. form에 :initial-values 속성을 사용하여 초기값을 설정
const formValues = {
  email: 'example@example.com',
  password: 'P@$$w0Rd'
};

function handleSubmit(values) {
  alert(JSON.stringify(values, null, 2));
}
</script>
