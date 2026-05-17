# Docker 배포 가이드

## 파일 구성

```
deploy/
├── Dockerfile                # 애플리케이션 이미지 (Python 3.13-slim + uv)
├── docker-compose.yml        # 로컬/개발용
├── docker-compose.prod.yml   # 프로덕션 오버라이드 (리소스 제한, 로그 설정)
├── .env.example              # 환경변수 템플릿
├── loki-config.yml           # Loki 로그 수집 설정
├── promtail-config.yml       # Promtail 에이전트 설정
└── README.md
```

## 서비스 구성

| 서비스 | 이미지 | 역할 |
|--------|--------|------|
| `postgres` | postgres:16-alpine | 데이터베이스 |
| `mcp` | 앱 이미지 | MCP 서버 (8000포트) |
| `pgadmin` | dpage/pgadmin4:8 | DB 관리 UI (`--profile admin` 시만 실행) |
| `loki` / `promtail` / `grafana` | Grafana 스택 | 로그 모니터링 (`--profile monitoring` 시만 실행) |

---

## 로컬/개발 환경 실행

### 1. 환경변수 설정

```bash
cd deploy
cp .env.example .env
```

`.env`에서 반드시 수정할 항목:

```ini
POSTGRES_PASSWORD=your_password
DATABASE_URL=postgresql://postgres:your_password@postgres:5432/fastmcp_db
JWT_SECRET_KEY=<openssl rand -hex 32>
AUTH_USERS=admin:your_password
```

> `DATABASE_URL`의 호스트는 반드시 `postgres` (docker 서비스명)로 유지하세요.  
> `localhost`로 바꾸면 컨테이너 간 통신이 불가합니다.

### 2. 빌드 및 실행

```bash
# deploy/ 디렉토리에서 실행
docker compose up --build
```

시작 순서:
1. `postgres` 기동 — 최초 실행 시 `scripts/schema.sql`로 테이블 자동 생성 후 healthcheck 통과
2. `mcp` 서버 기동

### 3. 접속 확인

| 서비스 | URL |
|--------|-----|
| MCP 엔드포인트 | http://localhost:8000/mcp |
| 헬스체크 | http://localhost:8000/health |
| pgAdmin (선택) | http://localhost:5050 |

### 4. pgAdmin 포함 실행 (선택)

```bash
docker compose --profile admin up --build
```

pgAdmin 초기 로그인: `.env`의 `PGADMIN_EMAIL` / `PGADMIN_PASSWORD`

---

## 프로덕션 환경 실행

`docker-compose.prod.yml`을 오버라이드로 추가합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

프로덕션 오버라이드 내용:
- `mcp`: CPU 1코어·메모리 512MB 제한, 로그 로테이션(10MB × 5)
- `postgres`: 메모리 1GB 제한, 로그 로테이션, 외부 포트 비노출

---

## 유용한 명령어

```bash
# 실시간 로그
docker compose logs -f mcp

# 컨테이너 쉘 접속
docker compose exec mcp bash

# PostgreSQL 접속
docker compose exec postgres psql -U postgres -d fastmcp_db

# 서비스 중지 (볼륨 유지)
docker compose down

# 서비스 중지 + 볼륨 삭제 (데이터 초기화)
docker compose down -v

# 이미지 재빌드
docker compose build --no-cache mcp
```

---

## 포트 충돌 시

`.env`에서 포트를 오버라이드합니다.

```ini
MCP_PORT=8001
POSTGRES_PORT=5433
PGADMIN_PORT=5051
```

---

## 주의사항

- `.env`는 절대 git에 커밋하지 마세요 (`.gitignore`에 추가되어 있습니다).
- `POSTGRES_PASSWORD`와 `DATABASE_URL`의 비밀번호는 반드시 일치해야 합니다.
- `DATABASE_URL` 호스트는 컨테이너 내부에서 `postgres` (서비스명)을 사용합니다.
- Docker 환경에서는 `APP_ENV` 파일 분리 방식 대신 `.env`로 환경변수를 직접 주입합니다.
