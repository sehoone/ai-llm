import json
import logging
from typing import Dict, List, Any
import httpx

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware

from src.voice_evaluation.schemas.voice_evaluation_schema import ConversationResponse, EvaluationRequest, EvaluationResponse
from src.voice_evaluation.services.audio_service import AudioService
from src.voice_evaluation.services.evaluation_service import EvaluationService
from src.common.config import settings

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# 서비스 인스턴스
evaluation_service = EvaluationService()
audio_service = AudioService()

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.conversation_histories: Dict[WebSocket, List[Dict[str, str]]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.conversation_histories[websocket] = []
        logger.info(f"클라이언트 연결됨. 총 연결: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.conversation_histories:
            del self.conversation_histories[websocket]
        logger.info(f"클라이언트 연결 해제. 총 연결: {len(self.active_connections)}")
    
    def get_history(self, websocket: WebSocket) -> List[Dict[str, str]]:
        return self.conversation_histories.get(websocket, [])
    
    def add_to_history(self, websocket: WebSocket, role: str, content: str):
        if websocket not in self.conversation_histories:
            self.conversation_histories[websocket] = []
        self.conversation_histories[websocket].append({"role": role, "content": content})

manager = ConnectionManager()


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_text(request: EvaluationRequest):
    """텍스트 기반 평가 엔드포인트"""
    try:
        evaluation_result = await evaluation_service.evaluate_conversation(
            text=request.text,
            conversation_history=request.conversation_history
        )
        return EvaluationResponse(**evaluation_result)
    except Exception as e:
        logger.error(f"평가 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"평가 중 오류가 발생했습니다: {str(e)}")


@router.get("/azure-avatar-token")
async def get_azure_avatar_token():
    """Azure TTS Avatar 토큰 발급"""
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Service 설정이 누락되었습니다.")
    
    fetch_token_url = f"https://{settings.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                fetch_token_url,
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Azure Avatar Token 발급 실패: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Azure Avatar Token 발급 실패")
                
            return response.json()
        except Exception as e:
            logger.error(f"Azure Avatar Token 요청 중 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Azure Avatar Token 요청 중 오류: {str(e)}")


@router.get("/speech-token")
async def get_speech_token():
    """Azure Speech Service 인증 토큰 발급"""
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Service 설정이 누락되었습니다.")
    
    fetch_token_url = f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                fetch_token_url,
                headers={
                    "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Speech Token 발급 실패: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Speech Token 발급 실패")
                
            return {"token": response.text, "region": settings.AZURE_SPEECH_REGION}
        except Exception as e:
            logger.error(f"Speech Token 요청 중 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Speech Token 요청 중 오류: {str(e)}")


@router.websocket("/ws/conversation")
async def websocket_conversation(websocket: WebSocket):
    """실시간 음성 대화 및 평가 WebSocket"""
    await manager.connect(websocket)
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive()
            
            # 텍스트 메시지 처리
            if "text" in data:
                message_data = json.loads(data["text"])
                message_type = message_data.get("type", "text")
                
                if message_type == "text":
                    # 텍스트 입력 처리
                    user_text = message_data.get("text", "")
                    if not user_text:
                        continue
                    
                    logger.info(f"사용자 텍스트 수신: {user_text}")
                    
                    # 대화 히스토리 가져오기
                    history = manager.get_history(websocket)
                    
                    # 모의평가 시작 메시지인지 확인
                    is_start_message = user_text.strip() == "모의평가 시작"
                    
                    # AI 응답 생성
                    ai_response = await evaluation_service.generate_response(
                        user_input=user_text,
                        conversation_history=history
                    )
                    
                    # 시작 메시지가 아닐 때만 히스토리에 추가
                    if not is_start_message:
                        manager.add_to_history(websocket, "user", user_text)
                    manager.add_to_history(websocket, "assistant", ai_response)
                    
                    # TTS 생성
                    logger.info(f"TTS 생성 시작: {ai_response[:50]}...")
                    audio_data = await audio_service.text_to_speech(ai_response)
                    audio_base64 = None
                    if audio_data:
                        audio_base64 = audio_service.audio_to_base64(audio_data)
                        logger.info(f"TTS 생성 완료, Base64 길이: {len(audio_base64)}")
                    else:
                        logger.warning("TTS 생성 실패 - audio_data가 None")
                    
                    # 응답 전송 (평가 없이)
                    response = ConversationResponse(
                        text=ai_response,
                        audio=audio_base64,
                        evaluation=None
                    )
                    
                    logger.info(f"응답 전송: text={len(ai_response)}자, audio={'있음' if audio_base64 else '없음'}, 시작메시지={is_start_message}")
                    await websocket.send_json(response.dict())
                    logger.info("응답 전송 완료")
                
                elif message_type == "audio":
                    # 오디오 입력 처리
                    audio_base64 = message_data.get("audio_data", "")
                    audio_format = message_data.get("format", "wav")
                    
                    if not audio_base64:
                        continue
                    
                    logger.info("사용자 오디오 수신")
                    
                    # STT: 오디오를 텍스트로 변환
                    audio_bytes = audio_service.base64_to_audio(audio_base64)
                    user_text = await audio_service.speech_to_text(audio_bytes, audio_format)
                    
                    if not user_text:
                        await websocket.send_json({
                            "error": "음성을 텍스트로 변환할 수 없습니다."
                        })
                        continue
                    
                    logger.info(f"STT 결과: {user_text}")
                    
                    # 발음 평가 수행 (Azure Speech Service)
                    pronunciation_result = await audio_service.assess_pronunciation(
                        audio_bytes, 
                        user_text
                    )
                    
                    if pronunciation_result:
                        logger.info(f"발음 평가 완료 - 점수: {pronunciation_result.get('pronunciation_score', 0)}")
                    
                    # 대화 히스토리 가져오기
                    history = manager.get_history(websocket)
                    
                    # AI 응답 생성
                    ai_response = await evaluation_service.generate_response(
                        user_input=user_text,
                        conversation_history=history
                    )
                    
                    # 히스토리 업데이트
                    manager.add_to_history(websocket, "user", user_text)
                    manager.add_to_history(websocket, "assistant", ai_response)
                    
                    # TTS 생성
                    audio_data = await audio_service.text_to_speech(ai_response)
                    audio_base64 = None
                    if audio_data:
                        audio_base64 = audio_service.audio_to_base64(audio_data)
                    
                    # 응답 전송 (발음 평가 결과 포함)
                    response = ConversationResponse(
                        text=ai_response,
                        audio=audio_base64,
                        evaluation=None
                    )
                    
                    # 사용자 텍스트와 발음 평가를 별도로 전송
                    await websocket.send_json({
                        "type": "user_text",
                        "text": user_text,
                        "pronunciation": pronunciation_result
                    })
                    
                    logger.info(f"발음 평가 데이터 전송: {pronunciation_result}")
                    
                    await websocket.send_json(response.dict())
                    logger.info("응답 전송 완료")
                
                elif message_type == "reset":
                    # 대화 히스토리 초기화
                    manager.conversation_histories[websocket] = []
                    await websocket.send_json({"status": "reset", "message": "대화 히스토리가 초기화되었습니다."})
                
                elif message_type == "evaluate":
                    # 평가 요청 처리
                    logger.info("평가 요청 수신")
                    history = manager.get_history(websocket)
                    
                    if not history or len(history) == 0:
                        await websocket.send_json({
                            "error": "평가할 대화 내용이 없습니다."
                        })
                        continue
                    
                    # 전체 대화 히스토리를 기반으로 평가 수행
                    # 대화 내용을 텍스트로 변환
                    conversation_text = ""
                    for msg in history:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        conversation_text += f"{role}: {content}\n"
                    
                    # 평가 수행 (발음 평가는 실시간으로 이미 수행되었으므로 텍스트 평가만)
                    evaluation_result = await evaluation_service.evaluate_conversation(
                        text="",  # 전체 대화를 평가하므로 빈 텍스트
                        conversation_history=history
                    )
                    
                    # 평가 결과 전송
                    response = ConversationResponse(
                        text="",
                        audio=None,
                        evaluation=EvaluationResponse(**evaluation_result)
                    )
                    await websocket.send_json(response.dict())
                    logger.info("평가 결과 전송 완료")
            
            # 바이너리 메시지 처리 (직접 오디오 데이터)
            elif "bytes" in data:
                # 바이너리 오디오 데이터 처리
                audio_bytes = data["bytes"]
                logger.info("바이너리 오디오 데이터 수신")
                
                # STT: 오디오를 텍스트로 변환
                user_text = await audio_service.speech_to_text(audio_bytes)
                
                if not user_text:
                    await websocket.send_json({
                        "error": "음성을 텍스트로 변환할 수 없습니다."
                    })
                    continue
                
                logger.info(f"STT 결과: {user_text}")
                
                # 발음 평가 수행 (Azure Speech Service)
                pronunciation_result = await audio_service.assess_pronunciation(
                    audio_bytes, 
                    user_text
                )
                
                if pronunciation_result:
                    logger.info(f"발음 평가 완료 - 점수: {pronunciation_result.get('pronunciation_score', 0)}")
                
                # 대화 히스토리 가져오기
                history = manager.get_history(websocket)
                
                # AI 응답 생성
                ai_response = await evaluation_service.generate_response(
                    user_input=user_text,
                    conversation_history=history
                )
                
                # 히스토리 업데이트
                manager.add_to_history(websocket, "user", user_text)
                manager.add_to_history(websocket, "assistant", ai_response)
                
                # TTS 생성
                audio_data = await audio_service.text_to_speech(ai_response)
                audio_base64 = None
                if audio_data:
                    audio_base64 = audio_service.audio_to_base64(audio_data)
                
                # 응답 전송 (발음 평가 결과 포함)
                response = ConversationResponse(
                    text=ai_response,
                    audio=audio_base64,
                    evaluation=None
                )
                
                # 사용자 텍스트와 발음 평가를 별도로 전송
                await websocket.send_json({
                    "type": "user_text",
                    "text": user_text,
                    "pronunciation": pronunciation_result
                })
                
                logger.info(f"발음 평가 데이터 전송: {pronunciation_result}")
                
                await websocket.send_json(response.dict())
                logger.info("응답 전송 완료")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("클라이언트 연결 종료")
    except RuntimeError as e:
        if "disconnect message has been received" in str(e) or "Unexpected ASGI message" in str(e):
            manager.disconnect(websocket)
            logger.info("클라이언트 연결 종료 (RuntimeError)")
        else:
            logger.error(f"WebSocket 런타임 오류: {str(e)}")
            manager.disconnect(websocket)
            try:
                await websocket.close()
            except:
                pass
    except Exception as e:
        logger.error(f"WebSocket 오류: {str(e)}")
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass
