import { defineStore } from 'pinia';
import type {
  CommonUseAxiosModalInterface,
  CommonUseAxiosSpinnerInterface,
  CommonUseMessageModalInterface,
  showedModal
} from '@/service/common/model/commonModel';
import { isEmpty } from 'lodash-es';

interface commonState {
  commonUseMessageModalInfo: CommonUseMessageModalInterface;
  commonUseAxiosModalInfo: CommonUseAxiosModalInterface;
  commonUseAxiosSpinnerInfo: CommonUseAxiosSpinnerInterface;
  isDummyApiMode: boolean;
  routerHeaderTitle: string | null;
  isShowedMainTabbar: boolean;
  isFirstRouteMoveWebView: boolean;
  isCallMoveWebView: boolean;
  showedModals: showedModal[];
}

export const CommonUseMessageModalInfoInit = {
  isShowedModal: false,
  showedModalCount: 0
};

export const CommonUseAxiosModalInfoInit = {
  isShowedModal: false
};

export const CommonUseAxiosSpinnerInfoInit = {
  isShowedSpinner: false,
  showedSpinnerCount: 0
};

export const useCommonStore = defineStore({
  id: 'common-store',

  state: (): commonState => ({
    commonUseMessageModalInfo: CommonUseMessageModalInfoInit, // 공통 메세지 modal 정보
    commonUseAxiosModalInfo: CommonUseAxiosModalInfoInit, // axios에서 사용하는 애러 modal 정보
    commonUseAxiosSpinnerInfo: CommonUseAxiosSpinnerInfoInit, // axios 요청시 노출되는 spinner 정보
    isDummyApiMode: false, // dummy api mode 여부. 로컬 모드일떄 더미API를 하여 개발하고자 할떄 사용
    routerHeaderTitle: null, // router header name
    isShowedMainTabbar: false,
    isFirstRouteMoveWebView: false, // moveWebView 호출시 첫번째 라우터 여부
    isCallMoveWebView: false, // moveWebView 호출 여부
    showedModals: []
  }),

  getters: {
    // useMessageModal 정보. 공통 메세지 modal 정보
    getCommonUseMessageModalInfo(): CommonUseMessageModalInterface {
      return this.commonUseMessageModalInfo;
    },
    // useMessageModal 노출 여부. 공통 메세지 modal 노출 여부
    getCommonUseMessageModalIsShowedModal(): boolean {
      return this.commonUseMessageModalInfo.isShowedModal;
    },
    // useAxiosModal 노출 여부. axios에서 사용하는 애러 modal 노출 여부
    getCommonUseAxiosModalIsShowedModal(): boolean {
      return this.commonUseAxiosModalInfo.isShowedModal;
    },
    // useAxiosSpinner 정보. axios 요청시 노출되는 spinner 정보
    getCommonUseAxiosSpinnerInfo(): CommonUseAxiosSpinnerInterface {
      return this.commonUseAxiosSpinnerInfo;
    },
    // useAxiosSpinner 노출 여부. axios 요청시 노출되는 spinner 노출여부
    getCommonUseAxiosSpinnerIsShowedSpinner(): boolean {
      return this.commonUseAxiosSpinnerInfo.isShowedSpinner;
    },
    // dummy api mode 여부. 로컬 모드일떄 더미API를 하여 개발하고자 할떄 사용
    getIsDummyApiMode(): boolean {
      return this.isDummyApiMode;
    },
    // router 헤더 타이틀. openView브릿지 호출할떄 사용
    getRouterHeaderTitle(): string | null {
      return this.routerHeaderTitle;
    },
    // 메인 탭바 노출 여부
    getIsShowedMainTabbar(): boolean {
      return this.isShowedMainTabbar;
    },
    // 첫번째 라우터 moveWebView 여부
    getIsFirstRouteMoveWebView(): boolean {
      return this.isFirstRouteMoveWebView;
    },
    getIsCallMoveWebView(): boolean {
      return this.isCallMoveWebView;
    },
    getShowedModals(): showedModal[] {
      return this.showedModals;
    },
    // 노출된 모달이 있는지 여부
    isEmptyShowedModals(): boolean {
      return isEmpty(this.showedModals);
    }
  },
  actions: {
    // useMessageModal 노출 modal count 증가
    setIncCommonUseMessageModalShowedModalCount() {
      this.commonUseMessageModalInfo.showedModalCount++;
      if (this.commonUseMessageModalInfo.showedModalCount > 0) {
        this.commonUseMessageModalInfo.isShowedModal = true;
      }
    },
    // useMessageModal 노출 modal count 감소
    setDecCommonUseMessageModalShowedModalCount() {
      this.commonUseMessageModalInfo.showedModalCount--;
      if (this.commonUseMessageModalInfo.showedModalCount <= 0) {
        this.commonUseMessageModalInfo.isShowedModal = false;
      }
    },
    // useMessageModal 노출 modal count 감소
    setDecCommonUseAxiosModalIsShowed(isShowedModal: boolean) {
      this.commonUseAxiosModalInfo.isShowedModal = isShowedModal;
    },
    // useAxiosSpinner 노출 count 증가
    setIncCommonUseAxiosSpinnerShowedSpinnerCount() {
      this.commonUseAxiosSpinnerInfo.showedSpinnerCount++;
      if (this.commonUseAxiosSpinnerInfo.showedSpinnerCount > 0) {
        this.commonUseAxiosSpinnerInfo.isShowedSpinner = true;
      }
    },
    // useAxiosSpinner 노출 count 감소
    setDecCommonUseAxiosSpinnerShowedSpinnerCount() {
      this.commonUseAxiosSpinnerInfo.showedSpinnerCount--;
      if (this.commonUseAxiosSpinnerInfo.showedSpinnerCount <= 0) {
        this.commonUseAxiosSpinnerInfo.isShowedSpinner = false;
      }
    },
    setDummyApiMode(isDummyApiMode: boolean) {
      this.isDummyApiMode = isDummyApiMode;
    },
    setRouterHeaderTitle(routerHeaderTitle: string | null) {
      this.routerHeaderTitle = routerHeaderTitle;
    },
    setIsShowedMainTabbar(isShowedMainTabbar: boolean) {
      this.isShowedMainTabbar = isShowedMainTabbar;
    },
    setIsFirstRouteMoveWebView(isFirstRouteMoveWebView: boolean) {
      this.isFirstRouteMoveWebView = isFirstRouteMoveWebView;
    },
    setIsCallMoveWebView(isCallMoveWebView: boolean) {
      this.isCallMoveWebView = isCallMoveWebView;
    },
    /**
     * Push showedModal
     * @param modal showedModal
     */
    pushShowedModal(modal: showedModal) {
      this.showedModals.push(modal);
    },
    // pop showedModal
    popShowedModal() {
      if (this.showedModals.length === 0) {
        return;
      }
      return this.showedModals.pop();
    },
    peekShowedModal() {
      return this.showedModals[this.showedModals.length - 1];
    },
    // remove showedModal
    removeShowedModal(modalId: string) {
      this.showedModals = this.showedModals.filter((modal) => modal.modalId !== modalId);
    }
  }
});
