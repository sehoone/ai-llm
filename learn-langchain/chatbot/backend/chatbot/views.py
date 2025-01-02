import json
from typing import Any, Dict, TypedDict
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from chatbot.core import run_llm

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