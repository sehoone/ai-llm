<template>
  <div>
    <h1>Multi-step Form Wizard</h1>

    <FormWizard :validation-schema="validationSchema" @submit="onSubmit">
      <FormStep>
        <Field name="fullName" type="text" placeholder="Type your Full name" />
        <ErrorMessage name="fullName" />

        <Field name="email" type="email" placeholder="Type your email" />
        <ErrorMessage name="email" />
      </FormStep>

      <FormStep>
        <Field name="password" type="password" placeholder="Type a strong one" />
        <ErrorMessage name="password" />

        <Field name="confirmPass" type="password" placeholder="Confirm your password" />
        <ErrorMessage name="confirmPass" />
      </FormStep>

      <FormStep>
        <Field name="favoriteDrink" as="select">
          <option>Select a drink</option>
          <option value="coffee">Coffee</option>
          <option value="tea">Tea</option>
          <option value="soda">Soda</option>
        </Field>
        <ErrorMessage name="favoriteDrink" />
      </FormStep>
    </FormWizard>
  </div>
</template>

<script setup lang="ts">
import { Field, ErrorMessage } from 'vee-validate';
import * as yup from 'yup';
import FormWizard from './_components/FormWizerd.vue';
import FormStep from './_components/FormStep.vue';

// 유효성 체크를 위한 스키마
const validationSchema = [
  yup.object({
    fullName: yup.string().required().label('Full Name'),
    email: yup.string().required().email().label('Email Address')
  }),
  yup.object({
    password: yup.string().min(8).required(),
    confirmPass: yup
      .string()
      .required()
      .oneOf([yup.ref('password')], 'Passwords must match')
  }),
  yup.object({
    favoriteDrink: yup.string().required().oneOf(['coffee', 'tea', 'soda'], 'Choose a drink')
  })
];

/**
 * Only Called when the last step is submitted
 */
function onSubmit(formData: any) {
  console.log(JSON.stringify(formData, null, 2));
}
</script>

<style>
input,
select {
  margin: 10px 0;
  display: block;
}
</style>
