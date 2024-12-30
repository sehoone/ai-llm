from dotenv import load_dotenv
from langchain.chains.retrieval import create_retrieval_chain

load_dotenv()

from langchain import hub
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_pinecone import PineconeVectorStore

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

INDEX_NAME = "langchain-doc-index"

# RAG 를 사용하여 문서 검색 및 질문 응답을 수행하는 함수
def run_llm(query: str):
    # OpenAI의 텍스트 임베딩 모델을 사용하여 임베딩 생성
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    # 주어진 인덱스 이름과 임베딩을 사용하여 Pinecone 벡터 스토어 초기화
    docsearch = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    # 특정 매개변수로 채팅 모델 초기화
    chat = ChatOpenAI(verbose=True, temperature=0)

    # 랭체인허브에서 검색 QA 채팅 프롬프트 가져오기
    retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
    # 채팅 모델과 가져온 프롬프트를 사용하여 문서 처리 체인 생성
    stuff_documents_chain = create_stuff_documents_chain(chat, retrieval_qa_chat_prompt)

    # 백터DB 검색 체인 생성. 유사성 검색을 수행하고 결과를 반환
    qa = create_retrieval_chain(
        retriever=docsearch.as_retriever(), combine_docs_chain=stuff_documents_chain
    )
    result = qa.invoke(input={"input": query})
    return result


if __name__ == "__main__":
    res = run_llm(query="What is a LangChain Chain?")
    print(res["answer"])
