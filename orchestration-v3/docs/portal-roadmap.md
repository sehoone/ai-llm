# 사용자 포털 로드맵 — "클로드급" 챗 경험

`apps/portal`을 **Claude.ai 수준의 사용자 챗 제품**으로 끌어올리는 단계별 계획.
분리 결정은 [ADR-0023](adr/0023-admin-portal-split.md)(관리자/사용자 포털 분리), 포털 프론트 구현·스코핑·
셀프가입은 [ADR-0020](adr/0020-user-portal-frontend.md), 챗 백엔드 계약은
ADR-0008(HITL)·0011(스트리밍)·0013(아티팩트)·0014(첨부)·0015(메모리) 참고.

> 이 문서는 **로드맵(실행 계획)** 이다 — 확정된 아키텍처 결정은 ADR에, 단계·작업·완료기준은 여기에 둔다.

## 목표 (Vision)

최종 사용자가 체감하는 Claude.ai의 핵심을 재현한다: **마크다운/코드 렌더링**, 세련된 스트리밍 UX(중단·
재생성·복사), 대화 관리, 라이트/다크 테마, (후속) 멀티모달 첨부·아티팩트 사이드 패널.

> **레버리지**: 백엔드는 이미 풍부하다(chat HITL·실 LLM·첨부·메모리·아티팩트·RAG·GPTs·AI오버뷰).
> 포털 작업은 대부분 **기존 백엔드 능력을 사용자 UX로 표면화**하는 프론트 작업이다.

## 단계 개요

| Phase | 주제 | 상태 |
|-------|------|------|
| **1** | "진짜 챗다운" 코어 — 디자인시스템·마크다운·스트리밍 제어(중단·재생성·복사)·대화관리·테마 | **완료(stg 실증)** |
| **2** | 멀티모달 & 아티팩트 — 첨부 업로드 + 아티팩트 사이드 패널(ADR-0013·0014) | **완료(stg 실증)** |
| **3** | 능력 확장 — HITL 승인·모델 선택·커스텀 GPT·RAG 그룹·장기메모리 삭제 | **완료(stg 실증)** · AI오버뷰 검색은 후속 |
| **4** | 제품화 마감 — 설정 페이지·단축키·로딩 스켈레톤·성능(memo) | **핵심 완료(stg 실증)** · 가상 스크롤·a11y 감사는 보류 |

현재(Phase 0 완료): 앱 분리·라우팅·공유 인증·로그인/셀프가입·**최소 챗**(plaintext + SSE 스트리밍 + 세션 목록/생성).

---

## Phase 1 — 코어 챗 (상세 설계)

> **구현 상태(2026-11-15)**: 아래 설계대로 코드 반영 완료. **셸에 uv/pnpm/node가 없어 lint/build/test는
> 미실행** — 사용자 검증 필요. 백엔드 재생성은 `chat_session.thread_rev` 컬럼 추가(init.sql 멱등 ALTER 포함).

### 범위
- **IN**: 디자인시스템(shadcn + 라이트/다크 + 반응형) · 마크다운/코드 렌더링 · 스트리밍 **중단(stop)** ·
  메시지 **복사** · **재생성(regenerate)** · 대화관리(이름변경·삭제·제목검색·새대화) · 빈 상태 + 추천 프롬프트.
- **OUT (후속)**: 첨부·아티팩트 패널·HITL·GPTs·RAG·메모리·모델선택·설정페이지·메시지 편집·메시지 본문 검색.

### 화면 구성
데스크톱 2-pane(좌: 대화 사이드바 / 우: 메시지 + 입력창), 모바일은 사이드바를 `Sheet` 드로어로.
```
┌─ 사이드바 ─┬─ 챗 ──────────────── [☾/☀] ┐
│ [+ 새 대화] │   (빈 상태) 무엇을 도와드릴까요? │
│ 🔍 검색…    │   [추천1][추천2][추천3][추천4]   │
│ • 세션들 ⋯ │   user ▸ / ◂ assistant(md·code) │
│ 👤 사용자⋯ │   ⧉복사 ↻재생성   [입력… ⏹/➤]   │
└─────────────┴─────────────────────────────────┘
```

### 디자인 시스템 (ADR-0020 결정: portal에 shadcn+테마 복사)
- web `src/components/ui/`에서 **사용하는 primitive만 복사** + `lib/cn.ts`(clsx+tailwind-merge).
- `styles/index.css`에 **shadcn 토큰 레이어 복사**(`:root`/`.dark` CSS 변수) — 현재 plain slate → 토큰 기반.
- 테마: **next-themes**(`class` 전략, SSR-safe). web의 다중 provider(font/direction)는 포팅하지 않음(린 유지).
- **추가 deps**: `react-markdown` `remark-gfm` `rehype-highlight`(+highlight.js css) · `class-variance-authority`
  `clsx` `tailwind-merge` · 필요한 `@radix-ui/react-*`(dropdown-menu·dialog·alert-dialog·tooltip·avatar·
  scroll-area·separator·slot) · `next-themes` · `lucide-react` · `tw-animate-css`.

### 마크다운/코드 렌더링 (스트리밍 안전)
- `react-markdown` + `remark-gfm`(표·체크리스트·취소선) + `rehype-highlight`(highlight.js — 가볍고 스트리밍 친화).
- 코드블록: 언어 라벨 + **복사 버튼**.
- **성능**: 토큰마다 재파싱되므로 `message-bubble`을 `content` 기준 `memo` + 렌더 **throttle(≈60–100ms)**.
- LaTeX(remark-math+rehype-katex)는 선택 — 수요 시 Phase 1.5.

### 스트리밍 제어
- **중단**: `api/chat.ts streamMessage`에 `AbortSignal` 추가 → `fetch({ signal })`. 페이지가 `AbortController`
  보유, 중단 버튼이 `abort()`. 중단 시 **부분 응답 보존** + `sending=false`.
- 타이핑 인디케이터(첫 토큰 전), 자동 스크롤(사용자가 위로 스크롤하면 고정 해제).

### 재생성(regenerate) — **Phase 1 포함, 백엔드 신규 필요**
마지막 user 메시지에 대한 답변을 새로 생성해 **직전 assistant 턴을 교체**(user 메시지 중복 없음).

**백엔드 — 신규 엔드포인트**: `POST /api/v1/chat/sessions/{id}/regenerate` (SSE, send와 동일 이벤트 포맷).
선택 body `{ llm_resource_id? }`(재생성 시 모델 변경 허용). 동작:
1. `get_session_owned` 소유권 검증.
2. DB 히스토리에서 **마지막 user 메시지 U** 식별(없으면 400). U 이후 메시지(직전 assistant/tool)와
   그 턴에 생성된 아티팩트 버전 정리(삭제).
3. **대화 스레드 포크** — `chat_session`에 `thread_rev`(int, 기본 0) 추가, `_run`의 `thread_id`를
   `f"{session.id}:{thread_rev}"`로 통일. regenerate가 rev를 +1 하고, 재구성한 히스토리 `[m0..U]`를
   그래프 입력으로 **새 스레드에 seed**해 재실행 → 새 assistant 스트리밍·영속. 이후 일반 전송은 새 rev
   스레드를 이어가므로 맥락 유지(InMemory 체크포인터 분기 폐기).

**제약/리스크**(로드맵 메모):
- 히스토리 재구성은 **텍스트 턴 기준**이 명확. tool-call/HITL이 섞인 턴의 정확한 LangChain 메시지 복원은
  엣지 케이스 — 1차는 best-effort, tool 턴 재생성은 Phase 3(HITL)와 함께 정교화.
- 대안(클린·장기): **DB 권위 히스토리**(매 턴 전체 히스토리를 그래프 입력으로 전달, 체크포인터 누적 비의존)로
  전환하면 regenerate가 trivial해지고 InMemory 재시작-맥락손실도 해소되나, HITL resume(interrupt 기반)과
  충돌하므로 별도 ADR 후보. **Phase 1은 thread-rev 포크 방식 채택.**

**프론트**: `api/chat.ts`에 `regenerate(sessionId, cb, signal)` 추가(fetch SSE). 마지막 assistant 버블의
↻ 버튼이 해당 버블 제거 후 새 스트림 수신.

### 대화 관리
- 이름변경 `PATCH /sessions/{id}`(존재) 인라인 편집 · 삭제 `DELETE /sessions/{id}`(존재) `alert-dialog` 확인.
- **검색**: 백엔드 세션 검색 없음 → **클라이언트 제목 필터**(로드된 목록). 메시지 본문 검색은 후속(백엔드 필요).
- 상태관리: **`stores/chat-store.ts`(zustand)** 도입 — 세션/메시지/스트리밍 상태를 페이지에서 분리.

### 파일 계획 (portal)
```
src/
├─ components/ui/*            # shadcn 복사(button·input·textarea·scroll-area·dropdown-menu·
│                             #   dialog·alert-dialog·tooltip·avatar·separator·skeleton·sheet·sonner)
├─ components/theme-provider.tsx · theme-toggle.tsx
├─ components/markdown.tsx
├─ components/chat/{chat-sidebar,conversation-item,chat-messages,message-bubble,
│                   message-actions,composer,empty-state,typing-indicator}.tsx
├─ lib/cn.ts                  # 신규
├─ api/chat.ts                # 변경: AbortSignal + regenerate()
├─ stores/chat-store.ts       # 신규(zustand)
├─ styles/index.css           # 변경: shadcn 토큰 + .dark + hljs 테마
└─ app/(authenticated)/chat/page.tsx   # 리라이트: 컴포넌트 조립 + store 연결

apps/api 측(재생성):
├─ domains/chat/model.py      # chat_session.thread_rev 추가
├─ domains/chat/api.py        # POST /sessions/{id}/regenerate
├─ domains/chat/service.py    # regenerate() + _run thread_id = f"{id}:{rev}"
└─ deploy/postgres/schema.sql # thread_rev 컬럼 (수동 관리 — create_all 없음)
```

### 작업 순서
1. **디자인시스템 토대** — deps · ui primitive·`cn` 복사 · 토큰/다크 `index.css` · 테마토글 → **빌드 확인**
2. **마크다운 렌더러**(memo·throttle·코드 복사)
3. **챗 페이지 리팩터** — sidebar/messages/composer를 shadcn으로, `chat-store` 연결
4. **스트리밍 제어** — AbortController 중단 · 타이핑 인디케이터
5. **재생성** — 백엔드 엔드포인트 + `thread_rev` + 프론트 ↻
6. **대화 관리** — 이름변경·삭제(alert)·제목검색
7. **빈 상태 + 추천 프롬프트 · 반응형(Sheet 드로어)**
8. **마감** — 스켈레톤·토스트·키보드·스크롤 거동

### 완료 기준 (Acceptance)
- 코드블록/표/리스트가 스트리밍 중에도 깨지지 않고 렌더.
- 전송 중 **중단**(부분 응답 보존) · 메시지 **복사** · **재생성**(직전 답변 교체, user 중복 없음) 동작.
- 대화 **이름변경·삭제·제목검색·새대화** 동작.
- **라이트/다크** 전환 · **모바일 드로어**.
- `uv run poe lint && uv run poe test`(api) · `pnpm lint && pnpm build`(portal) 통과.

---

## 후속 Phase (요약)

- **Phase 2 — 멀티모달 & 아티팩트**: 첨부 업로드(파일·이미지 드래그앤드롭, ADR-0014) · 아티팩트 사이드
  패널(스트리밍 렌더 + 버전 + 공유 링크, ADR-0013; web `artifact-renderer` 재사용). 공개 뷰어 relocation 검토.
- **Phase 3 — 능력 확장**: HITL 승인 UI(ADR-0008) · 커스텀 GPT 사용 화면 · RAG/AI오버뷰 검색 · 장기메모리
  토글·관리(ADR-0015) · 모델 선택(llm_resource). tool 턴 재생성 정교화.
- **Phase 4 — 제품화 마감**: ✅ 설정 페이지(프로필·비밀번호·테마·메모리) · ✅ 키보드 단축키(⌘/Ctrl+K) ·
  ✅ 로딩 스켈레톤 · ✅ 성능(MessageBubble memo). **보류**: 가상 스크롤(대화가 수백 메시지일 때만 필요 —
  현재 memo로 충분) · 전체 접근성 감사. **(선택)**: 메시지 본문 검색 백엔드 · 가입 2차(이메일 인증·초대) ·
  운영 서브도메인 전환.
