"""Voice evaluation API endpoints.

This module provides endpoints for voice evaluation, including WebSocket connections
for real-time conversation and evaluation.
"""

import json
from typing import Dict, List, Any
import httpx

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from src.voice_evaluation.schemas.voice_evaluation_schema import ConversationResponse, EvaluationRequest, EvaluationResponse
from src.voice_evaluation.services.audio_service import AudioService
from src.voice_evaluation.services.evaluation_service import EvaluationService
from src.common.config import settings
from src.common.logging import logger

router = APIRouter()

evaluation_service = EvaluationService()
audio_service = AudioService()


class ConnectionManager:
    """Manages WebSocket connections for voice evaluation."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.conversation_histories: Dict[WebSocket, List[Dict[str, str]]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.conversation_histories[websocket] = []
        logger.info("client_connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.conversation_histories:
            del self.conversation_histories[websocket]
        logger.info("client_disconnected", total_connections=len(self.active_connections))

    def get_history(self, websocket: WebSocket) -> List[Dict[str, str]]:
        return self.conversation_histories.get(websocket, [])

    def add_to_history(self, websocket: WebSocket, role: str, content: str):
        if websocket not in self.conversation_histories:
            self.conversation_histories[websocket] = []
        self.conversation_histories[websocket].append({"role": role, "content": content})


manager = ConnectionManager()


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_text(request: EvaluationRequest):
    """Evaluate text-based conversation."""
    try:
        evaluation_result = await evaluation_service.evaluate_conversation(
            text=request.text,
            conversation_history=request.conversation_history,
        )
        return EvaluationResponse(**evaluation_result)
    except Exception as e:
        logger.error("evaluation_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error occurred during evaluation: {str(e)}")


@router.get("/azure-avatar-token")
async def get_azure_avatar_token():
    """Get Azure TTS Avatar token."""
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Service configuration missing.")

    fetch_token_url = f"https://{settings.AZURE_SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(fetch_token_url, headers={"Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY})
            if response.status_code != 200:
                logger.error("azure_avatar_token_failed", status_code=response.status_code)
                raise HTTPException(status_code=response.status_code, detail="Failed to issue Azure Avatar Token")
            return response.json()
        except HTTPException:
            raise
        except Exception as e:
            logger.error("azure_avatar_token_request_error", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error during Azure Avatar Token request: {str(e)}")


@router.get("/speech-token")
async def get_speech_token():
    """Get Azure Speech Service authentication token."""
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Service configuration missing.")

    fetch_token_url = f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(fetch_token_url, headers={"Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY})
            if response.status_code != 200:
                logger.error("speech_token_failed", status_code=response.status_code)
                raise HTTPException(status_code=response.status_code, detail="Failed to issue Speech Token")
            return {"token": response.text, "region": settings.AZURE_SPEECH_REGION}
        except HTTPException:
            raise
        except Exception as e:
            logger.error("speech_token_request_error", error=str(e), exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error during Speech Token request: {str(e)}")


@router.websocket("/ws/conversation")
async def websocket_conversation(websocket: WebSocket):
    """Real-time voice conversation and evaluation WebSocket."""
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive()

            if "text" in data:
                message_data = json.loads(data["text"])
                message_type = message_data.get("type", "text")

                if message_type == "text":
                    user_text = message_data.get("text", "")
                    if not user_text:
                        continue

                    logger.info("user_text_received", text_length=len(user_text))

                    history = manager.get_history(websocket)
                    is_start_message = user_text.strip() == "모의평가 시작"

                    ai_response = await evaluation_service.generate_response(
                        user_input=user_text, conversation_history=history
                    )

                    if not is_start_message:
                        manager.add_to_history(websocket, "user", user_text)
                    manager.add_to_history(websocket, "assistant", ai_response)

                    logger.info("tts_generation_start", response_length=len(ai_response))
                    audio_data = await audio_service.text_to_speech(ai_response)
                    audio_base64 = None
                    if audio_data:
                        audio_base64 = audio_service.audio_to_base64(audio_data)
                        logger.info("tts_generation_complete", base64_length=len(audio_base64))
                    else:
                        logger.warning("tts_generation_failed")

                    response = ConversationResponse(text=ai_response, audio=audio_base64, evaluation=None)
                    logger.info("sending_response", text_chars=len(ai_response), has_audio=audio_base64 is not None)
                    await websocket.send_json(response.dict())

                elif message_type == "audio":
                    audio_base64 = message_data.get("audio_data", "")
                    audio_format = message_data.get("format", "wav")
                    if not audio_base64:
                        continue

                    logger.info("user_audio_received")
                    audio_bytes = audio_service.base64_to_audio(audio_base64)
                    user_text = await audio_service.speech_to_text(audio_bytes, audio_format)

                    if not user_text:
                        await websocket.send_json({"error": "Could not convert speech to text."})
                        continue

                    logger.info("stt_result", text_length=len(user_text))

                    pronunciation_result = await audio_service.assess_pronunciation(audio_bytes, user_text)
                    if pronunciation_result:
                        logger.info("pronunciation_assessment_complete", score=pronunciation_result.get("pronunciation_score", 0))

                    history = manager.get_history(websocket)
                    ai_response = await evaluation_service.generate_response(user_input=user_text, conversation_history=history)

                    manager.add_to_history(websocket, "user", user_text)
                    manager.add_to_history(websocket, "assistant", ai_response)

                    audio_data = await audio_service.text_to_speech(ai_response)
                    audio_base64 = audio_service.audio_to_base64(audio_data) if audio_data else None

                    response = ConversationResponse(text=ai_response, audio=audio_base64, evaluation=None)
                    await websocket.send_json({"type": "user_text", "text": user_text, "pronunciation": pronunciation_result})
                    logger.info("pronunciation_data_sent", has_result=pronunciation_result is not None)
                    await websocket.send_json(response.dict())

                elif message_type == "reset":
                    manager.conversation_histories[websocket] = []
                    await websocket.send_json({"status": "reset", "message": "Conversation history reset."})

                elif message_type == "evaluate":
                    logger.info("evaluation_request_received")
                    history = manager.get_history(websocket)
                    if not history:
                        await websocket.send_json({"error": "No conversation history to evaluate."})
                        continue

                    evaluation_result = await evaluation_service.evaluate_conversation(
                        text="", conversation_history=history
                    )
                    response = ConversationResponse(
                        text="", audio=None, evaluation=EvaluationResponse(**evaluation_result)
                    )
                    await websocket.send_json(response.dict())
                    logger.info("evaluation_result_sent")

            elif "bytes" in data:
                audio_bytes = data["bytes"]
                logger.info("binary_audio_received")

                user_text = await audio_service.speech_to_text(audio_bytes)
                if not user_text:
                    await websocket.send_json({"error": "Could not convert speech to text."})
                    continue

                logger.info("stt_result", text_length=len(user_text))

                pronunciation_result = await audio_service.assess_pronunciation(audio_bytes, user_text)
                if pronunciation_result:
                    logger.info("pronunciation_assessment_complete", score=pronunciation_result.get("pronunciation_score", 0))

                history = manager.get_history(websocket)
                ai_response = await evaluation_service.generate_response(user_input=user_text, conversation_history=history)

                manager.add_to_history(websocket, "user", user_text)
                manager.add_to_history(websocket, "assistant", ai_response)

                audio_data = await audio_service.text_to_speech(ai_response)
                audio_base64 = audio_service.audio_to_base64(audio_data) if audio_data else None

                response = ConversationResponse(text=ai_response, audio=audio_base64, evaluation=None)
                await websocket.send_json({"type": "user_text", "text": user_text, "pronunciation": pronunciation_result})
                logger.info("pronunciation_data_sent", has_result=pronunciation_result is not None)
                await websocket.send_json(response.dict())

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("client_disconnected_clean")
    except RuntimeError as e:
        manager.disconnect(websocket)
        if "disconnect message has been received" in str(e) or "Unexpected ASGI message" in str(e):
            logger.info("client_disconnected_runtime")
        else:
            logger.error("websocket_runtime_error", error=str(e), exc_info=True)
        try:
            await websocket.close()
        except Exception:
            pass
    except Exception as e:
        logger.error("websocket_error", error=str(e), exc_info=True)
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
