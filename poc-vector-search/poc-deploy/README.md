# poc-vector-search 배포 가이드

## 아키텍처

```
브라우저
  │
  ▼
Nginx :80  (poc-nginx)
  │
  ├─ /api/* ──────▶  Spring Boot :8080  (poc-vector-server)
  │                         │
  │                         ▼
  │                  PostgreSQL :5432  (poc-postgres)
  │                   + pgvector 확장
  │
  └─ /*  ─────────▶  Next.js :3000  (poc-admin-front)
```

## 사전 요구사항

| 항목 | 버전 |
|------|------|
| Docker | 24+ |
| Docker Compose | v2 (plugin 방식) |
| OpenAI API Key | `text-embedding-3-small` 사용 권한 |

---

## 빠른 시작

### 1. 환경 변수 설정

```bash
cd poc-vector-search/poc-deploy
cp .env.example .env
```

`.env` 파일을 열고 필수 값을 채웁니다:

```dotenv
# Azure OpenAI (필수)
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=text-embedding-3-small  # Azure에서 만든 배포 이름
AZURE_OPENAI_API_VERSION=2024-02-01

# 권장: 변경
POSTGRES_PASSWORD=your-pass
JWT_SECRET=32자-이상-시크릿
NGINX_PORT=80  # 포트 충돌 시 변경 (예: 8080)
```

### 2. 배포

```bash
bash deploy.sh up
```

빌드 순서: `postgres` → `vector-server` → `admin-front` → `nginx`  
첫 빌드는 Gradle 다운로드, npm install 등으로 **5~10분** 소요됩니다.

### 3. DB 스키마 초기화 (최초 1회)

```bash
bash deploy.sh init-db
```

> postgres 컨테이너가 완전히 기동된 후 실행해야 합니다. `bash deploy.sh ps` 로 상태를 확인하세요.

### 4. 접속

| 항목 | 값 |
|------|-----|
| URL | `http://localhost` (또는 `http://서버IP`) |
| 이메일 | `admin@poc.com` |
| 비밀번호 | `admin1234` |

---

## deploy.sh 명령어

```bash
bash deploy.sh up                  # 전체 빌드 & 시작
bash deploy.sh init-db             # DB 스키마 초기화 (최초 1회 수동 실행)
bash deploy.sh down                # 컨테이너 종료 (볼륨 유지)
bash deploy.sh restart             # 재빌드 후 재시작
bash deploy.sh logs                # 전체 로그 스트리밍
bash deploy.sh logs vector-server  # 특정 서비스 로그
bash deploy.sh ps                  # 컨테이너 상태 확인
bash deploy.sh clean               # 컨테이너 + 볼륨 완전 삭제
```

Docker Compose를 직접 사용할 수도 있습니다:

```bash
# 특정 서비스만 재빌드
docker compose --env-file .env up -d --build vector-server

# 실행 중인 컨테이너 목록
docker compose ps

# Spring Boot 로그
docker compose logs -f vector-server

# Next.js 로그
docker compose logs -f admin-front
```

---

## 포트 충돌 시

`.env`에서 `NGINX_PORT`를 변경합니다:

```dotenv
NGINX_PORT=8060
```

이후 `bash deploy.sh restart` 실행.

---

## DB 초기화 방식

스키마 생성 책임은 환경에 따라 명확히 분리됩니다:

| 환경 | 스키마 생성 주체 |
|------|-----------------|
| **Docker 배포** | `poc-deploy/init.sql` — **수동 실행** 필요 |
| **로컬 개발** | `vector-server/src/main/resources/schema.sql` (Spring Boot 매 기동마다 자동) |

Docker 배포 시 Spring Boot의 SQL init은 `SPRING_SQL_INIT_MODE=never`로 비활성화되어 있으므로, postgres 컨테이너 기동 후 아래 명령으로 스키마를 직접 생성해야 합니다:

```bash
bash deploy.sh init-db
```

또는 psql 직접 실행:

```bash
docker exec -i poc-postgres psql -U postgres -d poc_vector < init.sql
```

`init.sql`이 생성하는 항목:
- `vector` 확장 (pgvector)
- `users` 테이블 + 초기 admin 계정 (`admin@poc.com` / `admin1234`)
- `documents` 테이블 + IVFFlat cosine 인덱스

### DB 볼륨 초기화 (데이터 전체 삭제 후 재생성)

```bash
bash deploy.sh clean   # 볼륨 포함 전체 삭제
bash deploy.sh up      # 재배포 → init.sql 재실행
```

> 저장된 임베딩 데이터가 모두 삭제되므로 주의하세요.

---

## 트러블슈팅

### vector-server가 계속 재시작되는 경우

DB healthcheck가 통과되기 전에 Spring Boot가 먼저 시작을 시도할 수 있습니다. 잠시 기다리거나 로그를 확인합니다:

```bash
docker compose logs -f postgres
docker compose logs -f vector-server
```

### Azure OpenAI API 오류

`vector-server` 로그에서 확인:

```bash
docker compose logs vector-server | grep -i azure
```

`.env`의 `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT_NAME` 값이 올바른지 확인하고, `bash deploy.sh restart` 실행.

Azure 포털에서 확인할 항목:
- **엔드포인트**: Azure OpenAI 리소스 → 키 및 엔드포인트
- **API 키**: 동일 페이지의 KEY1 또는 KEY2
- **배포 이름**: Azure OpenAI Studio → 배포 → 배포 이름 (모델명과 다를 수 있음)

### Next.js 빌드 실패

`admin-front/.env.production`이 Nginx 경유 설정으로 되어 있어야 합니다:

```dotenv
NEXT_PUBLIC_API_URL=
API_URL=http://vector-server:8080
```

### 방화벽 / 원격 서버 접속

`NGINX_PORT`로 설정한 포트를 방화벽에서 허용해야 합니다:

```bash
# Ubuntu/Debian
sudo ufw allow 80/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

---

## 파일 구조

```
poc-deploy/
├── docker-compose.yml   # 전체 스택 정의
├── init.sql             # DB 초기화 (최초 기동 시 1회 실행)
├── nginx.conf           # 리버스 프록시 설정
├── .env.example         # 환경 변수 템플릿
├── .env                 # 실제 환경 변수 (gitignore)
├── .gitignore
├── deploy.sh            # 편의 스크립트
└── README.md
```

관련 Dockerfile:
- `../vector-server/Dockerfile` — Spring Boot 멀티스테이지 빌드 (eclipse-temurin:8)
- `../admin-front/Dockerfile` — Next.js 멀티스테이지 빌드 (node:20-alpine)
