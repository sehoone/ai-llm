# Docker 배포 가이드

## 파일 구성

```
deploy/
├── Dockerfile                          # 앱 이미지 (Python 3.13-slim + uv, 비root 실행)
├── docker-compose.yml                  # 로컬/개발용
├── docker-compose.prod.yml             # 프로덕션 오버라이드 (리소스 제한, 로그 설정)
├── .env.example                        # 환경변수 템플릿
├── nginx.conf.template                 # Nginx HTTPS 설정 템플릿 (DOMAIN 변수 치환)
├── nginx-http.conf.template            # Nginx HTTP 설정 템플릿 (SSL 없음)
├── loki-config.yml                     # Loki 로그 수집 설정
├── promtail-config.yml                 # Promtail 에이전트 설정
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── loki.yaml               # Loki 데이터소스 자동 등록
└── README.md
```

> 프로젝트 루트의 `.dockerignore`가 빌드 컨텍스트에서 `.git`, `tests/`, `.env*` 등 제외

## 서비스 구성

| 서비스 | 이미지 | 프로필 | 역할 |
|--------|--------|--------|------|
| `postgres` | postgres:16-alpine | 기본 | 데이터베이스 |
| `mcp` | 앱 이미지 | 기본 | MCP 서버 |
| `loki` | grafana/loki:3.4 | `monitoring` | 로그 집계 |
| `promtail` | grafana/promtail:3.4 | `monitoring` | 로그 수집 에이전트 |
| `grafana` | grafana/grafana:11.6 | `monitoring` | 로그 시각화 |
| `nginx` | nginx:1.27-alpine | `nginx` | HTTPS 종단 / 리버스 프록시 |

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

# openssl rand -hex 32
JWT_SECRET_KEY=<랜덤 32바이트 hex>
AUTH_USERS=admin:your_password
```

> `DATABASE_URL` 호스트는 반드시 `postgres` (Docker 서비스명)로 유지.
> `localhost`로 변경 시 컨테이너 간 통신 불가.

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
| Grafana (monitoring 프로필) | http://localhost:3000 |

---

## 프로필별 실행

### 로그 모니터링 스택 포함

```bash
docker compose --profile monitoring up --build
```

- Grafana 초기 로그인: `admin` / `.env`의 `GRAFANA_PASSWORD`
- Loki 데이터소스 → `grafana/provisioning/datasources/loki.yaml`로 **자동 등록** — 별도 설정 불필요
- Loki(3100포트)는 Docker 내부 네트워크에만 노출 — 호스트에서 직접 접근 불가

### nginx 포함 (HTTP / HTTPS)

`.env`의 `NGINX_MODE`로 모드 선택. 기본값은 `https`.

#### HTTP 모드 (SSL 불필요)

```ini
# .env
DOMAIN=your-domain.com
NGINX_MODE=http
```

```bash
docker compose --profile nginx up --build
```

포트 80으로 mcp를 서빙. SSL 인증서 불필요.

#### HTTPS 모드

SSL 인증서 준비:

```bash
# Let's Encrypt (도메인 필요)
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem   deploy/ssl/key.pem

# 또는 자체 서명 인증서 (테스트용)
mkdir -p deploy/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deploy/ssl/key.pem -out deploy/ssl/cert.pem \
  -subj "/CN=localhost"
```

```ini
# .env
DOMAIN=your-domain.com
NGINX_MODE=https
```

```bash
docker compose --profile nginx up --build
```

포트 80 → 443 자동 리다이렉트. nginx 시작 시 `${DOMAIN}`을 `.env` 값으로 치환.

---

## 프로덕션 환경 실행

`docker-compose.prod.yml`을 오버라이드로 추가:

```bash
# 기본 (mcp + postgres + nginx)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile nginx up -d --build

# 모니터링 포함
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --profile nginx --profile monitoring up -d --build
```

프로덕션 오버라이드 내용:
- `mcp`: CPU 1코어·메모리 512MB 제한, 로그 로테이션(10MB × 5)
- `postgres`: 메모리 1GB 제한, 로그 로테이션, 외부 포트 비노출
- `nginx`: 프로필 없이 기본 활성화, `restart: always`

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

`.env`에서 포트 오버라이드:

```ini
MCP_PORT=8001
POSTGRES_PORT=5433
GRAFANA_PORT=3001
```

---

## 주의사항

- `.env`는 git 커밋 금지 (`.gitignore`에 추가되어 있음)
- `POSTGRES_PASSWORD`와 `DATABASE_URL`의 비밀번호는 반드시 일치
- `JWT_SECRET_KEY`는 `openssl rand -hex 32`로 생성한 값 사용
- `AUTH_USERS`의 비밀번호는 평문 또는 bcrypt 해시(`$2b$...`) 모두 지원
- Docker 환경에서는 `APP_ENV` 파일 분리 방식 대신 `.env`로 환경변수 직접 주입
- `mcp` 컨테이너는 비root 사용자(`appuser`, UID 1001)로 실행
