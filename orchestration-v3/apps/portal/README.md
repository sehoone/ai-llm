# portal (사용자 포털)

최종 사용자용 Next.js 프론트엔드. 관리자 UI(`apps/web`)와 **별도 앱**으로 분리 — 설계 근거는
[ADR-0020](../../docs/adr/0020-user-portal-frontend.md).

- 백엔드·인증(ID/PW → JWT, ADR-0009)·`packages/contracts` 타입은 `web`과 **공유**한다.
- nginx 단일 진입점에서 `/` → portal, `/admin` → web, `/api/*` → api 로 라우팅.
- 로그인(`/login`) · **셀프 가입(`/register`, role=USER)** + 인증 게이트(`(authenticated)`) + 랜딩.
- **챗(`/chat`) — "클로드급" 코어(Phase 1, [portal-roadmap](../../docs/portal-roadmap.md))**:
  shadcn + 라이트/다크 테마 · **마크다운/코드 렌더링**(스트리밍 안전) · 스트리밍 **중단**·**복사**·**재생성** ·
  대화 **이름변경·삭제·검색** · 빈 상태+추천 프롬프트 · 모바일 드로어.
  - HITL 승인·첨부·아티팩트는 미지원(Phase 2~3). 가입 남용 방지는 1차 레이트리밋만.

## 구조

```
src/
├─ app/
│  ├─ layout.tsx · providers.tsx     # 루트 + Providers(theme·react-query·sonner)
│  ├─ login · register               # ID/PW 로그인 · 셀프 가입
│  └─ (authenticated)/               # access_token 쿠키 게이트(서버) — 없으면 /login
│     ├─ page.tsx                    # 랜딩
│     └─ chat/page.tsx               # 챗 (사이드바 + 메시지 + Composer 조립)
├─ components/
│  ├─ ui/*                           # shadcn 복사(button·input·textarea·dropdown·alert-dialog·sheet·skeleton)
│  ├─ theme-provider · theme-toggle  # next-themes
│  ├─ markdown.tsx                   # react-markdown+gfm+highlight(memo, 코드 복사)
│  └─ chat/*                         # sidebar·conversation-item·messages·message-bubble·composer·empty-state 등
├─ hooks/use-chat.ts                 # 오케스트레이션(로드·전송·중단·재생성·이름변경·삭제 + throttle)
├─ stores/{auth,chat}-store.ts       # zustand
├─ api/{axios,chat}.ts               # ApiResponse unwrap·Bearer·401 / 세션·메시지·fetch SSE(중단·재생성)
├─ lib/{utils,cookies,sse}.ts        # cn · 쿠키 · SSE 파서
└─ styles/{index,theme}.css          # tailwind v4 + shadcn 토큰(.dark) + hljs
```

## 개발

```bash
cd apps/portal && pnpm install
pnpm dev        # :3100 (web은 :3000 — 로컬 동시 구동 대비 포트 분리)
pnpm lint
pnpm build && pnpm start
```

로컬 dev는 `NEXT_PUBLIC_API_URL`이 비면 `/api` 상대경로 → `next.config` rewrite가
`localhost:8000`(api)로 프록시. docker 빌드는 `API_URL` build arg 사용(기본 `http://api:8000`).
