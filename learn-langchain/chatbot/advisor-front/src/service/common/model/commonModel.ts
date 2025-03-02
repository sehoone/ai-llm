/**
 * @description: 공통 UseMessageModal 모델
 */
export interface CommonUseMessageModalInterface {
  isShowedModal: boolean;
  showedModalCount: number;
}

/**
 * @description: 공통 UseAxiosModal 모델
 */
export interface CommonUseAxiosModalInterface {
  isShowedModal: boolean;
}

/**
 * @description 공통 응답 공통 코드 모델
 */
export interface CommonResStatInterface {
  rstCd: string;
  err_cod: string;
  err_msg: string;
}

export interface CommonUseAxiosSpinnerInterface {
  isShowedSpinner: boolean;
  showedSpinnerCount: number;
}

export interface showedModal {
  modalId: String;
}
