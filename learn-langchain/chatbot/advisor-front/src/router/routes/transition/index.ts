export default {
  path: '/transition',
  component: () => import('@/views/sample/TransitionTest.vue'),
  redirect: '/transition/page1',

  children: [
    {
      path: '/transition/page1',
      component: () => import('@/views/sample/Page1.vue'),
      meta: { transition: 'slide' }
    },
    {
      path: '/transition/page2',
      component: () => import('@/views/sample/Page2.vue')
    },
    {
      path: '/transition/page3',
      component: () => import('@/views/sample/Page3.vue')
    },
    {
      path: '/transition/:segment',
      component: () => import('@/views/sample/CatchAll.vue')
    }
  ]
};
