import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

if __name__ == '__main__':
    # 1. 텍스트 데이터 불러오기
    # 2. 텍스트 데이터를 적절한 크기로 나누기
    # 3. OpenAIEmbeddings 을 사용하여 데이터 임베딩
    # 4. PineconeVectorStore 를 사용하여 임베딩된 데이터를 Pinecone에 저장

    # 1. 텍스트 데이터를 불러오기
    print("Ingesting...")
    loader = TextLoader("mediumblog1.txt", encoding='utf-8')
    document = loader.load()

    # 2. 텍스트 데이터를 적절한 크기로 나누기
    print("splitting...")
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = text_splitter.split_documents(document)
    print(f"created {len(texts)} chunks")

    # 3. 임베팅모델을 사용하여 데이터 임베딩
    embeddings = OpenAIEmbeddings(openai_api_key=os.environ.get("OPENAI_API_KEY"))

    # 4. PineconeVectorStore 를 사용하여 임베딩된 데이터를 Pinecone에 저장
    print("ingesting...")
    PineconeVectorStore.from_documents(texts, embeddings, index_name=os.environ['INDEX_NAME'])
    print("finish")
