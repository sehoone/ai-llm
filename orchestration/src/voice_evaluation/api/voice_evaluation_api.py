"""Voice evaluation API endpoints.

This module provides endpoints for voice evaluation, including WebSocket connections
for real-time conversation and evaluation.
"""

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

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize service instances
evaluation_service = EvaluationService()
audio_service = AudioService()

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for voice evaluation."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: List[WebSocket] = []
        self.conversation_histories: Dict[WebSocket, List[Dict[str, str]]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to accept.
        """
        await websocket.accept()
        self.active_connections.append(websocket)
        self.conversation_histories[websocket] = []
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket connection.

        Args:
            websocket: The WebSocket connection to disconnect.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.conversation_histories:
            del self.conversation_histories[websocket]
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    def get_history(self, websocket: WebSocket) -> List[Dict[str, str]]:
        """Get conversation history for a connection.

        Args:
            websocket: The WebSocket connection.

        Returns:
            List[Dict[str, str]]: The conversation history.
        """
        return self.conversation_histories.get(websocket, [])
    
    def add_to_history(self, websocket: WebSocket, role: str, content: str):
        """Add a message to the conversation history.

        Args:
            websocket: The WebSocket connection.
            role: The role of the message sender (e.g., user, assistant).
            content: The content of the message.
        """
        if websocket not in self.conversation_histories:
            self.conversation_histories[websocket] = []
        self.conversation_histories[websocket].append({"role": role, "content": content})

manager = ConnectionManager()


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_text(request: EvaluationRequest):
    """Evaluate text-based conversation.

    Args:
        request: The evaluation request containing text and history.

    Returns:
        EvaluationResponse: The evaluation results.

    Raises:
        HTTPException: If an error occurs during evaluation.
    """
    try:
        evaluation_result = await evaluation_service.evaluate_conversation(
            text=request.text,
            conversation_history=request.conversation_history
        )
        return EvaluationResponse(**evaluation_result)
    except Exception as e:
        logger.error(f"Evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error occurred during evaluation: {str(e)}")


@router.get("/azure-avatar-token")
async def get_azure_avatar_token():
    """Get Azure TTS Avatar token.

    Returns:
        dict: The token information.

    Raises:
        HTTPException: If Azure Speech Service settings are missing or token request fails.
    """
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Service configuration missing.")
    
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
                logger.error(f"Failed to issue Azure Avatar Token: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to issue Azure Avatar Token")
                
            return response.json()
        except Exception as e:
            logger.error(f"Error during Azure Avatar Token request: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error during Azure Avatar Token request: {str(e)}")


@router.get("/speech-token")
async def get_speech_token():
    """Get Azure Speech Service authentication token.

    Returns:
        dict: The token and region information.

    Raises:
        HTTPException: If Azure Speech Service settings are missing or token request fails.
    """
    if not settings.AZURE_SPEECH_KEY or not settings.AZURE_SPEECH_REGION:
        raise HTTPException(status_code=500, detail="Azure Speech Service configuration missing.")
    
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
                logger.error(f"Failed to issue Speech Token: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to issue Speech Token")
                
            return {"token": response.text, "region": settings.AZURE_SPEECH_REGION}
        except Exception as e:
            logger.error(f"Error during Speech Token request: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error during Speech Token request: {str(e)}")


@router.websocket("/ws/conversation")
async def websocket_conversation(websocket: WebSocket):
    """Real-time voice conversation and evaluation WebSocket.

    Args:
        websocket: The WebSocket connection.
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive()
            
            # Process text message
            if "text" in data:
                message_data = json.loads(data["text"])
                message_type = message_data.get("type", "text")
                
                if message_type == "text":
                    # Process text input
                    user_text = message_data.get("text", "")
                    if not user_text:
                        continue
                    
                    logger.info(f"Received user text: {user_text}")
                    
                    # Get conversation history
                    history = manager.get_history(websocket)
                    
                    # Check if it's a start message
                    is_start_message = user_text.strip() == "모의평가 시작"
                    
                    # Generate AI response
                    ai_response = await evaluation_service.generate_response(
                        user_input=user_text,
                        conversation_history=history
                    )
                    
                    # Add to history unless it's a start message
                    if not is_start_message:
                        manager.add_to_history(websocket, "user", user_text)
                    manager.add_to_history(websocket, "assistant", ai_response)
                    
                    # Generate TTS
                    logger.info(f"Starting TTS generation: {ai_response[:50]}...")
                    audio_data = await audio_service.text_to_speech(ai_response)
                    audio_base64 = None
                    if audio_data:
                        audio_base64 = audio_service.audio_to_base64(audio_data)
                        logger.info(f"TTS generation complete, Base64 length: {len(audio_base64)}")
                    else:
                        logger.warning("TTS generation failed - audio_data is None")
                    
                    # Send response (without evaluation)
                    response = ConversationResponse(
                        text=ai_response,
                        audio=audio_base64,
                        evaluation=None
                    )
                    
                    logger.info(f"Sending response: text={len(ai_response)} chars, audio={'Yes' if audio_base64 else 'No'}, start_msg={is_start_message}")
                    await websocket.send_json(response.dict())
                    logger.info("Response sent")
                
                elif message_type == "audio":
                    # Process audio input
                    audio_base64 = message_data.get("audio_data", "")
                    audio_format = message_data.get("format", "wav")
                    
                    if not audio_base64:
                        continue
                    
                    logger.info("Received user audio")
                    
                    # STT: Convert audio to text
                    audio_bytes = audio_service.base64_to_audio(audio_base64)
                    user_text = await audio_service.speech_to_text(audio_bytes, audio_format)
                    
                    if not user_text:
                        await websocket.send_json({
                            "error": "Could not convert speech to text."
                        })
                        continue
                    
                    logger.info(f"STT Result: {user_text}")
                    
                    # Perform pronunciation assessment (Azure Speech Service)
                    pronunciation_result = await audio_service.assess_pronunciation(
                        audio_bytes, 
                        user_text
                    )
                    
                    if pronunciation_result:
                        logger.info(f"Pronunciation assessment complete - Score: {pronunciation_result.get('pronunciation_score', 0)}")
                    
                    # Get conversation history
                    history = manager.get_history(websocket)
                    
                    # Generate AI response
                    ai_response = await evaluation_service.generate_response(
                        user_input=user_text,
                        conversation_history=history
                    )
                    
                    # Update history
                    manager.add_to_history(websocket, "user", user_text)
                    manager.add_to_history(websocket, "assistant", ai_response)
                    
                    # Generate TTS
                    audio_data = await audio_service.text_to_speech(ai_response)
                    audio_base64 = None
                    if audio_data:
                        audio_base64 = audio_service.audio_to_base64(audio_data)
                    
                    # Send response (include pronunciation assessment)
                    response = ConversationResponse(
                        text=ai_response,
                        audio=audio_base64,
                        evaluation=None
                    )
                    
                    # Send user text and pronunciation assessment separately
                    await websocket.send_json({
                        "type": "user_text",
                        "text": user_text,
                        "pronunciation": pronunciation_result
                    })
                    
                    logger.info(f"Sending pronunciation data: {pronunciation_result}")
                    
                    await websocket.send_json(response.dict())
                    logger.info("Response sent")
                
                elif message_type == "reset":
                    # Reset conversation history
                    manager.conversation_histories[websocket] = []
                    await websocket.send_json({"status": "reset", "message": "Conversation history reset."})
                
                elif message_type == "evaluate":
                    # Process evaluation request
                    logger.info("Received evaluation request")
                    history = manager.get_history(websocket)
                    
                    if not history or len(history) == 0:
                        await websocket.send_json({
                            "error": "No conversation history to evaluate."
                        })
                        continue
                    
                    # Evaluate based on entire conversation history
                    # Convert conversation to text
                    conversation_text = ""
                    for msg in history:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        conversation_text += f"{role}: {content}\n"
                    
                    # Perform evaluation (pronunciation is already done real-time, so text only)
                    evaluation_result = await evaluation_service.evaluate_conversation(
                        text="",  # Empty text as we evaluate whole conversation
                        conversation_history=history
                    )
                    
                    # Send evaluation result
                    response = ConversationResponse(
                        text="",
                        audio=None,
                        evaluation=EvaluationResponse(**evaluation_result)
                    )
                    await websocket.send_json(response.dict())
                    logger.info("Evaluation result sent")
            
            # Process binary message (raw audio data)
            elif "bytes" in data:
                # Process binary audio data
                audio_bytes = data["bytes"]
                logger.info("Received binary audio data")
                
                # STT: Convert audio to text
                user_text = await audio_service.speech_to_text(audio_bytes)
                
                if not user_text:
                    await websocket.send_json({
                        "error": "Could not convert speech to text."
                    })
                    continue
                
                logger.info(f"STT Result: {user_text}")
                
                # Perform pronunciation assessment (Azure Speech Service)
                pronunciation_result = await audio_service.assess_pronunciation(
                    audio_bytes, 
                    user_text
                )
                
                if pronunciation_result:
                    logger.info(f"Pronunciation assessment complete - Score: {pronunciation_result.get('pronunciation_score', 0)}")
                
                # Get conversation history
                history = manager.get_history(websocket)
                
                # Generate AI response
                ai_response = await evaluation_service.generate_response(
                    user_input=user_text,
                    conversation_history=history
                )
                
                # Update history
                manager.add_to_history(websocket, "user", user_text)
                manager.add_to_history(websocket, "assistant", ai_response)
                
                # Generate TTS
                audio_data = await audio_service.text_to_speech(ai_response)
                audio_base64 = None
                if audio_data:
                    audio_base64 = audio_service.audio_to_base64(audio_data)
                
                # Send response (include pronunciation assessment)
                response = ConversationResponse(
                    text=ai_response,
                    audio=audio_base64,
                    evaluation=None
                )
                
                # Send user text and pronunciation assessment separately
                await websocket.send_json({
                    "type": "user_text",
                    "text": user_text,
                    "pronunciation": pronunciation_result
                })
                
                logger.info(f"Sending pronunciation data: {pronunciation_result}")
                
                await websocket.send_json(response.dict())
                logger.info("Response sent")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")
    except RuntimeError as e:
        if "disconnect message has been received" in str(e) or "Unexpected ASGI message" in str(e):
            manager.disconnect(websocket)
            logger.info("Client disconnected (RuntimeError)")
        else:
            logger.error(f"WebSocket runtime error: {str(e)}")
            manager.disconnect(websocket)
            try:
                await websocket.close()
            except:
                pass
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass
