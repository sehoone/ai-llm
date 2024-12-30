from typing import Set

from backend.core import run_llm
import streamlit as st
from streamlit_chat import message

st.header("Documentation Helper Bot")

# 사용자로부터 입력을 받는 텍스트 입력 필드 생성
prompt = st.text_input("Prompt", placeholder="Enter your prompt here..")

# 세션 상태에 사용자 프롬프트 히스토리가 없으면 빈 리스트로 초기화
if "user_prompt_history" not in st.session_state:
    st.session_state["user_prompt_history"] = []

# 세션 상태에 채팅 응답 히스토리가 없으면 빈 리스트로 초기화
if "chat_answers_history" not in st.session_state:
    st.session_state["chat_answers_history"] = []

# 소스 URL들을 문자열로 변환하는 함수
def create_sources_string(source_urls: Set[str]) -> str:
    if not source_urls:
        return ""
    sources_list = list(source_urls)
    sources_list.sort()
    sources_string = "sources:\n"
    for i, source in enumerate(sources_list):
        sources_string += f"{i+1}. {source}\n"
    return sources_string

# 프롬프트가 입력되었을 때
if prompt:
    with st.spinner("Generating response.."):
        # run_llm 함수를 호출하여 응답 생성
        generated_response = run_llm(query=prompt)
        # 응답에서 소스 문서들의 URL을 추출하여 집합으로 만듦
        sources = set(
            [doc.metadata["source"] for doc in generated_response["source_documents"]]
        )

        # 응답 결과와 소스 URL들을 포맷팅하여 하나의 문자열로 만듦
        formatted_response = (
            f"{generated_response['result']} \n\n {create_sources_string(sources)}"
        )

        # 세션 상태에 사용자 프롬프트와 응답을 추가
        st.session_state["user_prompt_history"].append(prompt)
        st.session_state["chat_answers_history"].append(formatted_response)

# 세션 상태에 저장된 채팅 응답 히스토리가 있을 때
if st.session_state["chat_answers_history"]:
    for generated_response, user_query in zip(
        st.session_state["chat_answers_history"],
        st.session_state["user_prompt_history"],
    ):
        # 사용자 프롬프트와 응답을 채팅 메시지로 표시
        message(user_query, is_user=True)
        message(generated_response)