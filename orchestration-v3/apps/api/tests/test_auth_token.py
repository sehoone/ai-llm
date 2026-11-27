"""JWT 발급 — jti(폐기 식별자) 포함 검증 (ADR-0032 Phase 2).

폐기 블랙리스트(revoked_token) 전체 흐름은 DB가 필요해 stg 라이브로 검증한다. 여기서는 DB 없이
토큰이 고유 jti를 담고 decode가 이를 복원하는지만 확인한다.
"""

from src.core.config import settings
from src.core.security import create_access_token, decode_access_token


def test_token_carries_unique_jti() -> None:
    settings.jwt_secret_key = "test-secret-key-at-least-32-characters-long!!"  # 서명용(테스트 env)
    t1 = create_access_token(subject="1")
    t2 = create_access_token(subject="1")
    c1 = decode_access_token(t1)
    c2 = decode_access_token(t2)
    assert c1["jti"] and c2["jti"]
    assert c1["jti"] != c2["jti"]  # 매 발급마다 고유 — 토큰 단위 폐기 가능
    assert c1["sub"] == "1"
