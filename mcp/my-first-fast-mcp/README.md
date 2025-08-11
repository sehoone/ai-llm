# my-first-fast-mcp

## 로컬 개발 환경 구축 및 실행 방법

### 1. [uv](https://docs.astral.sh/uv/) 설치

uv는 Python 패키지 관리 도구. 아래 명령어로 설치:

```powershell
pip install uv
```

### 2. 의존성 설치

아래 명령어로 프로젝트 의존성을 설치:

```powershell
uv pip install -r requirements.txt
```

또는 pyproject.toml 기반 설치:

```powershell
uv pip install -r pyproject.toml
```

### 3. MCP 서버 실행

아래 명령어로 MCP 서버를 실행할 수 있습니다:

```powershell
python main.py
```

### claud desktop 설정예시
```json
{
  "mcpServers": {
    "fastmcp": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\dev\\workspace\\ai-llm\\mcp\\my-first-fast-mcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

