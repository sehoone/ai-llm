export default {
  path: '/chatbot',
  component: () => import('@/views/chatbot/Chatbot.vue'),
  redirect: '/chatbot',

  children: [
    {
      path: '/chatbot',
      component: () => import('@/views/chatbot/Chatbot.vue')
    }
  ]
};
