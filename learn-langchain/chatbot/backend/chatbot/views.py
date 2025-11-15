import json
import time
from typing import Any, Dict, TypedDict
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from langchain_openai import ChatOpenAI

from chatbot.core import run_llm

# Bedrock 챗봇 함수 import
from chatbot.bedrock_chatbot import run_bedrock_llm

class PromptRequest(TypedDict):
    prompt: str
    
@csrf_exempt
@require_GET
def helloworld(request: HttpRequest) -> JsonResponse:
    data: Dict[str, Any] = json.loads(request.body)
    
    response_data = {
                "message": "Received data successfully",
                "received_data": data
            }
    return JsonResponse(response_data, status=200)

@csrf_exempt
@require_POST
def conversation(request: HttpRequest) -> JsonResponse:
    data: PromptRequest = json.loads(request.body)
    generated_response = run_llm(query=data['prompt'])
    
    response_data = {
                "message": "Received data successfully",
                "received_data": generated_response["answer"]
            }
    return JsonResponse(response_data, status=200)


# Bedrock 챗봇 API 엔드포인트
@csrf_exempt
@require_POST
def bedrock_conversation(request: HttpRequest) -> JsonResponse:
    data: PromptRequest = json.loads(request.body)
    generated_response = run_bedrock_llm(data['prompt'])
    response_data = {
        "message": "Bedrock 응답",
        "received_data": generated_response
    }
    return JsonResponse(response_data, status=200)

# stream응답을 테스트 하기위해 curl로 호출함
# stream example: curl -X POST http://127.0.0.1:8000/chatbot/stream-conversation -H "Content-Type: application/json" -d "{\"prompt\": \"What is the capital of France?\"}"
@csrf_exempt
@require_POST
def stream_conversation(request: HttpRequest) -> StreamingHttpResponse:
    try:
        data: PromptRequest = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    def stream():
        for chunk in run_llm(data['prompt']):
            yield chunk
            # time.sleep(1)

    return StreamingHttpResponse(stream(), content_type='text/plain')

# @csrf_exempt
# @require_GET
# def stream_text(request: HttpRequest) -> StreamingHttpResponse:
#     def stream():
#         texts = ["This is a test message.", "Streaming data in chunks.", "End of stream."]
#         for text in texts:
#             yield text + "\n"
#             time.sleep(1) 
    
#     return StreamingHttpResponse(stream(), content_type='text/plain')

@csrf_exempt
@require_GET
def stream_text(request: HttpRequest) -> StreamingHttpResponse:
    def stream():
        model = ChatOpenAI(model="gpt-4o-mini")
        chunks = []
        for chunk in model.stream("what color is the sky?"):
            yield chunk
            # chunks.append(chunk)
            # print(chunk.content, end="|", flush=True)
    
    return StreamingHttpResponse(stream(), content_type='text/plain')