from dotenv import load_dotenv

load_dotenv()

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import ReadTheDocsLoader
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# 임베딩 모델 생성
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def ingest_docs():
    # ReadTheDocsLoader를 사용하여 문서를 로드
    loader = ReadTheDocsLoader("langchain-docs/api.python.langchain.com/en/latest", "utf-8")

    raw_documents = loader.load()
    print(f"loaded {len(raw_documents)} documents")

    # 문서를 split chunking. chunk_size를 너무 작게 잡으면 벡터DB에서 유사성을 수행하기 위해 의미를 못찾게됨. 그렇다고 너무 크게 잡으면 토큰을 많이 사용하여 요청하게됨
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=50)
    documents = text_splitter.split_documents(raw_documents)
    # 문서마다 새로운 URL문자열로 치환
    for doc in documents:
        new_url = doc.metadata["source"]
        new_url = new_url.replace("langchain-docs", "https:/")
        doc.metadata.update({"source": new_url})

    print(f"Going to add {len(documents)} to Pinecone")
    # PineconeVectorStore를 사용하여 백터DB에 저장
    PineconeVectorStore.from_documents(
        documents, embeddings, index_name="langchain-doc-index"
    )
    print("****Loading to vectorstore done ***")


if __name__ == "__main__":
    ingest_docs()
