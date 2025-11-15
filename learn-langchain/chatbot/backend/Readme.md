# chatbot backend(Django)

### install
1. 가상환경 생성
```
# Windows에서 uv 설치 (이미 설치된 경우 건너뛰기)
winget install --id=astral-sh.uv -e

# 프로젝트 의존성 설치
uv sync

# 또는 개별 패키지 설치
uv add fastmcp httpx pydantic uvicorn
```

2. Django 서버 run
```
python manage.py runserver
```