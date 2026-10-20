# mcp-server (템플릿)

orchestration-v3에서 **외부 시스템 연동용 MCP 서버**를 추가할 때 복사해 쓰는 스타터 템플릿.

- **v3 컨벤션 네이티브**: uv + ruff + import-linter, 단일 `.env`, `llmonl` 스키마, **도메인 수직 슬라이스**(`apps/api`와 동일 멘탈 모델).
- **인증은 IdP 위임(ADR-0003)**: 자체 토큰 발급 없음 — IdP 발급 토큰을 **JWKS로 검증만**.
- **도메인 하나가 여러 외부 시스템을 조합**: 샘플 도메인이 REST + DB를 함께 사용.
- **데모 모드**: API 키 없이 클론 즉시 실행·테스트.

## 조직 축 = 도메인 (domains-lite)

`apps/api`의 `domains/<d>/`(api·service·repository·schema)와 같은 축으로 조직하되, MCP 서버는 HTTP REST 경계도 `engine/`도 없으므로 **축소판**으로 둔다:

```
src/domains/<domain>/
├─ tools.py        # @mcp.tool — LLM 경계 (apps/api의 api 계층 대체)
├─ service.py      # 비즈니스 로직 — 어댑터들을 조합
├─ client.py       # 외부 REST egress (있으면)
├─ repository.py   # DB egress (있으면, llmonl)
└─ models.py       # pydantic 스키마 (schema 계층)
# prompts.py / resources.py  # (선택) MCP resource·prompt
```

**도메인이 조직 축, 어댑터(client/repository)는 도메인 내부 구현.** 호출 흐름:

```
@mcp.tool  →  service  →  client(REST) / repository(DB)  →  외부 시스템
 (얇음)       (조합)       (egress: 재시도·쿼리)
```

## 새 MCP 서버 만들기 — 복제 → 리네임 → 도메인 추가

> 템플릿 위치: `templates/mcp-server/` · 인스턴스 권장 위치: `apps/<name>-mcp/` (ADR-0004)

1. **복제**: `cp -r templates/mcp-server apps/<name>-mcp`
2. **리네임**: `pyproject.toml`(name·description), `src/core/mcp.py`의 `FastMCP("...")` 타이틀
3. **도메인 추가**: `src/domains/sample/`를 `src/domains/<domain>/`로 복사해
   - `tools.py` — 노출할 도구(기능) 정의
   - `service.py` — 도메인 로직 (어댑터 조합)
   - `client.py` / `repository.py` — 필요한 egress만 남기고 교체 (REST만/DB만/둘 다)
   - `models.py` — 입출력 스키마
4. **설정 추가**: `src/core/config.py`에 도메인 설정(`*_base_url`·`*_api_key` 등) + `is_demo_*` 프로퍼티
5. **등록**: `src/app.py`에 `from src.domains.<domain> import tools ...  # noqa: F401`
6. **환경파일**: `cp .env.example .env` 작성 — 실제 키 세팅 시 데모 모드 해제
7. **DB 사용 도메인**: `scripts/schema.sql`을 llmonl 스키마에 적용 (이 템플릿은 create_all 안 함)

## 개발·실행

```bash
cd apps/<name>-mcp
uv sync --group dev
cp .env.example .env

# 로컬: stdio Inspector + 데모 모드 (OIDC·외부 시스템 불필요)
uv run fastmcp dev inspector src/app.py

# HTTP 서버 (hot-reload). global 인증이면 OIDC_* 설정 필요
uv run poe dev                 # uvicorn src.asgi:app :8000  (/health, /mcp)

uv run poe lint                # ruff check + lint-imports(domains → core 경계)
uv run poe format
uv run pytest tests/unit/      # 데모 모드라 외부 의존 0
```

## 샘플 도메인이 보여주는 것

`src/domains/sample/`의 세 도구:
- `get_sample_item` — 외부 REST 조회 (데모 모드 → 외부 호출 없음)
- `list_sample_records` — 로컬 DB 조회
- `get_sample_overview` — **REST + DB를 한 도메인에서 조합** (service 계층 예시)

> DB 도구(`list_sample_records`·`get_sample_overview`)는 PostgreSQL + `scripts/schema.sql`이 있어야 실제 동작한다. 단위 테스트는 REST 데모 호출 + 도구 등록만 검증한다.

## 인증 (ADR-0003 — 검증만)

- 자체 로그인·토큰 발급 **없음**. 사내 IdP가 발급한 Bearer 토큰을 `src/core/security.py`의 `verify_token`(JWKS, RS256)으로 검증만 — `apps/api`와 동일.
- `AUTH_MODE=global`(기본): `OIDCAuthMiddleware`가 모든 MCP 요청 차단(`/health`만 bypass). `OIDC_JWKS_URL` 등 미설정 시 모든 요청 401.
- `AUTH_MODE=per-tool`: 미들웨어는 토큰 파싱만, `@protected`/`require_auth(ctx)` 도구가 직접 검증.
- **stdio transport는 HTTP 미들웨어 미적용** → 로컬 Inspector·단위 테스트는 인증 없이 동작.

## 구조

```
src/
├─ core/           config(.env)·mcp(인스턴스+lifespan)·db(async psycopg, llmonl)
│                  ·http(재시도)·security(JWKS 검증 + 미들웨어)·logging·middleware·context
├─ domains/<domain>/  도메인 수직 슬라이스 (= 확장 단위) — tools·service·client·repository·models
├─ app.py          도메인 tools import → 도구 등록 트리거
└─ asgi.py         ASGI 진입점 — /health + OIDC·RequestID 미들웨어 조립
main.py            CLI: stdio면 mcp.run, HTTP면 uvicorn
scripts/schema.sql DB 도메인 DDL (llmonl)
deploy/            Dockerfile · docker-compose(mcp+postgres) · .env.example
```

> 참고: 이 템플릿의 코어는 `mcp/fastmcp-base`(워크스페이스 레퍼런스 구현)에서 v3 컨벤션에 맞춰 이식했다. Resource/Prompt, 관측 스택 등 추가 패턴은 거기를 참고.
