import router from '@/router';
import { useCommonStore } from '@/service/common/commonModule';
import { logger } from '@/utils/logger';
/**
 * @description 웹뷰 뒤로가기 이벤트
 * @returns void
 * native to web 브릿지 backWebView 이벤트 핸들러
 */
const webViewBack = () => {
  logger.debug('call webview back');
  const commonStore = useCommonStore();
  // 모달이 떠있으면 화면 뒤로가기 막기
  if (!commonStore.isEmptyShowedModals) {
    commonStore.popShowedModal();
    return;
  }

  if ('/sample/reactive' == router.currentRoute.value.path) {
    logger.debug('is last page');
  } else {
    router.back();
  }
};

// 전역 이벤트 리스너 등록
export const loadGlobalEventListner = async () => {
  window.addEventListener('webViewBack', webViewBack as EventListener);
};

export const removeGlobalEventListner = () => {
  window.removeEventListener('webViewBack', webViewBack);
};
