<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useRuntimeConfig } from '@/composables/useRuntimeConfig';
// import { useDrawer } from '@/composables/useDrawer';
import Welcome from '@/components/Welcome.vue';
import Conversation from '@/components/Conversation.vue';

const { t } = useI18n();
const runtimeConfig = useRuntimeConfig();
// const drawer = useDrawer();
const route = useRoute();
const router = useRouter();

const getDefaultConversationData = () => {
  return {
    id: null,
    topic: null,
    messages: [],
    loadingMessages: false
  };
};

const conversation = ref(getDefaultConversationData());

const loadConversation = async () => {
  // const { data, error } = await useAuthFetch('/api/chat/conversations/' + route.params.id);
  // if (!error.value) {
  //   conversation.value = Object.assign(conversation.value, data.value);
  // }
};

const loadMessage = async () => {
  // const { data, error } = await useAuthFetch('/api/chat/messages/?conversationId=' + route.params.id);
  // if (!error.value) {
  //   conversation.value.messages = data.value;
  //   conversation.value.id = route.params.id;
  // }
};

const createNewConversation = () => {
  if (route.path !== '/') {
    return router.push('/?new');
  }
  conversation.value = Object.assign(getDefaultConversationData(), {
    topic: t('newConversation')
  });
};

onMounted(async () => {
  if (route.params.id) {
    conversation.value.loadingMessages = true;
    await loadConversation();
    await loadMessage();
    conversation.value.loadingMessages = false;
  }
});

const navTitle = computed(() => {
  if (conversation.value && conversation.value.topic !== null) {
    return conversation.value.topic === '' ? t('defaultConversationTitle') : conversation.value.topic;
  }
  return 'chatbot';
});
</script>

<template>
  dd
  <v-app>
    <v-app-bar>
      <v-app-bar-nav-icon></v-app-bar-nav-icon>

      <v-toolbar-title>{{ navTitle }}</v-toolbar-title>

      <v-spacer></v-spacer>

      <v-btn :title="t('newConversation')" icon="add" @click="createNewConversation" class="d-md-none ma-3"></v-btn>
      <v-btn variant="outlined" class="text-none d-none d-md-block" @click="createNewConversation">
        {{ t('newConversation') }}
      </v-btn>
    </v-app-bar>

    <v-main>
      <Welcome v-if="!route.params.id && conversation.messages.length === 0" />
      <Conversation :conversation="conversation" />
    </v-main>
  </v-app>
</template>
