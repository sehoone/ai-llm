# 런북: DB 백업·복구 (ADR-0032 Phase 3)

orchestration-v3의 PostgreSQL은 **단일 컨테이너(SPOF)** + 명명 볼륨(`orchestration-v3-<env>_postgres-data`)이다.
관리형 DB로 외부화하기 전까지 **디스크/볼륨 손실에 대비한 논리 백업**이 유일한 복구 수단이다. 스키마는 수동
DDL(`init.sql` + `migrations/*.sql`)로 관리하지만, **데이터 복구는 이 논리 덤프**로 한다.

대상 DB: `mydb`(앱 — `llmonl` 스키마), `langfuse`(관측 — 동일 컨테이너 공유).

## 백업

```bash
# custom-format(-Fc) 덤프를 ./backups 에 저장 (mydb + langfuse)
python tools/backup_db.py stg                 # local|dev|stg|prd
python tools/backup_db.py prd --out /mnt/backups
```

- 산출물: `backups/<env>-<db>-<YYYYMMDD-HHMMSS>.dump` (pg_dump custom-format).
- 내부적으로 `docker exec orchestration-v3-<env>-db-1 pg_dump -U postgres -Fc -d <db>`를 호스트 파일로 리다이렉트.
- **운영 권장**: cron/스케줄러로 주기 실행(예: 매일) + **원격 사본**(S3/MinIO 등)으로 이전 — 호스트 디스크가
  볼륨과 함께 손실되면 로컬 백업도 함께 잃는다. 보존 기간(예: 7/30일) 로테이션.

### 수동 백업(스크립트 없이)
```bash
docker exec orchestration-v3-stg-db-1 pg_dump -U postgres -Fc -d mydb > stg-mydb.dump
docker exec orchestration-v3-stg-db-1 pg_dump -U postgres -Fc -d langfuse > stg-langfuse.dump
```

## 복구

> ⚠️ 복구는 **데이터를 덮어쓴다**. 대상 환경·DB를 반드시 재확인하고, 가능하면 복구 전 현재 상태를 1회 더 백업한다.

### A. 기존 DB에 복구(테이블 초기화 후 적재)
```bash
# .dump 파일을 컨테이너로 복사 후 pg_restore (--clean: 기존 객체 DROP 후 재생성)
docker cp backups/stg-mydb-20261128-030000.dump orchestration-v3-stg-db-1:/tmp/mydb.dump
docker exec orchestration-v3-stg-db-1 \
  pg_restore -U postgres -d mydb --clean --if-exists --no-owner /tmp/mydb.dump
```

### B. 깨끗한 새 볼륨에 복구(디스크 전손 등)
```bash
# 1) 스택을 새 볼륨으로 기동 → init.sql이 스키마를 먼저 만든다(볼륨 최초 init 시 1회).
task deploy ENV=stg            # 또는 docker compose ... up -d db
# 2) langfuse DB가 없으면 생성(최초 init이 아니면 수동).
docker exec orchestration-v3-stg-db-1 psql -U postgres -c "CREATE DATABASE langfuse;"
# 3) 복구
docker cp backups/stg-mydb-....dump orchestration-v3-stg-db-1:/tmp/mydb.dump
docker exec orchestration-v3-stg-db-1 pg_restore -U postgres -d mydb --clean --if-exists --no-owner /tmp/mydb.dump
docker cp backups/stg-langfuse-....dump orchestration-v3-stg-db-1:/tmp/lf.dump
docker exec orchestration-v3-stg-db-1 pg_restore -U postgres -d langfuse --clean --if-exists --no-owner /tmp/lf.dump
```

### 복구 후 점검
- `docker exec … psql -U postgres -d mydb -c "\dt llmonl.*"` — 테이블 존재.
- api readiness: `GET /health/ready` → `{"checks":{"db":"ok",…}}`.
- 적용 안 된 최신 마이그레이션이 있으면 `migrations/*.sql`을 순서대로 수동 적용(멱등).

## 주의
- custom-format 덤프는 `pg_restore`로만 복구(평문 psql `<` 입력 불가).
- 덤프에는 비밀번호 해시(`users.hashed_password`)·API 키 등 **민감 데이터**가 포함된다 — 백업 파일 접근 통제·암호화.
- 버전 호환: 복구 대상 PostgreSQL 메이저 버전은 덤프 생성 버전과 같거나 상위(현재 pg16).
