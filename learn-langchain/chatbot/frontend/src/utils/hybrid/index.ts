import type FlexAuth from './auth';
import type FlexDevice from './device/index';
import type FlexEtc from './etc';

/**
 * Native(App)와 통신을 위한 브릿지 추가
 * Native에서 WebView를 생성시 UserAgent에 customApp 문자열을 추가
 * Native에서 WebView를 생성시 script를 주입하여, window.$flex 객체를 생성해서 브릿지 통신시 사용
 * window.$flex: Native와 브릿지 통신으로 사용할 오브젝트
 * window.$flex.xxxx(): Web to Native 인터페이스
 * window.$flex.web:  Native to Web 인터페이스가 정의된 오브젝트
 * window.$flex.web.xxxx():  Native to Web 인터페이스
 * window.onload(): Native에서 스크립트 주입이 완료되면 실행되는 함수
 *
 * https://github.com/Kyun-J/FlexHybridApp-Scripts
 */

export default interface AppBridge extends FlexDevice, FlexEtc, FlexAuth {}
