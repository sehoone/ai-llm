# deploy

V2 `orchestration-v2/deploy`를 계승·단순화할 예정입니다.

## V3에서 바뀌는 점 (ADR-0003)

- **서비스 2개**: `api`(FastAPI) + `web`(Next.js). V2의 platform-server(Java)는 api로 통합되어 사라짐.
- **Keycloak 불필요**: 인증은 **사내 기존 IdP**에 위임. api는 OIDC 토큰 검증만.
- 계승: Nginx(단일 진입점) · PostgreSQL+pgvector · 관측 스택(Prometheus/Grafana/Loki/Langfuse).

## 현재 포함됨

- `docker-compose.yml` — nginx · web · api · db(pgvector) · prometheus · grafana · cadvisor + **Langfuse 스택**(langfuse-web · langfuse-worker · clickhouse · redis · minio). **platform 서비스 제거**, `app→api` / `llm-admin→web` 리네임, api는 OIDC_* 사용. 상단 `name: orchestration-v3`로 **compose 프로젝트 격리**(v2 `deploy`와 볼륨/컨테이너 충돌 방지).
- `nginx/nginx.conf` — `/api/*` → api 단일 백엔드 직접 프록시(platform 게이트웨이 경유 제거), `/` → web.
- `postgres/init.sql` — llmonl 스키마 + 플랫폼 테이블(users[idp_subject]·api_key·llm_resource). **users에서 hashed_password 제거·idp_subject 추가, refresh_token 테이블 제거**(ADR-0003).
- `postgres/langfuse-db.sql` — Langfuse 전용 `langfuse` DB 생성(앱 `mydb`와 분리, 같은 Postgres 인스턴스). 볼륨 최초 init 시 1회 (ADR-0007).
- `clickhouse/config.xml` — Langfuse v3 ClickHouse 단일노드 cluster 매크로 + 내장 Keeper.
- `prometheus/prometheus.yml` — cadvisor + api /metrics(이식 후 활성).
- `.env.example` — compose 변수 + Langfuse 시크릿.

### 포트 맵
| 서비스 | host 포트 |
|--------|-----------|
| nginx (진입점) | 8060 |
| prometheus | 8063 |
| grafana | 8064 |
| cadvisor | 8065 |
| db (pgvector) | 8066 |
| **langfuse-web (UI)** | **8067** |
| minio console | 8068 |

### Langfuse 사용 (ADR-0007)
1. `deploy/.env`의 `LANGFUSE_NEXTAUTH_SECRET`·`LANGFUSE_SALT`·`LANGFUSE_ENCRYPTION_KEY`를 `openssl rand -hex 32`로 교체.
2. `docker compose up -d` → http://localhost:8067 접속 → 계정·프로젝트 생성 → **public/secret 키 발급**.
3. 키를 `apps/api/.env.production`의 `LANGFUSE_PUBLIC_KEY`/`LANGFUSE_SECRET_KEY`에 넣고 `docker compose up -d api` 재기동. (`LANGFUSE_HOST=http://langfuse-web:3000` — 컨테이너 내부 주소)
4. 키가 비어 있으면 api는 관측을 **자동 비활성**(무해). LLM 트레이스는 LLM 도메인 이식 후 `engine/observability`를 통해 수집됨.

## 아직 이식 안 됨 (후속)

- **LLM 도메인 테이블** — chat·rag·agent·workflow·meeting 포팅 시 V2 init.sql의 orchestrator 섹션을 `postgres/init.sql`에 추가.
- **Loki/Promtail** — V2에서 그대로 carry (언어 무관 인프라).
- **k8s/** HA 매니페스트 — 2서비스 기준 재작성.
- **Keycloak 없음** — 인증은 사내 기존 IdP 사용.
