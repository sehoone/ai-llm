from typing import Any, Dict, List
from dotenv import load_dotenv
from langchain.chains.retrieval import create_retrieval_chain

load_dotenv()

from langchain import hub
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_pinecone import PineconeVectorStore
from langchain.chains.history_aware_retriever import create_history_aware_retriever

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

INDEX_NAME = "langchain-doc-index"

# RAG 를 사용하여 문서 검색 및 질문 응답을 수행하는 함수
def run_llm(query: str, chat_history: List[Dict[str, Any]] = []):
    # OpenAI의 텍스트 임베딩 모델을 사용하여 임베딩 생성
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    # 주어진 인덱스 이름과 임베딩을 사용하여 Pinecone 벡터 스토어 초기화
    docsearch = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    # 특정 매개변수로 채팅 모델 초기화
    chat = ChatOpenAI(verbose=True, temperature=0)

    # 히스토리(캐시) 기반의 검색을 위한 프롬프트 가져오기
    rephrase_prompt = hub.pull("langchain-ai/chat-langchain-rephrase")

    # 랭체인허브에서 검색 QA 채팅 프롬프트 가져오기
    retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
    # 채팅 모델과 가져온 프롬프트를 사용하여 문서 처리 체인 생성
    stuff_documents_chain = create_stuff_documents_chain(chat, retrieval_qa_chat_prompt)

    # 백터DB 검색 체인 생성. 유사성 검색을 수행하고 결과를 반환
    history_aware_retriever = create_history_aware_retriever(
        llm=chat, retriever=docsearch.as_retriever(), prompt=rephrase_prompt
    )
    # 히스토리 기반 검색을 수행하고 결과를 반환
    qa = create_retrieval_chain(
        retriever=history_aware_retriever, combine_docs_chain=stuff_documents_chain
    )

    # 채팅 히스토리를 사용하여 LLM 모델을 호출
    result = qa.invoke(input={"input": query, "chat_history": chat_history})
    print(result)
    return result

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
