---
description: 전체 스택 배포(docker compose build+up) 후 로그인 스모크 테스트 (ADR-0009)
---

레포 루트에서 `task deploy-test`를 실행해 전체 스택을 빌드·기동하고 로그인 스모크 테스트를 돌린다.

실행 후:
- 스모크가 **통과**하면 발급된 토큰 확인 결과를 간단히 보고한다.
- **401**로 실패하면: seed 관리자 자격 불일치/미생성이 원인 — `apps/api/.env.production`의
  `SEED_ADMIN_*`가 설정됐는지, DB의 `users` 테이블에 `hashed_password` 컬럼이 있는지 확인하라고 안내한다.
  기존 `postgres-data` 볼륨은 `init.sql`을 재실행하지 않으므로 ADR-0009 스키마가 없을 수 있다 →
  `task deploy-down -- -v`로 볼륨을 비우고 `task deploy-test`를 다시 실행하는 방법을 제시한다.
- 그 외 실패는 `docker compose logs api`(deploy/ 기준) 등 관련 로그를 확인해 원인을 짚는다.

주의: `docker`·`uv`는 사용자 셸에서 실행된다. 빌드가 오래 걸릴 수 있으니 백그라운드가 아닌 충분한 타임아웃으로 실행한다.
