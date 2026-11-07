# engine/observability

LLM 관측(Langfuse) 계측 — 횡단 모듈 (ADR-0007). `llm`·`graph`·`agent`가 공유.

## 경계

- 엔진 규칙 준수: `domains`·FastAPI를 import하지 않는다. `core.config`만 의존.
- 관측은 **best-effort** — 초기화/전송 실패는 로깅 후 조용히 비활성(요청을 깨지 않음).
- 프롬프트 관리는 여기 소관이 아니다 — 프롬프트는 `engine/prompts`의 Git 자산(ADR-0005 §5).

## 구성

| 파일 | 책임 |
|------|------|
| `context.py`   | `TraceContext` 값 객체 — 도메인이 생성해 주입(user_id·session_id·tags·extra) |
| `langfuse.py`  | Langfuse 싱글턴·CallbackHandler 생성·flush(shutdown) |
| `runconfig.py` | `TraceContext → RunnableConfig({callbacks, metadata, tags})`. 비활성 시 `{}` |

## 사용 (도메인 이식 시)

```python
# domains/chat/service.py (예시)
from src.engine.observability import TraceContext, build_run_config

trace = TraceContext(user_id=current.id, session_id=session.id, tags=("chat",))
run_config = build_run_config(trace)          # 비활성이면 {}
async for chunk in llm.astream(messages, config=run_config):
    ...
```

- 세션/사용자는 langfuse 3.x가 metadata의 `langfuse_session_id`/`langfuse_user_id`로 트레이스에 귀속.
- 프로세스 종료 시 flush는 `src.main`의 FastAPI lifespan이 `shutdown()`을 호출해 처리.

## 설정 (`core/config.py` → env)

`LANGFUSE_PUBLIC_KEY`·`LANGFUSE_SECRET_KEY`·`LANGFUSE_HOST`·`LANGFUSE_ENABLED`.
키가 비면 `langfuse_is_enabled`가 false → 계측 완전 비활성. 키는 Langfuse UI에서 프로젝트 생성 후 발급.
