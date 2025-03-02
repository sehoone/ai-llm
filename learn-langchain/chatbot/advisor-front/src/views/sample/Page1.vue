<template>
  <div>
    <h1 ref="title">111</h1>
    <div>
      <h1>222</h1>
    </div>
  </div>
</template>

<script>
export default {
  mounted() {
    this.$refs.title.innerText = this.$options.__file.split('/').pop();
  }
};
</script>
