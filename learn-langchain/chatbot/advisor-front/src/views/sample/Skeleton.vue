<template>
  <div class="card">
    <div class="card__image">
      <Skeletor height="200" />
    </div>

    <div class="card__slim">
      <div class="card__avatar">
        <Skeletor circle size="48" class="post__avatar" />
      </div>

      <div class="card__meta">
        <h2>
          <Skeletor width="50%" />
        </h2>

        <p>
          <Skeletor width="75%" />
        </p>
      </div>
    </div>

    <div class="card__text">
      <Skeletor v-for="i in 5" :key="i" />
    </div>

    <div class="card__actions">
      <Skeletor width="96" height="36" pill style="margin-right: 4px" />
      <Skeletor width="96" height="36" pill />
    </div>

    <div class="card_category">
      <Skeletor width="10rem" height="10rem" />
      <Skeletor width="10rem" height="10rem" />
    </div>
  </div>
</template>

<script setup lang="ts">
import 'vue-skeletor/dist/vue-skeletor.css';
import { Skeletor } from 'vue-skeletor';
</script>

<style scoped>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin-top: 60px;
}

.card {
  width: 360px;
  margin: 0 auto;
}

.card__image {
  margin-bottom: 12px;
}

.card__slim {
  display: flex;
  margin-bottom: 12px;
}

.card__avatar {
  margin-right: 12px;
}

.card__meta {
  flex-grow: 1;
}

.card__meta p,
.card__meta h2 {
  margin: 0;
}

.card__text {
  margin-bottom: 12px;
}

.card__actions {
  display: flex;
  justify-content: flex-end;
}

.card_category {
  margin: 1.2rem 0.5rem;
  display: flex;
  /* justify-content: space-between; */
}

.card_category > * {
  margin: 0 10px; /* 좌우 마진 추가 */
}
</style>
