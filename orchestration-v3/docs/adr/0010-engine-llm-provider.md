# ADR-0010: engine/llm — provider 추상화 + 모델 해석·주입 경계

- 상태: Accepted
- 날짜: 2026-11-07
- 결정자: sehoon
- 관련: [ADR-0005](0005-ai-engine-layer.md)(engine 레이어·값 주입), [ADR-0008](0008-chat-human-approval.md)(그래프 모델 seam), [ADR-0007](0007-llm-observability-langfuse.md)(관측)
- 참조: V2 `common/services/llm.py`(LLMService), `common/langgraph/_nodes.py`, `common/prompts/`
- 로드맵: [v2-chat-migration-roadmap](../v2-chat-migration-roadmap.md) Phase 0

## Context (맥락)

V3 챗 그래프(ADR-0008)의 모델 노드는 아직 `FakeToolCallingModel` 주입 seam이다 — 실제 LLM
호출이 없다. V2 chat 기능 이식(로드맵)의 **모든 실기능(실 답변·제목생성·RAG·deep thinking)이
실 LLM 호출을 선행 조건**으로 한다. 따라서 Phase 0에서 `engine/llm`을 심는다.

V2 `LLMService`(589 LOC)는 강력하지만 **`src.common.services.database`·`src.llm_resources.models`를
직접 import**한다 — DB·도메인 결합. V3는 ADR-0005로 `engine`이 `domains`·FastAPI·DB 세션을 모르게
한다(`import-linter`로 강제). 그대로 옮길 수 없다.

제약:
- **단방향 레이어**(ADR-0005): engine은 `domains`를 모른다. LLM 설정(provider·모델·키)은 **값으로
  주입**받거나 `core.config`(env)에서 읽는다 — `llm_resource` **테이블 조회는 domain 책임**.
- 그래프 모델 노드 계약(ADR-0008): `ChatModel.invoke(messages) -> AIMessage` (동기). 그래프는 동기
  `stream`으로 구동되므로 어댑터도 동기 `invoke`를 제공해야 한다.

## Decision (결정)

### 1. provider 통합은 LiteLLM (V2 계승)

`engine/llm`은 `langchain-litellm`의 `ChatLiteLLM`으로 provider를 통합한다. 하나의 클라이언트로
Azure / OpenAI / Anthropic / Google(Gemini) / Ollama를 처리한다. `model_id`는 LiteLLM 관례:

| provider | model_id |
|----------|----------|
| openai (기본) | `<model>` (예: `gpt-4o-mini`) |
| azure | `azure/<deployment>` |
| anthropic | `anthropic/<model>` |
| google | `gemini/<model>` |
| ollama | `ollama/<model>` |

(V2의 `_create_llm_from_resource` 매핑을 **순수 함수**로 재작성 — DB 미의존.)

### 2. 설정은 "값(LlmConfig)"으로, DB 조회는 domain

```
engine/llm/
  config.py   # LlmConfig(provider·model·api_key·api_base·api_version·temperature·max_tokens) — 순수 값
  model.py    # build_chat_model(LlmConfig, *, tools, system_prompt) -> LlmChatModel
              #   LlmChatModel.invoke(messages): system prompt 선주입 후 내부 Runnable.invoke → AIMessage
  __init__.py # default_llm_config(): core.config(env)에서 LlmConfig | None
              # build_default_chat_model(...): 기본 설정으로 LlmChatModel
```

- `build_chat_model(config)`는 **순수**(주입된 값만 사용). Phase 1에서 domain이 `llm_resource` 행을
  해석해 `LlmConfig`로 변환·주입하는 경로를 연다(현재는 default만).
- **추론 모델**(gpt-5·o1·o3 계열)은 임의 temperature를 거부 → `temperature` 생략(V2 로직 계승).
- 키 주입: `api_key`는 `LlmConfig` 값. 기본값은 `core.config`(env `LLM_API_KEY`). engine은
  `llm_resource.api_key`(DB)를 직접 읽지 않는다.

### 3. 폴백 토글 — 키 없으면 FakeToolCallingModel

`settings.llm_is_configured`(키 존재 또는 ollama)가 거짓이면 chat 서비스는 `FakeToolCallingModel`을
계속 쓴다. 덕분에 **로컬·CI·테스트(키 없음)는 결정적 데모 흐름 유지**(ADR-0008 HITL 테스트 불변),
운영(`LLM_API_KEY` 설정)에서는 실 LLM로 응답한다. 실모델 조립 실패 시에도 fake로 안전 폴백.

### 4. system prompt는 engine/prompts

`engine/prompts/load_system_prompt(**kwargs)` + `system.md`(V2 트림 — Phase 0는 아티팩트/도구 지시
제외, 이후 Phase에서 확장). `LlmChatModel`이 메시지에 `SystemMessage`가 없으면 선주입한다.

### 5. Phase 0 범위 경계 (의도적 비포함)

- **도구 바인딩**: Phase 0 기본 모델은 도구를 바인딩하지 않는다(평범한 답변). `build_chat_model`은
  `tools` 인자를 받되 chat 기본 경로에선 비움 — 실 도구(RAG·MCP) 바인딩은 Phase 2+. HITL은 fake
  경로·단위테스트로 이미 검증됨.
- **토큰 단위 SSE**: 현재 그래프는 `stream_mode="updates"`(메시지 단위). 실 LLM 답변은 1건의
  `event: message`로 방출(진행형 토큰 아님). 토큰 SSE(`stream_mode="messages"`)는 Phase 1.
- **per-request 모델 선택**(`llm_resource_id`): Phase 1. Phase 0는 `core.config` 기본 모델 1종.
- **복원력**(circuit breaker·weighted random·registry fallback): V2의 선택 로직은 Phase 1+ 후속.
- **Langfuse 콜백을 LLM 호출에 주입**: 후속(ADR-0007 — 현재는 그래프 레벨 트레이스/flush만).

## Alternatives considered (대안)

| 대안 | 기각 사유 |
|------|-----------|
| V2 `LLMService` 그대로 이식 | `database`·`llm_resources` 직접 import → ADR-0005 위반. DB 결합을 engine에 들임. |
| `langchain-openai`만 사용(OpenAI 전용) | `llm_resource.provider`가 azure/anthropic/google/ollama를 가짐 → 멀티 provider 필요. LiteLLM이 V2와 일관. |
| 키 없을 때도 실모델 강제 | 로컬·CI·테스트가 키 없이 깨짐. HITL 데모(fake)의 결정성 상실. |
| engine이 `llm_resource` DB를 직접 조회 | 레이어 경계 위반. 해석은 domain, 주입은 값으로. |
| Phase 0에서 도구+토큰스트리밍까지 | 마일스톤 비대·리스크↑. "실 답변"을 먼저 세우고 점증. |

## Consequences (결과)

**긍정**
- 실 LLM 응답 능력 확보(데모 seam 제거 경로). ADR-0005 경계 유지(engine 순수·값 주입).
- LiteLLM로 provider 교체가 설정만으로 가능. V2 매핑 계승으로 이식 리스크↓.
- 키 토글로 로컬/운영 이원화 — 테스트·HITL 데모 불변.

**부정 / 리스크**
- 신규 의존성 `langchain-litellm`(+litellm) 추가 — `uv sync` 필요. provider SDK 호환성 표면 증가.
- 메시지 단위 스트림은 진행형 UX 아님(Phase 1에서 토큰 SSE로 개선).
- 기본 모델 1종·복원력 미비 — 운영 안정성은 Phase 1+ 후속에 의존.

**후속 작업 (다음 Phase)**
- Phase 1: 토큰 SSE(`stream_mode="messages"`) + 제목생성 + `llm_resource` 기반 per-request 모델 주입(domain 해석).
- Phase 1+: circuit breaker·weighted random·registry fallback(V2 `LLMService` 선택 로직), Langfuse 콜백 주입.
- Phase 2+: RAG·MCP 실도구를 모델에 바인딩(HITL 실동작), system.md 아티팩트/도구 지시 확장.
