# FastMCP API base프# 실제 API 데이터를 사용하려면 `.env` 파일을 생성하고 API 키를 설정:

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일에 실제 API 키 입력
OPENWEATHER_API_KEY=your_openweather_api_key_here
NEWS_API_KEY=your_newsapi_key_here
DATABASE_URL=postgresql://postgres:password@localhost:5432/fastmcp_db
```

**API 키 발급 방법:**
- OpenWeatherMap: https://openweathermap.org/api (무료)
- NewsAPI: https://newsapi.org/ (무료)

**데이터베이스 설정:**
- PostgreSQL 설치 후 데이터베이스 생성 필요
- DATABASE_URL을 실제 데이터베이스 연결 정보로 수정 설정

### 1. uv를 사용한 설치 (권장)

```bash
# Windows에서 uv 설치 (이미 설치된 경우 건너뛰기)
winget install --id=astral-sh.uv -e

# 프로젝트 의존성 설치
uv sync

# 또는 개별 패키지 설치
uv add fastmcp httpx pydantic uvicorn
```

### 2. 환경변수 설정 (선택사항)

실제 API 데이터를 사용하려면 `.env` 파일을 생성하고 API 키를 설정:

```bash
# .env.example을 .env로 복사
cp .env.example .env

# .env 파일에 실제 API 키 입력
OPENWEATHER_API_KEY=your_openweather_api_key_here
NEWS_API_KEY=your_newsapi_key_here
```

**API 키 발급 방법:**
- OpenWeatherMap: https://openweathermap.org/api (무료)
- NewsAPI: https://newsapi.org/ (무료)

## 실행 방법

### 1. 통합 실행기 사용 (권장)
```bash
# 통합 서버 실행
uv run python main.py server integrated

# 날씨 서버 실행
uv run python main.py server weather

# 뉴스 서버 실행
uv run python main.py server news

# 데이터베이스 서버 실행
uv run python main.py server database

# 간단한 테스트
uv run python main.py test simple

# 상세 테스트
uv run python main.py test tools

# 데이터베이스 테스트
uv run python main.py test database

# 대화형 테스트
uv run python main.py test interactive

# 데이터베이스 초기화
uv run python main.py init database

# 클라이언트 데모
uv run python main.py demo client

# SQL 쿼리 데모
uv run python main.py demo sql
```

### 2. 직접 실행
```bash
# 간단한 테스트
uv run python tests/simple_test.py

# 통합 MCP 서버 실행
uv run python src/integrated_server.py

# 개별 서버 실행
uv run python src/weather_mcp_server.py
uv run python src/news_mcp_server.py
uv run python src/database_mcp_server.py

# 클라이언트 데모
uv run python examples/client_demo.py

# SQL 쿼리 데모
uv run python examples/sql_query_demo.py

# 대화형 테스트
uv run python tests/test_tools.py interactive
```

## 프로젝트 구조

```
fastmcp-base/
├── main.py                     # 통합 실행기 (권장 실행 방법)
├── pyproject.toml              # 프로젝트 설정 및 의존성
├── uv.lock                     # uv 잠금 파일
├── .env.example               # 환경변수 예제
├── README.md                  # 프로젝트 문서
├── 
├── src/                       # MCP 서버 소스 코드
│   ├── __init__.py
│   ├── integrated_server.py   # 통합 MCP 서버 (모든 기능)
│   ├── weather_mcp_server.py  # 날씨 전용 MCP 서버
│   ├── news_mcp_server.py     # 뉴스 전용 MCP 서버
│   ├── database_mcp_server.py # 데이터베이스 MCP 서버
│   └── database_config.py     # 데이터베이스 설정
├── 
├── examples/                  # 사용 예제
│   ├── __init__.py
│   └── client_demo.py         # MCP 클라이언트 데모
├── 
├── tests/                     # 테스트 파일
│   ├── __init__.py
│   ├── simple_test.py         # 기본 기능 테스트
│   ├── test_tools.py          # 상세 도구 테스트
│   └── test_database.py       # 데이터베이스 테스트
├── 
├── scripts/                   # 설정 스크립트
│   ├── README.md
│   ├── setup_uv.bat          # Windows uv 설정 스크립트
│   └── setup_uv.sh           # Linux/Mac uv 설정 스크립트
└── .venv/                     # uv 가상환경
```

## 기능

### 통합 MCP 서버 (integrated_server.py)
- **get_weather**: 특정 도시의 현재 날씨 조회
- **get_forecast**: 날씨 예보 조회
- **get_news**: 뉴스 조회 (키워드, 카테고리 검색)
- **get_time**: 현재 시간 조회
- **calculate**: 수학 계산 수행
- **ping_server**: 서버 응답 시간 측정

### Weather MCP Server
- 위치별 날씨 정보 조회
- 날씨 예보 조회 (최대 5일)
- 기상 경보 조회

### News MCP Server
- 최신 뉴스 헤드라인
- 카테고리별 뉴스 검색
- 키워드별 뉴스 검색
- 뉴스 소스 목록 조회

### Database MCP Server
- **User 관리**: 사용자 생성, 조회, 업데이트, 삭제
- **Post 관리**: 게시물 생성, 조회, 업데이트, 삭제
- **검색 기능**: 사용자 및 게시물 검색
- **통계 기능**: 사용자/게시물 통계 조회
- **원시 SQL**: 직접 SQL 쿼리 실행 및 스키마 조회
- **분석 쿼리**: 미리 정의된 분석 쿼리 실행
- **데이터베이스**: PostgreSQL + SQLAlchemy ORM

## 사용 예제

### 1. MCP 클라이언트에서 사용
```python
# 날씨 조회
result = await mcp_client.call_tool("get_weather", city="Seoul", country_code="KR")

# 뉴스 검색
result = await mcp_client.call_tool("get_news", query="AI", count=5)

# 계산기
result = await mcp_client.call_tool("calculate", expression="2 + 3 * 4")

# 사용자 생성 (데이터베이스)
result = await mcp_client.call_tool("create_user", username="john", email="john@example.com")

# 게시물 생성 (데이터베이스)
result = await mcp_client.call_tool("create_post", user_id=1, title="Hello", content="World")

# 원시 SQL 쿼리 실행
result = await mcp_client.call_tool("execute_raw_query", query="SELECT COUNT(*) FROM users")

# 테이블 스키마 조회
result = await mcp_client.call_tool("get_table_schema", table_name="users")

# 분석 쿼리 실행
result = await mcp_client.call_tool("execute_analytics_query", query_type="user_activity")
```

### 2. 직접 함수 호출
```python
from src.integrated_server import get_weather, get_news, calculate

# 비동기 함수 호출
weather = await get_weather("Seoul", "KR")
news = await get_news("Python", count=3)
calc_result = await calculate("100 / 4")
```

## 개발

### 새로운 도구 추가
```python
@mcp.tool()
async def new_tool(param: str) -> dict:
    """새로운 도구 설명"""
    # 도구 로직 구현
    return {"result": "success"}
```

### 테스트 실행
```bash
# 통합 실행기 사용 (권장)
uv run python main.py test simple
uv run python main.py test tools
uv run python main.py test interactive

# 직접 실행
uv run python tests/simple_test.py
uv run python tests/test_tools.py
uv run python tests/test_tools.py weather
uv run python tests/test_tools.py news
uv run python tests/test_tools.py integrated
```

## 문제 해결

### 1. uv 명령을 찾을 수 없는 경우
```bash
# Windows
winget install --id=astral-sh.uv -e

# 환경변수 새로고침
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
```

### 2. API 키 없이 사용
- 모든 서버는 API 키 없이도 데모 데이터로 동작합니다
- 실제 데이터가 필요한 경우에만 API 키를 설정하세요

### 3. 데이터베이스 서버 사용
```bash
# 1. PostgreSQL 설치 및 데이터베이스 생성
# Windows에서 PostgreSQL 설치: https://www.postgresql.org/download/windows/

# 2. 필요한 테이블 생성 (SQL 스크립트 직접 실행)
# users 테이블과 posts 테이블을 미리 생성해야 합니다
# PostgreSQL에서 다음 명령으로 스크립트 실행:
# psql -d fastmcp_db -f scripts/create_tables.sql

# 3. 환경변수 설정
# .env 파일에 DATABASE_URL 추가
DATABASE_URL=postgresql://postgres:password@localhost:5432/fastmcp_db

# 4. 데이터베이스 연결 테스트
uv run python main.py init database

# 5. 데이터베이스 서버 실행
uv run python main.py server database

# 6. 데이터베이스 테스트
uv run python main.py test database
```

### 4. 패키지 설치 문제
```bash
# 캐시 정리 후 재설치
uv cache clean
uv sync --reinstall
```
