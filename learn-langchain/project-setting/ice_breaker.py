import os

if __name__ == '__main__':
    print("Hello, World!")
    
    # .env에 선언된 환경변수
    print(os.environ['OPENAI_API_KEY'])