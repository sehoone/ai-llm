from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import PromptTemplate
from langchain_pinecone import PineconeVectorStore


from langchain_openai import ChatOpenAI, OpenAIEmbeddings

INDEX_NAME = "langchain-doc-index"

# RAG 를 사용하여 문서 검색 및 질문 응답을 수행하는 함수
def run_llm(query: str, chat_history: List[Dict[str, Any]] = []):
    # OpenAI 임베딩 및 Pinecone 벡터 스토어 초기화
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    docsearch = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    chat = ChatOpenAI(verbose=True, temperature=0, stream=True, model_name="gpt-4o-mini")

    # 명시적 프롬프트 템플릿 정의 (history, context, input 포함)
    prompt_template = (
        "너는 불친절한 AI 챗봇이야.\n"
        "이전 대화 기록:\n{history}\n"
        "관련 문서 내용:\n{context}\n"
        "질문: {input}\n"
        "반말로 답변을 해줘."
    )
    prompt = PromptTemplate.from_template(prompt_template)

    # 벡터 검색
    docs = docsearch.as_retriever().invoke(query)
    context = "\n".join([doc.page_content for doc in docs])

    # 히스토리 텍스트 생성
    history_text = "\n".join([f"{h['role']}: {h['content']}" for h in chat_history]) if chat_history else ""

    # 프롬프트에 context, 질문, 히스토리 포함
    full_prompt = prompt.format(input=query, context=context, history=history_text)
    for chunk in chat.stream(full_prompt):
        # chunk.content 또는 chunk.text 등 실제 응답 필드에 따라 조정
        yield getattr(chunk, "content", str(chunk))

    # # 랭체인허브에서 검색 QA 채팅 프롬프트 가져오기
    # retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
    # # 채팅 모델과 가져온 프롬프트를 사용하여 문서 처리 체인 생성
    # stuff_documents_chain = create_stuff_documents_chain(chat, retrieval_qa_chat_prompt)

    # # 백터DB 검색 체인 생성. 유사성 검색을 수행하고 결과를 반환
    # qa = create_retrieval_chain(
    #     retriever=docsearch.as_retriever(), combine_docs_chain=stuff_documents_chain
    # )
    # result = qa.invoke(input={"input": query})
    # new_result = {
    #     "query": result["input"],
    #     "result": result["answer"],
    #     "source_documents": result["context"],
    # }
    # return new_result

if __name__ == "__main__":
    res = run_llm(query="What is a LangChain Chain?")
    print(res["result"])
