# domains

도메인 수직 슬라이스. 각 도메인은 다음 계층을 자체 보유한다:

```
<domain>/
├─ api.py          # FastAPI 라우터 (HTTP 경계)
├─ service.py      # 유스케이스/비즈니스 로직
├─ repository.py   # DB 접근 (SQLModel)
└─ schema.py       # 요청/응답 모델 (Pydantic)
```

> 파일명은 **단수**(`api`·`model`·`schema`) — 의도된 컨벤션입니다. FastAPI 통용 가이드의 복수형(`router`·`models`·`schemas`)과 다르지만 전 도메인이 일관되게 단수를 따릅니다.

## AI 도메인은 로직을 engine에 위임 (ADR-0005)

`chat·rag·agent·workflow·meeting`의 **실제 AI 연산(LLM 호출·프롬프트·그래프·툴·전사·ingestion)은
도메인이 소유하지 않는다** — `src/engine/`에 위임한다. 도메인 서비스는 유스케이스를 조율하고
engine을 호출할 뿐이다.

```
domains/<d>/service.py  ──>  engine/{llm,prompts,rag,agent,graph,memory,transcription}
```

- 도메인은 **HTTP 경계 + 관계형 영속화**(세션·메시지·레코드)만 소유. 벡터스토어는 `engine/rag`.
- `llm_resource`는 설정을 **값 객체로 engine에 주입**(engine은 설정 테이블을 읽지 않음).
- 자세한 경계 규칙은 [`../engine/README.md`](../engine/README.md).

## 도메인 목록

| 도메인 | 책임 | 출처 (V2) |
|--------|------|-----------|
| `chat` | LLM 채팅 (SSE 스트리밍) | orchestrator |
| `rag` | 문서 업로드·검색 (pgvector) | orchestrator |
| `agent` | AI 에이전트 (tool calling) | orchestrator |
| `workflow` | DAG 워크플로우 (LangGraph) | orchestrator |
| `meeting` | 음성 회의록 (업로드·전사·요약) | orchestrator |
| `user` | 사용자 조회·수정 | platform (Java→Python 포팅) |
| `api_key` | API 키 발급·폐기 | platform (Java→Python 포팅) |
| `llm_resource` | LLM 모델 리소스 설정 | platform (Java→Python 포팅) |
| `auth` | 사내 IdP OIDC 토큰 검증 (발급 없음) | 신규 (ADR-0003) |

> 현재는 골격 — 각 도메인은 빈 패키지입니다. 이식 단계에서 위 계층을 채웁니다.
