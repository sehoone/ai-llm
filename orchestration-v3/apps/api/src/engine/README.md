# engine

AI 실행 능력(capability) 레이어. HTTP 도메인과 분리된 AI 연산의 집(ADR-0005).

## 경계 규칙 (단방향)

```
domains  ──>  engine  ──>  core(config·db)
```

- **engine은 `domains`를 import하지 않는다** (역의존·순환 금지).
- **engine은 FastAPI·HTTP를 모른다** — 라우팅·요청/응답 스키마·인증은 `domains`/`core` 소유.
- engine은 `core.config`와 `core.db`(벡터 연산용)만 의존한다.
- 관계형 도메인 테이블 CRUD는 `domains/<d>/repository.py`, 벡터스토어(pgvector)는 `engine/rag`.

## 능력 목록

| 모듈 | 책임 | 사용 도메인 |
|------|------|-------------|
| `llm/`     | 모델 호출 추상화 (provider·chat·stream), 프로바이더 중립 | chat·agent·rag·workflow·meeting |
| `prompts/` | 프롬프트 템플릿 (Git 버전관리, 로직 분리) + 로더 | chat·agent·rag·meeting |
| `rag/`     | ingestion·chunking·embedding·retrieval + 벡터스토어 어댑터 | rag |
| `agent/`   | tool 정의·레지스트리·tool calling 실행 | agent |
| `graph/`   | LangGraph 워크플로 그래프·노드 정의 | workflow |
| `memory/`  | 대화 메모리 | chat·agent |
| `transcription/` | 음성 전사 (Whisper 등) | meeting |

## 설정 주입 (llm_resource 역의존 회피)

engine은 모델 설정 테이블을 읽지 않는다. 도메인 서비스가 `llm_resource`를 해석해
**값 객체로 주입**한다: `llm_resource.repository → ModelConfig → engine.llm.chat(config, ...)`.

## 위치

현재 소비자는 `apps/api` 하나라 앱 내부(`src/engine/`)에 둔다. `apps/worker`가 engine 능력
(전사·ingestion)을 쓰게 되면 `packages/engine` 공유 라이브러리로 승격한다(ADR-0005 §6).

> 현재는 골격 — 각 모듈은 빈 패키지입니다. 도메인 이식 단계에서 채웁니다.
