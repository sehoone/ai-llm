"""로그인 스모크 테스트 (ADR-0009) — 배포된 스택이 ID/PW 로그인을 처리하는지 검증.

`task deploy-test`가 compose up 후 호출한다. 표준 라이브러리만 사용(추가 의존성 없음).

동작:
  1. api가 뜰 때까지 로그인 엔드포인트를 재시도(연결 거부·5xx·503은 대기).
  2. seed 관리자 자격으로 POST /api/v1/auth/login → 200 + access_token 이면 성공.
  3. 401(자격 불일치)·토큰 없음은 즉시 실패(대기해도 안 고쳐짐).

자격·URL 우선순위: 환경변수 > apps/api/.env.production > .env.development > .env.example > 기본값.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_CANDIDATES = [
    ROOT / "apps" / "api" / ".env.production",
    ROOT / "apps" / "api" / ".env.development",
    ROOT / "apps" / "api" / ".env.example",
]

DEFAULTS = {
    "SMOKE_BASE_URL": "http://localhost:8060",  # nginx 진입점 → /api/* 는 api로 프록시
    "SEED_ADMIN_USERNAME": "admin",
    "SEED_ADMIN_PASSWORD": "admin1234",
}

RETRY_SECONDS = 180  # api 콜드 스타트(빌드 직후) 여유
RETRY_INTERVAL = 3


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def resolve(key: str) -> str:
    if os.environ.get(key):
        return os.environ[key]
    for path in ENV_CANDIDATES:
        vals = _load_env_file(path)
        if vals.get(key):
            return vals[key]
    return DEFAULTS[key]


def main() -> int:
    base = resolve("SMOKE_BASE_URL").rstrip("/")
    username = resolve("SEED_ADMIN_USERNAME")
    password = resolve("SEED_ADMIN_PASSWORD")
    url = f"{base}/api/v1/auth/login"
    body = json.dumps({"username": username, "password": password}).encode("utf-8")

    print(f"[smoke] 로그인 검증 → {url} (user={username})")
    deadline = time.time() + RETRY_SECONDS
    last_err = "(no attempt)"

    while time.time() < deadline:
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                payload = json.loads(res.read().decode("utf-8"))
            token = (payload.get("data") or {}).get("access_token")
            if token:
                print(f"[smoke] OK — 토큰 발급 확인 (len={len(token)})")
                return 0
            print(f"[smoke] 실패 — 200이지만 access_token 없음: {payload}")
            return 1
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(
                    "[smoke] 실패 — 401. seed 관리자 자격 불일치 또는 미생성. "
                    "apps/api/.env.production의 SEED_ADMIN_* 와 DB 상태를 확인하세요."
                )
                return 1
            last_err = f"HTTP {e.code}"  # 502/503 등 — 기동 중일 수 있어 재시도
        except urllib.error.URLError as e:
            last_err = f"연결 실패({e.reason})"  # api 아직 안 뜸 — 재시도

        print(f"[smoke] 대기… {last_err} — {RETRY_INTERVAL}s 후 재시도")
        time.sleep(RETRY_INTERVAL)

    print(f"[smoke] 실패 — {RETRY_SECONDS}s 내 로그인 성공 못함 (마지막: {last_err})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
