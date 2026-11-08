"""로그인 스모크 테스트 (ADR-0009) — 배포된 스택이 ID/PW 로그인을 처리하는지 검증.

`task deploy-test`가 compose up 후 호출한다. 표준 라이브러리만 사용(추가 의존성 없음).

동작:
  1. api가 뜰 때까지 로그인 엔드포인트를 재시도(연결 거부·5xx·503은 대기).
  2. seed 관리자 자격으로 POST /api/v1/auth/login → 200 + access_token 이면 성공.
  3. 401(자격 불일치)·토큰 없음은 즉시 실패(대기해도 안 고쳐짐).

SMOKE_BASE_URL, SMOKE_USERNAME, SMOKE_PASSWORD 환경변수를 명시해야 한다.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
RETRY_SECONDS = 180  # api 콜드 스타트(빌드 직후) 여유
RETRY_INTERVAL = 3


def missing_config() -> list[str]:
    return [key for key in ("SMOKE_BASE_URL", "SMOKE_USERNAME", "SMOKE_PASSWORD") if not os.environ.get(key)]


def main(expected_env: str | None = None) -> int:
    missing = missing_config()
    if missing:
        print(f"[smoke] 필수 환경변수 누락: {', '.join(missing)}")
        return 1
    base = os.environ["SMOKE_BASE_URL"].rstrip("/")
    username = os.environ["SMOKE_USERNAME"]
    password = os.environ["SMOKE_PASSWORD"]
    url = f"{base}/api/v1/auth/login"
    body = json.dumps({"username": username, "password": password}).encode("utf-8")

    print(f"[smoke] 로그인 검증 → {url} (user={username})")
    deadline = time.time() + RETRY_SECONDS
    last_err = "(no attempt)"

    while time.time() < deadline:
        try:
            if expected_env:
                with urllib.request.urlopen(f"{base}/health", timeout=10) as res:
                    health = json.loads(res.read().decode("utf-8"))
                if health.get("env") != expected_env:
                    print(f"[smoke] 실패 — 배포 환경 불일치: 예상={expected_env}, 실제={health.get('env')}")
                    return 1
            req = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"}, method="POST"
            )
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
                    "선택한 환경의 테스트 계정과 DB 상태를 확인하세요."
                )
                return 1
            last_err = f"HTTP {e.code}"  # 502/503 등 — 기동 중일 수 있어 재시도
        except urllib.error.URLError as e:
            last_err = f"연결 실패({e.reason})"  # api 아직 안 뜸 — 재시도
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
            print(f"[smoke] 실패 — 예상하지 못한 응답: {e}")
            return 1

        print(f"[smoke] 대기… {last_err} — {RETRY_INTERVAL}s 후 재시도")
        time.sleep(RETRY_INTERVAL)

    print(f"[smoke] 실패 — {RETRY_SECONDS}s 내 로그인 성공 못함 (마지막: {last_err})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
