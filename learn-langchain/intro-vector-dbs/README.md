# intro
- 커스텀 데이터를 백터DB에 저장하고 그 정보로 LLM을 호출처리

### install
1. 가상환경 생성(for windows)
    - 명령어 실행
        ```sh
        pipenv shell
        pipenv install langchain langchain-openai langchain-pinecone langchainhub python-dotenv black
        ```
2. pincorn (백터DB) 인덱스 생성
    - 주소: https://www.pinecone.io/
    - metric: cosine 
    - embedding_model: text-embedding-3-small


### vscode setting
1. 환경변수 설정(launch.json)
 - 왼쪽 탭 > Run and Debug > create a launch.json file 선택
 - envFile 경로 추가
``` json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [

        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env"
        }
    ]
}
```

2. python interpreter 설정
- ctrl + shift + p > python:interpreter 선택 > 가상환경의 python 선택