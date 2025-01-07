import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

import sample from '@/router/routes/sample';
import transition from '@/router/routes/transition';
const NotfoundView = () => import('@/views/sample/NotFoundView.vue');

const routes: Array<RouteRecordRaw> = [
  sample,
  transition,
  // routerMembers,
  // routerPosts,
  // {
  //   path: '/',
  //   component: () => import('@/views/sample/TransitionTest.vue'),
  //   redirect: '/transition/page1',
  //   children: [
  //     sample,
  //     transition
  //     // Add other child routes here
  //   ]
  // },
  // {
  //   path: '/',
  //   redirect: '/sample/reactive',
  //   meta: {
  //     title: 'HomeMain'
  //   }
  // },
  // {
  //   path: '/',
  //   // Note: Must specify a component to remove warning of No matching path
  //   component: () => {},
  //   // Doc: https://router.vuejs.org/guide/advanced/navigation-guards.html#per-route-guard
  //   beforeEnter: (to, from, next) => {
  //     console.log(`[${import.meta.url.split('?')[0].split('/').slice(3).join('/')}::beforeEnter()] to, from`, to, from);
  //     // Default to page1
  //     next('/page1');
  //   }
  // },
  // {
  //   path: '/page1',
  //   component: () => import('@/views/sample/Page1.vue'),
  //   meta: { transition: 'slide' }
  // },
  // {
  //   path: '/page2',
  //   component: () => import('@/views/sample/Page2.vue')
  // },
  // {
  //   path: '/page3',
  //   component: () => import('@/views/sample/Page3.vue')
  // },
  // {
  //   path: '/:segment',
  //   component: () => import('@/views/sample/CatchAll.vue')
  // },
  {
    path: '/:pathMatch(.*)*', // 404 Not Found
    component: NotfoundView,
    meta: {
      title: 'Notfound'
    }
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve(savedPosition);
        }, 7000);
      });
    } else if (to.hash) {
      return {
        selector: to.hash,
        behavior: 'smooth'
      };
    } else {
      return { x: 0, y: 0, behavior: 'smooth' };
    }
  }
});

// 라우터 가드(router before/after) setup
// setupRouterGuard(router);

export default router;
