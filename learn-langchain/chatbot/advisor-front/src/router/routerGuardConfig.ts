import { ref } from 'vue';
import type { Router } from 'vue-router';

// const needsLoginPages = ['/pages/3']

export const isBack = ref(false);

// /* router settring
//   router 이동전 체크 or 처리해야될것들을 setup
// */
export function setupRouterGuard(router: Router): void {
  // createPermissionGuard(router) // 로그인 권한 체크
  // createParamMenuGuard(router) // 메뉴 권한 체크
  createDefaultGuard(router); // 기본처리
}

// // 사용자의 로그인여부에 따른 처리.(ex. 로그인필요메뉴 로그인여부 or jwt토큰 체크)
// export function createPermissionGuard(router: Router): void {
//   router.beforeEach(async (to, from, next) => {
//     logger.debug('createPermissionGuard to.path :' + to.path + ' from.path :' + from.path)
//     logger.debug('createPermissionGuard needsLoginPages.indexOf(to.path) : ', needsLoginPages.indexOf(to.path))

//     /* 토큰이 없는가 ===> 비로그인 상태인가 */
//     const token = localStorage.getItem(StorageNameCode.TOKEN)
//     if (token === null) {
//       if (needsLoginPages.includes(to.path)) {
//         next('/members/main')
//         return
//       }
//     }
//     next()
//   })
// }

// // 사용자의 메뉴 보유권한 처리
// export function createParamMenuGuard(router: Router): void {
//   router.beforeEach(async (to, from, next) => {
//     logger.debug('router.beforeEach createParamMenuGuard')
//     logger.debug('to.path :' + to.path + ' from.path :' + from.path)
//     next()
//   })
// }

/**
 * addEventListener가 setTimeout보다 먼저 실행되는 이유
 * window.addEventListener와 setTimeout이 동시에 호출되더라도,
 * window.addEventListener에 등록된 이벤트 리스너는 setTimeout에 전달된 콜백 함수보다 먼저 실행됨.
 * 이는 setTimeout에 전달된 콜백 함수가 지정된 시간이 경과하고, 현재 실행 중인 모든 코드가 완료될 때까지 대기해야 하기 때문.
 *
 * 이 경우, setTimeout에 전달된 콜백 함수는 0 밀리초 후에 실행되도록 예약되어 있지만,
 * window.addEventListener에 등록된 이벤트 리스너가 먼저 실행.
 * 이는 window.addEventListener에 등록된 이벤트 리스너가 popstate 이벤트가 발생하자마자 실행되기 때문. 그런 다음, setTimeout에 전달된 콜백 함수가 실행.
 */
/**
 *
 * JavaScript는 단일 스레드 언어이며, 이벤트 루프라는 개념을 사용하여 비동기 작업을 처리합.
 * 이벤트 루프는 콜 스택(call stack), 백그라운드(background), 태스크 큐(task queue) 세 가지 주요 구성 요소.
 * 1. 콜 스택: 현재 실행 중인 함수가 쌓이는 곳.
 * 2. 백그라운드: setTimeout과 같은 비동기 작업이 대기하는 곳.
 * 3. 태스크 큐: 백그라운드에서 완료된 비동기 작업의 콜백 함수가 대기하는 곳.
 *
 * setTimeout 함수를 호출하면, 브라우저는 지정된 시간 동안 대기한 후에 콜백 함수를 태스크 큐에 추가.
 * 이벤트 루프는 콜 스택이 비어 있을 때 태스크 큐에서 가장 오래된 작업을 콜 스택으로 이동시킵니다. 그런 다음 이 작업이 실행되고, 콜 스택에서 제거.
 * 따라서 setTimeout에 지정된 시간이 0이라도, 콜백 함수는 즉시 실행되지 않음.
 * 대신, 현재 실행 중인 모든 코드가 완료된 후에 실행됩니다. 이것이 setTimeout 함수가 코드의 실행을 지연시키는 방법.
 */
export function createDefaultGuard(router: Router): void {
  let isPopState = false;

  window.addEventListener('popstate', () => {
    isPopState = true;
  });

  router.beforeEach((to, from, next) => {
    setTimeout(() => {
      if (isPopState) {
        isBack.value = true;
        isPopState = false;
      } else {
        isBack.value = false;
      }
      next();
    }, 0);
  });
}
