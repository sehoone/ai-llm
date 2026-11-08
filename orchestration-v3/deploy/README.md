# 환경별 배포

Docker Compose로 `local`, `dev`, `stg`, `prd`를 각각 배포한다. 환경마다
프로젝트 이름(`orchestration-v3-<환경>`), 네트워크, PostgreSQL, 업로드 및
Langfuse 볼륨이 분리된다. 인증은 자체 ID/PW 방식이다(ADR-0009).

## 1. 환경 설정

사용할 환경의 `environments/<환경>/compose.env.example`과 `api.env.example`을
같은 디렉터리에 각각 `compose.env`, `api.env`로 복사해 수정한다.
실제 설정 파일은 Git에 커밋하지 않는다. 디렉터리와 파일의 접근 권한도 제한한다.

```powershell
# 프로젝트 루트. 다른 환경은 local을 dev, stg, prd로 변경.
Copy-Item deploy\environments\local\compose.env.example deploy\environments\local\compose.env
Copy-Item deploy\environments\local\api.env.example deploy\environments\local\api.env
```

- `compose.env`: 포트, DB 및 관측 스택 설정. DB 자격은 API에도 동일하게 주입된다.
- `api.env`: api 런타임 **단일 소스**(ADR-0018) — JWT, seed 관리자, LLM·Langfuse 키,
  네트워크 좌표 등. docker 배포 시 네트워크 좌표(`POSTGRES_HOST/PORT`, `STORAGE_BACKEND`,
  `MINIO_*`, `LANGFUSE_HOST`)는 Compose가 서비스 DNS로 override하고, 파일의 localhost 값은
  bare-metal 개발(`uv run poe dev`, `ENV_FILE`로 이 파일을 읽음) 전용이다. 항목 설명은 파일 주석 참고.
- 각 `REPLACE_ME`를 **환경마다 다른 비밀값**으로 교체한다. 예를 들어
  `openssl rand -hex 32`를 항목마다 별도로 실행한다.
  JWT 키는 32자 이상, Langfuse encryption key는 정확히 64자리 16진수여야 한다.
  PostgreSQL 사용자·비밀번호·DB 이름과 ClickHouse 비밀번호는 연결 URL에도 들어가므로
  영문·숫자·`.`, `_`, `~`, `-`만 사용한다.
- 최초 관리자 생성이 필요하면 `SEED_ADMIN_PASSWORD`를 설정한다. 빈 값이면 생성하지 않는다.
  이미 존재하는 관리자의 비밀번호는 설정을 바꿔도 바뀌지 않는다.
- LLM API 키가 비어 있고 provider가 Ollama가 아니면 실제 모델 대신 데모 모델이 사용된다.
  실제 모델이 필요한 환경에는 해당 환경의 LLM 설정을 준비한다.
- 예제 파일의 포트는 local `806x`, dev `816x`, stg `826x`, prd `836x`로 구분했다.
  실제 서버의 사용 가능한 포트로 변경할 수 있다. DB·관측 UI는 호스트 loopback에만 바인딩된다.
- Nginx도 기본적으로 loopback에 바인딩된다. 외부 접근이 필요한 환경은
  `NGINX_BIND_ADDRESS`와 방화벽을 설정하고, 앞단에서 HTTPS를 종료해야 한다.
  Langfuse UI를 외부에 제공한다면 접근을 제한하고 `LANGFUSE_NEXTAUTH_URL`을 실제 HTTPS URL로 설정한다.

Compose는 선택된 `compose.env`를 변수 치환에, `api.env`를 API 런타임에 사용한다.
배포 명령은 셸의 기존 Compose 변수들이 선택한 환경 설정을 덮어쓰지 못하게 한다.
필수 설정이 없거나 예제의 비밀값을 교체하지 않으면 배포가 실패한다.
Compose가 설정 파일의 `$`를 변수 치환으로 해석할 수 있으므로 비밀값은 16진수를
권장한다. 부득이하게 `$`를 사용한다면 Compose dotenv 문법에 맞게 따옴표로 감싼다.

## 2. 배포와 종료

프로젝트 루트에서 실행한다. `ENV`는 필수이며 네 환경 외의 값은 허용하지 않는다.
Docker Compose, uv, go-task가 필요하다.
명령은 현재 Docker context를 사용하므로 실행 전 대상 서버를 확인한다.

```powershell
task deploy ENV=local
task deploy ENV=dev
task deploy ENV=stg
task deploy ENV=prd

task deploy-down ENV=dev
$env:CONFIRM_PRD = 'prd'
task deploy-down ENV=prd
Remove-Item Env:\CONFIRM_PRD
```

`deploy`는 해당 환경의 이미지를 로컬에서 빌드하고 스택을 기동한다.
현재는 이미지 레지스트리나 `stg`에서 검증한 이미지의 `prd` 승격 기능을 제공하지 않는다.
`deploy-down`은 볼륨을 삭제하지 않는다. 운영 이미지 버전 고정,
TLS, 접근 통제, 백업 및 복구 테스트는 실제 운영 전에 별도로 준비해야 한다.
현재 Compose의 외부 이미지는 일부 `latest` 등 가변 태그를 사용한다.

### 로그인 스모크 테스트

먼저 해당 환경에 테스트 계정을 준비한 후 접근 가능한 Nginx 주소와 자격을 명시한다.
예시는 local이며, 다른 환경에서는 해당 주소와 전용 계정으로 변경한다.

```powershell
$env:SMOKE_BASE_URL = 'http://localhost:8060'
$env:SMOKE_USERNAME = '<test-user>'
$env:SMOKE_PASSWORD = '<test-password>'
task deploy-test ENV=local
Remove-Item Env:\SMOKE_BASE_URL, Env:\SMOKE_USERNAME, Env:\SMOKE_PASSWORD
```

스모크 테스트는 배포 후 `/health`의 환경이 선택한 환경과 일치하는지 확인하고
로그인 토큰 발급을 검사한다. 잘못된 환경이나 401이면 실패하며 다른 환경의
설정이나 기본 계정으로 폴백하지 않는다. 웹 UI 자체는 검사하지 않는다.

## 3. Langfuse

환경별 Langfuse UI(기본 loopback 포트: 8067/8167/8267/8367)에서 프로젝트를 만들고
발급받은 키를 같은 환경의 `api.env`에 설정한 뒤 해당 환경을 다시 배포한다.
`LANGFUSE_HOST=http://langfuse-web:3000`은 컨테이너 내부 주소다.
키가 비어 있으면 API의 Langfuse 관측은 비활성화된다(ADR-0007).

## 4. 기존 배포와 데이터

이전 프로젝트 `orchestration-v3`의 볼륨은 새 프로젝트에서 자동으로 사용되지 않는다.
기존 DB와 업로드, Grafana 및 Langfuse의 PostgreSQL·ClickHouse·MinIO 데이터가
필요하면 먼저 백업과 복구를 검증한 후 대상 환경으로 이전한다. 기존 볼륨을 지우거나
새 볼륨에 덮어쓰기 전에 반드시 대상을 확인한다.

PostgreSQL 초기화 SQL은 **빈 볼륨 최초 생성 시에만** 실행된다. 기존 데이터의 스키마
변경은 별도 마이그레이션이 필요하다. 비밀번호를 설정 파일에서 바꿔도 기존 PostgreSQL,
ClickHouse 등의 저장된 자격이 자동으로 변경되는 것은 아니다.
볼륨 삭제는 데이터 손실이므로 `deploy-down`에서 제공하지 않는다.

## 5. 장애 확인

정확한 환경을 지정해 Compose 로그를 조회한다. 설정 파일이나 `docker compose config`
출력에는 비밀정보가 들어갈 수 있으므로 공유하지 않는다.

```powershell
$env:DEPLOY_ENV = 'local'
docker compose -p orchestration-v3-local --project-directory deploy --env-file deploy\environments\local\compose.env -f deploy\docker-compose.yml logs api
Remove-Item Env:\DEPLOY_ENV
```

401은 테스트 계정 자격 또는 계정 상태를 확인한다. 스키마 오류는 DB 버전과
마이그레이션 상태를 확인한다. 문제 해결을 위해 무조건 볼륨을 삭제하지 않는다.
