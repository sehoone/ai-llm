"""DB 백업 — docker 내 PostgreSQL을 pg_dump로 호스트에 저장 (ADR-0032 Phase 3).

단일 postgres 컨테이너(SPOF)의 디스크 복구 수단. 각 DB(mydb·langfuse)를 custom-format(-Fc)으로
timestamped 파일에 덤프한다. custom-format은 pg_restore로 선택 복구·병렬 복구가 가능하다.

사용:
    python tools/backup_db.py <local|dev|stg|prd> [--out backups] [--user postgres]

복구 절차는 docs/runbooks/db-backup-restore.md 참고. 운영에서는 cron/스케줄러로 주기 실행 +
원격(객체 스토리지)로 사본 이전을 권장(호스트 디스크 동반 손실 대비).
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ENVIRONMENTS = ("local", "dev", "stg", "prd")
DATABASES = ("mydb", "langfuse")  # 앱 DB + Langfuse 관측 DB(동일 컨테이너 공유)


def container_name(environment: str) -> str:
    # deploy.py의 --project-name orchestration-v3-<env>와 동일 규칙.
    return f"orchestration-v3-{environment}-db-1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", choices=ENVIRONMENTS)
    parser.add_argument("--out", default="backups", help="백업 파일 저장 디렉터리")
    parser.add_argument("--user", default="postgres", help="postgres 슈퍼유저")
    args = parser.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    container = container_name(args.environment)

    rc = 0
    for db in DATABASES:
        dest = outdir / f"{args.environment}-{db}-{ts}.dump"
        print(f"[backup] {db} -> {dest}", flush=True)
        with dest.open("wb") as fh:
            result = subprocess.run(
                ["docker", "exec", container, "pg_dump", "-U", args.user, "-Fc", "-d", db],
                stdout=fh,
            )
        if result.returncode != 0:
            print(f"[backup] 실패: {db} (컨테이너 {container} 미기동/DB 부재?)", file=sys.stderr)
            dest.unlink(missing_ok=True)
            rc = 1
        else:
            print(f"[backup] 완료: {dest} ({dest.stat().st_size} bytes)", flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
