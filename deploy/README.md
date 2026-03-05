# Deploy

`orchestration` (FastAPI 백엔드)와 `llm-admin` (Next.js 프론트엔드)을 한 번에 Docker로 배포합니다.
Nginx가 단일 진입점(:8060)으로 두 서비스를 라우팅합니다.

## 디렉토리 구조

```
deploy/
├── docker-compose.yml   # 전체 서비스 정의
├── nginx/
│   └── nginx.conf       # 리버스 프록시 설정
├── deploy.sh            # 배포 스크립트
├── stop.sh              # 중지 스크립트
└── logs.sh              # 로그 조회 스크립트
```

## 노출 포트

| 포트 | 서비스 | 설명 |
|------|--------|------|
| `8060` | nginx | 프론트엔드 / API 단일 진입점 |
| `5432` | db | PostgreSQL (환경변수 `POSTGRES_PORT`로 변경 가능) |

### 트래픽 흐름

```
외부 요청
    │
    ▼
:8060 (nginx)
    ├── /api/*  →  orchestration:8000  (FastAPI)
    └── /*      →  llm-admin:3000      (Next.js)
```

## 사전 준비

환경변수 파일이 존재해야 합니다.

```bash
# API 서버 환경변수
orchestration/.env.production

# 프론트엔드 환경변수
admin/llm-admin/.env.production
```

각 경로의 `.env.example`을 복사해서 생성합니다.

```bash
cp orchestration/.env.example orchestration/.env.production
cp admin/llm-admin/.env.example admin/llm-admin/.env.production
```

## 배포

```bash
# production 배포 (기본값)
./deploy/deploy.sh

# 환경 지정
./deploy/deploy.sh production
./deploy/deploy.sh staging
./deploy/deploy.sh development
```

## 중지

```bash
./deploy/stop.sh

# 환경 지정
./deploy/stop.sh production
```

## 로그 조회

```bash
# 전체 서비스 로그
./deploy/logs.sh

# 특정 서비스 로그
./deploy/logs.sh app          # FastAPI
./deploy/logs.sh llm-admin    # Next.js
./deploy/logs.sh nginx        # Nginx
./deploy/logs.sh db           # PostgreSQL

# 환경 지정
./deploy/logs.sh app staging
```

## 서비스 상태 확인

```bash
cd deploy
docker compose ps
```
