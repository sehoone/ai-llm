"""요청 로깅 미들웨어 — request_id 발급·전파 + 액세스 로그 (ADR-0031 §B·§C).

순수 ASGI 미들웨어(BaseHTTPMiddleware 아님): 엔드포인트와 **같은 컨텍스트**에서 실행되므로
여기서 set한 request_id가 하위(동기 의존성 포함)에 보인다. user_id는 DB 없이 JWT sub로 best-effort
주입한다(실제 인증은 핸들러 의존성이 수행).

액세스 로그는 요청 1건당 1줄. `LOG_LEVEL=DEBUG`이면 요청/응답 본문 상세를 추가로 남긴다. 단
**안전 경계**를 둔다:
- **SSE 스트리밍**(text/event-stream) 응답 본문은 미캡처(메모리 폭증·스트리밍 방해 방지).
- **JSON 본문만** 캡처(multipart/form/바이너리는 스킵). 4KB 상한 초과 시 스킵/절단.
- **민감 필드**(password·token·secret·api_key 등)는 재귀적으로 `***` 마스킹.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from src.core.logging import request_id_var, user_id_var
from src.core.security import decode_access_token

logger = logging.getLogger("src.access")

# 노이즈 경로 — 액세스 로그를 DEBUG로 낮춰 INFO 로그를 더럽히지 않는다(헬스체크 등).
_QUIET_PATHS = {"/health"}

# JSON 본문에서 마스킹할 민감 필드명(소문자). 로그인 password·응답 access_token 등을 가린다.
_SENSITIVE_KEYS = {
    "password", "passwd", "pwd", "current_password", "new_password", "old_password",
    "hashed_password", "secret", "secret_key", "client_secret", "private_key",
    "api_key", "apikey", "token", "access_token", "refresh_token", "authorization",
}

# 본문 캡처 상한(바이트). 초과 요청은 스킵, 응답은 여기까지만 모으고 절단.
_BODY_CAP = 4096


def _header(headers: list[tuple[bytes, bytes]], name: bytes) -> str | None:
    for key, value in headers:
        if key == name:
            return value.decode("latin-1")
    return None


def _user_id_from_auth(headers: list[tuple[bytes, bytes]]) -> str:
    """로그 보강용 user_id를 best-effort로 추출 — 자체 JWT의 sub만(DB 조회 없음).

    실제 인증은 get_current_user가 수행한다. 여기선 로깅 목적이라 실패하면 조용히 "-".
    API 키(sk-)는 DB 없이 사용자를 알 수 없어 "-"로 둔다.
    """
    auth = _header(headers, b"authorization")
    if not auth:
        return "-"
    token = auth.removeprefix("Bearer ").strip()
    if not token or token.startswith("sk-"):
        return "-"
    try:
        return str(decode_access_token(token).get("sub", "-"))
    except Exception:
        return "-"


def _client_ip(headers: list[tuple[bytes, bytes]], scope: dict) -> str:
    """실제 클라이언트 IP — nginx 뒤라 X-Forwarded-For 우선, 없으면 소켓 peer."""
    xff = _header(headers, b"x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "-"


def _is_json_ct(content_type: str) -> bool:
    return "json" in content_type.lower()


def _redact(obj):
    """JSON 구조를 재귀 순회하며 민감 키 값을 ***로."""
    if isinstance(obj, dict):
        return {k: ("***" if str(k).lower() in _SENSITIVE_KEYS else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    return obj


def _render_body(raw: bytes) -> str:
    """JSON 본문을 파싱→민감 키 마스킹→직렬화. 파싱 실패 시 원문 미노출(형식 불명)."""
    if not raw:
        return "(empty)"
    try:
        data = json.loads(raw)
    except Exception:
        return "(unparseable)"
    rendered = json.dumps(_redact(data), ensure_ascii=False)
    if len(rendered) > _BODY_CAP:
        rendered = rendered[:_BODY_CAP] + "...(truncated)"
    return rendered


class RequestLoggingMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = scope.get("headers", [])
        # 들어온 X-Request-ID 재사용(nginx·클라이언트 추적) 또는 신규 발급.
        request_id = _header(headers, b"x-request-id") or uuid.uuid4().hex[:16]
        rid_token = request_id_var.set(request_id)
        # user_id는 JWT sub로 best-effort(DB 없음) — 실제 인증은 핸들러 의존성이 수행.
        uid_token = user_id_var.set(_user_id_from_auth(headers))

        method = scope.get("method", "-")
        path = scope.get("path", "-")
        query = scope.get("query_string", b"").decode("latin-1")
        client = _client_ip(headers, scope)
        req_ct = _header(headers, b"content-type") or ""
        cl = _header(headers, b"content-length")
        req_bytes = int(cl) if cl and cl.isdigit() else 0
        user_agent = _header(headers, b"user-agent") or "-"
        referer = _header(headers, b"referer") or "-"

        debug = logger.isEnabledFor(logging.DEBUG) and path not in _QUIET_PATHS

        # ── 요청 본문 캡처 (DEBUG·JSON·상한 이내일 때만) ──
        capture_req = debug and _is_json_ct(req_ct) and 0 < req_bytes <= _BODY_CAP
        if not debug or capture_req:
            req_body_reason: str | None = None
        elif req_bytes == 0:
            req_body_reason = "(empty)"
        elif not _is_json_ct(req_ct):
            req_body_reason = "(non-json)"
        else:
            req_body_reason = f"(too-large:{req_bytes})"

        req_chunks: list[bytes] = []

        async def recv() -> dict:
            # receive를 감싸 요청 본문을 기록(핸들러엔 그대로 전달). 캡처 대상일 때만 모은다.
            message = await receive()
            if capture_req and message["type"] == "http.request":
                req_chunks.append(message.get("body", b"") or b"")
            return message

        state: dict = {"status": 500, "resp_bytes": 0,
                       "capture_resp": False, "resp_body": bytearray(), "resp_reason": None}

        async def send_wrapper(message: dict) -> None:
            mtype = message["type"]
            if mtype == "http.response.start":
                state["status"] = message["status"]
                resp_headers = message.setdefault("headers", [])
                resp_headers.append((b"x-request-id", request_id.encode("latin-1")))
                if debug:
                    resp_ct = _header(resp_headers, b"content-type") or ""
                    if "text/event-stream" in resp_ct.lower():
                        state["resp_reason"] = "(stream)"
                    elif not _is_json_ct(resp_ct):
                        state["resp_reason"] = "(non-json)"
                    else:
                        state["capture_resp"] = True
            elif mtype == "http.response.body":
                body = message.get("body", b"") or b""
                state["resp_bytes"] += len(body)
                if state["capture_resp"] and len(state["resp_body"]) < _BODY_CAP:
                    state["resp_body"].extend(body[: _BODY_CAP - len(state["resp_body"])])
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, recv, send_wrapper)
        except Exception:
            # 미처리 예외(500) — ServerErrorMiddleware가 응답을 만들기 전 여기서 먼저 스택과 함께 기록.
            self._log(logging.ERROR, method, path, query, 500, start, client,
                      req_bytes, state["resp_bytes"], user_agent, referer, exc=True)
            raise
        else:
            code = state["status"]
            if path in _QUIET_PATHS:
                level = logging.DEBUG
            elif code >= 500:
                level = logging.ERROR
            elif code >= 400:
                level = logging.WARNING
            else:
                level = logging.INFO
            self._log(level, method, path, query, code, start, client,
                      req_bytes, state["resp_bytes"], user_agent, referer)

            # DEBUG일 때만 요청/응답 본문 상세 (민감 필드 마스킹, SSE·비JSON 본문 제외).
            if debug:
                req_body = req_body_reason if req_body_reason is not None else _render_body(b"".join(req_chunks))
                resp_body = state["resp_reason"] or _render_body(bytes(state["resp_body"]))
                logger.debug(
                    "http_request_detail method=%s path=%s req_body=%s resp_body=%s",
                    method, path, req_body, resp_body,
                    extra={"req_body": req_body, "resp_body": resp_body},
                )
        finally:
            user_id_var.reset(uid_token)
            request_id_var.reset(rid_token)

    @staticmethod
    def _log(level, method, path, query, status, start, client, req_bytes,
             resp_bytes, user_agent, referer, *, exc: bool = False) -> None:
        duration_ms = (time.perf_counter() - start) * 1000
        # 콘솔(dev)엔 핵심 필드를 읽기 쉽게. user_agent·referer는 JSON extra로만(콘솔 과밀 방지).
        logger.log(
            level,
            "http_request method=%s path=%s%s status=%s duration_ms=%.1f client=%s user=%s "
            "req_bytes=%d resp_bytes=%d",
            method, path, (f" query={query}" if query else ""), status, duration_ms,
            client, user_id_var.get(), req_bytes, resp_bytes,
            exc_info=exc,
            # JSON(docker)에선 아래가 구조화 필드로 — Loki에서 쿼리 가능(request_id·user_id는 필터가 주입).
            extra={
                "http_method": method,
                "http_path": path,
                "http_query": query,
                "http_status": status,
                "duration_ms": round(duration_ms, 1),
                "client": client,
                "req_bytes": req_bytes,
                "resp_bytes": resp_bytes,
                "user_agent": user_agent,
                "referer": referer,
            },
        )
