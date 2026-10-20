# deploy

V2 `orchestration-v2/deploy`를 계승·단순화할 예정입니다.

## V3에서 바뀌는 점 (ADR-0003)

- **서비스 2개**: `api`(FastAPI) + `web`(Next.js). V2의 platform-server(Java)는 api로 통합되어 사라짐.
- **Keycloak 불필요**: 인증은 **사내 기존 IdP**에 위임. api는 OIDC 토큰 검증만.
- 계승: Nginx(단일 진입점) · PostgreSQL+pgvector · 관측 스택(Prometheus/Grafana/Loki/Langfuse).

## 현재 포함됨

- `docker-compose.yml` — nginx · web · api · db(pgvector) · prometheus · grafana · cadvisor. **platform 서비스 제거**, `app→api` / `llm-admin→web` 리네임, api는 OIDC_* 사용.
- `nginx/nginx.conf` — `/api/*` → api 단일 백엔드 직접 프록시(platform 게이트웨이 경유 제거), `/` → web.
- `postgres/init.sql` — llmonl 스키마 + 플랫폼 테이블(users[idp_subject]·api_key·llm_resource). **users에서 hashed_password 제거·idp_subject 추가, refresh_token 테이블 제거**(ADR-0003).
- `prometheus/prometheus.yml` — cadvisor + api /metrics(이식 후 활성).
- `.env.example` — compose 변수.

## 아직 이식 안 됨 (후속)

- **LLM 도메인 테이블** — chat·rag·agent·workflow·meeting 포팅 시 V2 init.sql의 orchestrator 섹션을 `postgres/init.sql`에 추가.
- **Langfuse 스택** (clickhouse·redis·minio·langfuse·langfuse-worker) · **Loki/Promtail** — V2에서 그대로 carry (언어 무관 인프라).
- **k8s/** HA 매니페스트 — 2서비스 기준 재작성.
- **Keycloak 없음** — 인증은 사내 기존 IdP 사용.
