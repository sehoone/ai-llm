# ADR-0018: env 설정 레이아웃 — 환경별 단일 소스

- 상태: Accepted
- 날짜: 2026-11-08
- 결정자: sehoon
- 관련: [ADR-0004](0004-apps-packages-monorepo-layout.md) (모노레포 레이아웃), [ADR-0009](0009-self-id-password-auth.md) (JWT·seed 시크릿), [ADR-0007](0007-llm-observability-langfuse.md)·[ADR-0017](0017-attachment-object-storage-minio.md) (관측·스토리지 좌표)

## Context (맥락)

`.env`가 여러 곳에 흩어져 있었다 — `deploy/.env`(compose 변수), `apps/api/.env.production`,
`apps/web/.env.production`, `apps/{api,web}/.env.example`. 같은 값(DB 자격, LLM 키, Langfuse 키)이
파일마다 중복되었고, docker 런타임 설정과 bare-metal 개발 설정이 섞여 drift·혼동을 유발했다.
특히 실 LLM 키가 세 파일에 평문 중복 저장되어 있었다.

## Decision (결정)

### 1. 환경별 단일 홈 — `deploy/environments/<env>/`

환경(`local`/`dev`/`stg`/`prd`)마다 디렉터리 하나, **소비 주체별 2파일**:

- `compose.env` — docker compose가 `--env-file`로 읽음: 포트, bind 주소, DB명·자격,
  Grafana/ClickHouse/MinIO/Langfuse 인프라 시크릿. compose 변수 치환 + db 컨테이너·api에 주입.
- `api.env` — api 런타임 **단일 소스**: 인증(JWT·seed), LLM, 장기메모리, 첨부, Langfuse 키,
  네트워크 좌표. `docker-compose.yml`이 `env_file`로 api 컨테이너에 주입.

실파일은 gitignore, `*.example`만 커밋(`REPLACE_ME` 자리표시자). `tools/deploy.py`가
단일 진입점으로 설정 검증(시크릿 교체·URL 안전성·길이) 후 기동한다.

### 2. 네트워크 좌표는 compose가 override — `api.env`는 bare-metal 기준

`api.env`는 localhost 좌표(예: `POSTGRES_HOST=localhost:8066`, `LANGFUSE_HOST=localhost:8067`,
`STORAGE_BACKEND=local`)를 담는다. docker 배포 시 `docker-compose.yml`의 `environment:`가
서비스 DNS(`db:5432`, `langfuse-web:3000`, `minio:9000`, `STORAGE_BACKEND=minio` 등)로
**override**한다(compose `environment` > `env_file` 우선순위). 따라서 **한 파일이 두 컨텍스트를
모두 커버**한다:

- **docker 배포**: `api.env` + compose override → 서비스 DNS.
- **bare-metal 개발**(`uv run poe dev`): `api.env`를 그대로 읽음(localhost). 로컬 스택이 떠 있어야 함.

### 3. bare-metal api는 `ENV_FILE`로 단일 소스를 읽음

`core/config.py`가 `ENV_FILE` 환경변수(기본 `.env`)로 env 경로를 받는다. api의 poe `dev`
태스크가 `ENV_FILE=../../deploy/environments/local/api.env`를 주입한다. app-level `apps/api/.env*`는
제거됐다.

### 4. web은 로컬 env 파일 불필요

`NEXT_PUBLIC_API_URL`이 비면 axios는 `/api` 상대경로를 쓰고 `next.config` rewrite가
`API_URL`(기본 `localhost:8000`)로 프록시한다. docker 빌드는 `API_URL` build arg만 사용.
따라서 web에는 어떤 env 파일도 두지 않는다(`apps/web/.env*` 제거). OIDC 변수는 보존된
비활성 코드라 미설정이어도 무방.

## Consequences (결과)

- `.env`의 단일 소스가 환경당 `deploy/environments/<env>/{compose.env, api.env}`로 수렴. 중복 제거.
- docker/bare-metal이 같은 `api.env`를 공유하되 네트워크 좌표만 compose가 바꾼다.
- app-level `apps/{api,web}/.env*`, `deploy/.env` 제거.
- 남는 중복: `POSTGRES_*` 비밀값이 `compose.env`(db 컨테이너용)와 `api.env`(bare-metal 접속용)에
  각각 존재 — bare-metal이 로컬 스택 DB에 붙으려면 둘이 일치해야 한다. 서로 다른 컨텍스트라 수용.
- 평문 노출됐던 LLM 키는 `REPLACE_ME`로 치환 — **폐기(revoke) 후 재발급**이 필요(코드로 강제 불가).
