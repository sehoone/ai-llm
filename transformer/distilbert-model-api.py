from transformers import AutoModelForQuestionAnswering, AutoTokenizer
from flask import Flask, request, jsonify
from flask_ngrok import run_with_ngrok
import torch

# 모델 및 토크나이저 로드. 허깅페이스에서 필요한 모델을 사용할 수 있음
model_id = 'distilbert-base-uncased-distilled-squad' # DistilBERT는 BERT 모델의 경량화 모델
model = AutoModelForQuestionAnswering.from_pretrained(model_id)
tokenizer = AutoTokenizer.from_pretrained(model_id)

# Flask 앱 설정
app = Flask(__name__)
run_with_ngrok(app)  # ngrok을 사용하여 로컬 서버 run

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    question = data['question'] # 질문
    context = data['context'] # 질문에 대한 답변을 찾을 문맥
    
    # 입력 텍스트 토큰화
    inputs = tokenizer(question, context, return_tensors='pt')
    
    # 모델 예측
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Start and end logits에서 가장 높은 값을 가진 인덱스 추출
    answer_start = torch.argmax(outputs.start_logits)
    answer_end = torch.argmax(outputs.end_logits) + 1
    
    # 원본 텍스트에서 정답 추출
    answer = tokenizer.convert_tokens_to_string(tokenizer.convert_ids_to_tokens(inputs.input_ids[0][answer_start:answer_end]))
    
    # 결과 반환
    result = {'answer': answer}
    return jsonify(result)

if __name__ == '__main__':
    app.run()