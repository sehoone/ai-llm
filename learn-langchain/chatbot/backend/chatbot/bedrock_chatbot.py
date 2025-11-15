import os
from langchain_community.llms import Bedrock
from langchain_core.prompts import ChatPromptTemplate

def run_bedrock_llm(user_input: str) -> str:
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    llm = Bedrock(
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        model_id="anthropic.claude-v2"  # 원하는 Bedrock 모델 ID로 변경 가능
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", "너는 친절한 AI 챗봇이야. 질문에 답변해줘."),
        ("user", "{input}")
    ])
    chain = prompt | llm
    response = chain.invoke({"input": user_input})
    return response

if __name__ == "__main__":
    print(run_bedrock_llm("LangChain과 Bedrock 연동 챗봇 예시를 보여줘"))
