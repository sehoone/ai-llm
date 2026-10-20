"""api FastAPI 앱의 OpenAPI 스펙을 packages/contracts/openapi.json으로 export.

단방향 계약 흐름(ADR-0003): api가 진실의 원천 → web이 TS 타입 생성.
`task gen-types`가 이 스크립트 실행 후 web의 `pnpm gen:types`를 호출한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

from src.main import app  # noqa: E402

OUT = ROOT / "packages" / "contracts" / "openapi.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
