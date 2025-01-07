const SampleLayout = () => import(/* webpackChunkName: "group-sample" */ '@/layouts/sample/SampleLayout.vue');
const Reactive = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/Reactive.vue');
const Computed = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/Computed.vue');
const PropsParent = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/PropsParent.vue');
const EmitsParent = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/EmitsParent.vue');
const LoginPage = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/LoginPage.vue');
const PostsList = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/PostsList.vue');
const PostsDetail = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/PostsDetail.vue');
const BridgeTest = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/BridgeTest.vue');
const MultiLanguage = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/MultiLanguage.vue');
const ScrollBehavior1 = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/ScrollBehavior1.vue');
const ScrollBehavior2 = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/ScrollBehavior2.vue');
const InputTest = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/InputTest.vue');
const BackModal = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/BackModal.vue');
const Skeleton = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/Skeleton.vue');
const SimpleForm = () => import(/* webpackChunkName: "group-sample" */ '@/views/sample/form/SimpleForm.vue');
const MultipleStepForm = () =>
  import(/* webpackChunkName: "group-sample" */ '@/views/sample/form/MultipleStepForm.vue');

export default {
  path: '/sample',
  component: SampleLayout,
  redirect: '/sample/reactive',

  children: [
    {
      path: '/sample/reactive',
      component: Reactive,
      meta: {
        title: 'reactive'
      }
    },
    {
      path: '/sample/computed',
      component: Computed,
      meta: {
        title: 'computed'
      }
    },
    {
      path: '/sample/props-parent',
      component: PropsParent,
      meta: {
        title: 'propsParent'
      }
    },
    {
      path: '/sample/emits-parent',
      component: EmitsParent,
      meta: {
        title: 'emitsParent'
      }
    },

    {
      path: '/sample/login-page',
      component: LoginPage,
      meta: {
        title: 'loginPage'
      }
    },
    {
      path: '/sample/posts-list',
      component: PostsList,
      meta: {
        title: 'postsList'
      }
    },
    {
      path: '/sample/posts-detail',
      component: PostsDetail,
      meta: {
        title: 'postsDetail'
      }
    },
    {
      path: '/sample/bridge-test',
      component: BridgeTest,
      meta: {
        title: 'bridgeTest'
      }
    },
    {
      path: '/sample/multi-language',
      component: MultiLanguage,
      meta: {
        title: 'multiLanguage'
      }
    },
    {
      path: '/sample/scroll-behavior1',
      component: ScrollBehavior1,
      meta: {
        title: 'scrollBehavior1'
      }
    },
    {
      path: '/sample/scroll-behavior2',
      component: ScrollBehavior2,
      meta: {
        title: 'scrollBehavior2'
      }
    },
    {
      path: '/sample/input-test',
      component: InputTest,
      meta: {
        title: 'inputTest'
      }
    },
    {
      path: '/sample/back-modal',
      component: BackModal,
      meta: {
        title: 'backModal'
      }
    },
    {
      path: '/sample/skeleton',
      component: Skeleton,
      meta: {
        title: 'skeleton'
      }
    },
    {
      path: '/sample/simple-form',
      component: SimpleForm,
      meta: {
        title: 'simpleForm'
      }
    },
    {
      path: '/sample/multiple-step-form',
      component: MultipleStepForm,
      meta: {
        title: 'multipleStepForm'
      }
    }
  ]
};
