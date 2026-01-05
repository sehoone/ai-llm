import base64
import io
import json
import time
from openai import OpenAI
from src.common.config import settings, Environment
from typing import Optional, Dict, Any
import azure.cognitiveservices.speech as speechsdk
import tempfile
import os


class AudioService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.tts_model = settings.OPENAI_TTS_MODEL
        self.tts_voice = settings.OPENAI_TTS_VOICE
        self.stt_model = settings.OPENAI_STT_MODEL
        
        # Azure Speech Service 초기화
        if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION
            )
            self.speech_config.speech_recognition_language = "en-US"
            print(f"[Azure Speech] 초기화 성공 - 지역: {settings.AZURE_SPEECH_REGION}")
        else:
            self.speech_config = None
            print("[Azure Speech] API 키가 설정되지 않았습니다. 발음 평가 기능을 사용할 수 없습니다.")
    
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """텍스트를 음성으로 변환 (TTS)"""
        try:
            print(f"[TTS] 요청 시작 - 텍스트 길이: {len(text)}, 모델: {self.tts_model}, 음성: {self.tts_voice}")
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text
            )
            audio_content = response.content
            print(f"[TTS] 성공 - 오디오 크기: {len(audio_content)} bytes")
            return audio_content
        except Exception as e:
            print(f"[TTS] 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def speech_to_text(self, audio_data: bytes, format: str = "wav") -> Optional[str]:
        """음성을 텍스트로 변환 (STT)
        
        Azure Speech Service를 우선 사용하고, 실패 시 OpenAI Whisper 사용
        """
        try:
            print("\n[STT] ========== STT 요청 시작 ==========")
            print(f"[STT] 입력 형식: {format}, 크기: {len(audio_data)} bytes")
            
            if not audio_data or len(audio_data) == 0:
                print("[STT] 오디오 데이터가 비어있습니다")
                return None
            
            # 1단계: Azure Speech Service 시도
            if self.speech_config:
                # 로컬서버인경우는 azure stt 사용안함
                if settings.ENVIRONMENT != Environment.DEVELOPMENT:
                    print("[STT] Azure Speech Service로 STT 시도...")
                    azure_text = await self._azure_speech_to_text(audio_data, format)
                    if azure_text:
                        print(f"[STT] Azure STT 성공: '{azure_text}'")
                        print("[STT] ========== STT 완료 ==========\n")
                        return azure_text
                    else:
                        print("[STT] Azure STT 실패, Whisper로 폴백...")
            
            # 2단계: OpenAI Whisper 폴백
            print("[STT] OpenAI Whisper로 STT 시도...")
            whisper_text = await self._openai_speech_to_text(audio_data, format)
            if whisper_text:
                print(f"[STT] Whisper STT 성공: '{whisper_text}'")
            else:
                print("[STT] Whisper STT도 실패")
            print("[STT] ========== STT 완료 ==========\n")
            return whisper_text
            
        except Exception as e:
            print(f"[STT] 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _azure_speech_to_text(self, audio_data: bytes, format: str) -> Optional[str]:
        """Azure Speech Service를 사용한 STT"""
        if not self.speech_config:
            return None
        
        temp_file_path = None
        try:
            print(f"[Azure STT] 시작 - 형식: {format}, 크기: {len(audio_data)} bytes")
            
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # Azure 음성 인식
            audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            print("[Azure STT] 음성 인식 중...")
            result = speech_recognizer.recognize_once()
            print("[Azure STT] 인식 완료")
            # 인식기 해제
            del speech_recognizer
            del audio_config
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print(f"[Azure STT] 성공: '{result.text}'")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("[Azure STT] 음성 인식 실패 (NoMatch)")
                return None
            elif result.reason == speechsdk.ResultReason.Canceled:
                error_details = result.cancellation_details.error_details if result.cancellation_details else "알 수 없음"
                print(f"[Azure STT] 취소됨: {error_details}")
                return None
                
        except Exception as e:
            print(f"[Azure STT] 오류: {str(e)}")
            return None
        finally:
            # 임시 파일 삭제 시도 (최대 3회)
            if temp_file_path and os.path.exists(temp_file_path):
                for attempt in range(3):
                    try:
                        os.unlink(temp_file_path)
                        print("[Azure STT] 임시 파일 삭제 성공")
                        break
                    except OSError:
                        if attempt < 2:
                            print(f"[Azure STT] 파일 삭제 재시도 ({attempt + 1}/3)...")
                            time.sleep(0.1)  # 짧은 대기
                        else:
                            print(f"[Azure STT] 임시 파일 삭제 실패 (나중에 정리됨): {temp_file_path}")
    
    async def _openai_speech_to_text(self, audio_data: bytes, format: str) -> Optional[str]:
        """OpenAI Whisper를 사용한 STT"""
        try:
            print(f"[Whisper STT] 시작 - 크기: {len(audio_data)} bytes, 형식: {format}")
            
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{format}"
            
            transcript = self.client.audio.transcriptions.create(
                model=self.stt_model,
                file=audio_file,
                language="en"
            )
            print(f"[Whisper STT] 성공: '{transcript.text}'")
            return transcript.text
        except Exception as e:
            print(f"[Whisper STT] 오류: {str(e)}")
            return None
    
    def audio_to_base64(self, audio_data: bytes) -> str:
        """오디오 데이터를 base64로 인코딩"""
        return base64.b64encode(audio_data).decode('utf-8')
    
    def base64_to_audio(self, base64_string: str) -> bytes:
        """base64 문자열을 오디오 데이터로 디코딩"""
        return base64.b64decode(base64_string)
    
    async def assess_pronunciation(
        self, 
        audio_data: bytes, 
        reference_text: Optional[str] = None,
        format: str = "wav"
    ) -> Optional[Dict[str, Any]]:
        """
        Azure Speech Service를 사용한 발음 평가
        
        GitHub 샘플: https://github.com/Azure-Samples/cognitive-services-speech-sdk
        
        Args:
            audio_data: 평가할 오디오 데이터 (WAV 권장)
            reference_text: 참조 텍스트 (필수)
            format: 오디오 형식
        
        Returns:
            발음 평가 결과:
            {
                "accuracy_score": 0-100,
                "pronunciation_score": 0-100,
                "completeness_score": 0-100,
                "fluency_score": 0-100,
                "prosody_score": 0-100,
                "recognized_text": "인식된 텍스트",
                "reference_text": "참조 텍스트",
                "word_details": [...],  # 단어별 상세 점수
                "detailed_scores": {...}  # 추가 상세 정보
            }
        """
        if not self.speech_config:
            print("[발음 평가] Azure Speech Service가 설정되지 않았습니다")
            return None
        
        if not reference_text:
            print("[발음 평가] reference_text가 필요합니다")
            return None
        
        temp_file_path = None
        try:
            print("\n[발음 평가] ========== 평가 시작 ==========")
            print(f"[발음 평가] 참조 텍스트: '{reference_text}'")
            print(f"[발음 평가] 입력 형식: {format}, 크기: {len(audio_data)} bytes")
            
            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            # 1. 발음 평가 설정 (GitHub 샘플 참고)
            print("[발음 평가] 평가 설정 중...")
            
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                # reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            # 2. 오디오 설정
            audio_config = speechsdk.AudioConfig(filename=temp_file_path)
            
            # 3. 음성 인식기 생성
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # 4. 발음 평가 적용
            pronunciation_config.apply_to(speech_recognizer)
            
            # 5. 인식 수행
            print("[발음 평가] 음성 분석 중...")
            if settings.environment != "local":
                result = speech_recognizer.recognize_once()
                
                # 인식기 해제
                del speech_recognizer
                del audio_config
                
                # 6. 결과 처리
                if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    # 발음 평가 결과 파싱
                    pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
                    
                    # 기본 점수
                    accuracy = pronunciation_result.accuracy_score
                    pronunciation = pronunciation_result.pronunciation_score
                    completeness = pronunciation_result.completeness_score
                    fluency = pronunciation_result.fluency_score
                    
                    print(f"[발음 평가] 인식 성공: '{result.text}'")
                    print("[발음 평가] 점수:")
                    print(f"  - 정확도: {accuracy:.1f}")
                    print(f"  - 발음: {pronunciation:.1f}")
                    print(f"  - 완성도: {completeness:.1f}")
                    print(f"  - 유창성: {fluency:.1f}")
                    
                    # Prosody 점수 안전하게 처리
                    prosody = getattr(pronunciation_result, 'prosody_score', None)
                    prosody_score = round(prosody, 2) if prosody is not None else 0
                    
                    # 상세 결과 빌드
                    assessment_data = {
                        "accuracy_score": round(accuracy, 2),
                        "pronunciation_score": round(pronunciation, 2),
                        "completeness_score": round(completeness, 2),
                        "fluency_score": round(fluency, 2),
                        "prosody_score": prosody_score,
                        "recognized_text": result.text,
                        # "reference_text": reference_text,
                    }
                    
                    # JSON 형식으로 상세 결과 가져오기
                    json_result = result.properties.get(
                        speechsdk.PropertyId.SpeechServiceResponse_JsonResult
                    )
                    
                    if json_result:
                        try:
                            detailed_result = json.loads(json_result)
                            print("[발음 평가] 상세 분석 추출 중...")
                            
                            # NBest 결과에서 단어별 상세 정보 추출
                            if "NBest" in detailed_result and len(detailed_result["NBest"]) > 0:
                                nbest = detailed_result["NBest"][0]
                                
                                # 단어별 상세 점수
                                if "Words" in nbest:
                                    word_details = []
                                    for word_info in nbest["Words"]:
                                        word_details.append({
                                            "word": word_info.get("Word", ""),
                                            "accuracy_score": round(word_info.get("PronunciationAssessment", {}).get("AccuracyScore", 0), 2),
                                            "pronunciation_score": round(word_info.get("PronunciationAssessment", {}).get("PronunciationScore", 0), 2),
                                        })
                                    assessment_data["word_details"] = word_details
                                    print(f"[발음 평가] 단어별 분석: {len(word_details)}개 단어")
                                
                                # 전체 발음 평가 상세 정보
                                if "PronunciationAssessment" in nbest:
                                    pa = nbest["PronunciationAssessment"]
                                    assessment_data["detailed_scores"] = {
                                        "overall_accuracy": round(pa.get("AccuracyScore", 0), 2),
                                        "overall_pronunciation": round(pa.get("PronunciationScore", 0), 2),
                                        "overall_completeness": round(pa.get("CompletenessScore", 0), 2),
                                        "overall_fluency": round(pa.get("FluencyScore", 0), 2),
                                        "overall_prosody": round(pa.get("ProsodyScore", 0), 2),
                                    }
                                    print("[발음 평가] 상세 점수 추출 완료")
                        except json.JSONDecodeError as e:
                            print(f"[발음 평가] JSON 파싱 실패: {e}")
                    
                    print("[발음 평가] ========== 평가 완료 ==========\n")
                    return assessment_data
                    
                elif result.reason == speechsdk.ResultReason.NoMatch:
                    print("[발음 평가] 음성 인식 불가: {result.no_match_details}")
                    return None
                    
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation = result.cancellation_details
                    print("[발음 평가] 취소됨: {cancellation.reason}")
                    if cancellation.reason == speechsdk.CancellationReason.Error:
                        print("[발음 평가] 오류 상세: {cancellation.error_details}")
                    return None
                
        except Exception:
            print("[발음 평가] 예외 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # 임시 파일 삭제 시도 (최대 3회)
            if temp_file_path and os.path.exists(temp_file_path):
                for attempt in range(3):
                    try:
                        os.unlink(temp_file_path)
                        print("[발음 평가] 임시 파일 삭제 성공")
                        break
                    except OSError:
                        if attempt < 2:
                            print("[발음 평가] 파일 삭제 재시도 ({attempt + 1}/3)...")
                            time.sleep(0.1)  # 짧은 대기
                        else:
                            print("[발음 평가] 임시 파일 삭제 실패 (나중에 정리됨): {temp_file_path}")

