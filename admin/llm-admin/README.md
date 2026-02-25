# LLM Admin Dashboard

AI LLM 플랫폼을 위한 관리자 웹 UI입니다. Next.js 16 App Router 기반으로 구축되었습니다.

> 참고 소스: [shadcn-admin](https://github.com/satnaing/shadcn-admin) 를 베이스로 Next.js App Router 구조로 재구성

## 기술 스택

- **Framework**: [Next.js 16](https://nextjs.org/) (App Router)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Package Manager**: pnpm
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com/)
- **UI Library**: [shadcn/ui](https://ui.shadcn.com) (Radix UI)
- **Icons**: [Lucide React](https://lucide.dev/), [Radix UI Icons](https://icons.radix-ui.com/)
- **State Management**: [Zustand](https://github.com/pmndrs/zustand)
- **Data Fetching**: [TanStack Query v5](https://tanstack.com/query/latest), [Axios](https://axios-http.com/)
- **Tables**: [TanStack Table v8](https://tanstack.com/table/v8)
- **Forms**: [React Hook Form](https://react-hook-form.com/) + [Zod v4](https://zod.dev/)
- **Charts**: [Recharts](https://recharts.org/)
- **3D**: [@react-three/fiber](https://docs.pmnd.rs/react-three-fiber), [@react-three/drei](https://github.com/pmndrs/drei)
- **Speech**: [Azure Cognitive Services Speech SDK](https://github.com/microsoft/cognitive-services-speech-sdk-js)
- **Logging**: [pino](https://getpino.io/) (dev: debug, production: warn+)

## 주요 기능

| 기능 | 경로 | 설명 |
|------|------|------|
| 대시보드 | `/` | 분석 개요 및 통계 |
| 채팅 | `/chats` | LLM 세션 관리, SSE 스트리밍 응답 |
| My GPTs | `/gpts` | 커스텀 GPT 생성/수정/삭제/채팅 |
| 채팅 이력 | `/chat-history` | 과거 대화 내역 조회 |
| RAG 문서 | `/rag-documents` | RAG 지식 베이스 문서 업로드/관리 |
| 자연어 검색 | `/natural-search` | 데이터 소스에 대한 자연어 검색 |
| AI 음성 평가 | `/evaluation` | AI 음성 인터뷰 평가 (한국어, WebSocket + Azure STT/TTS) |
| 사용자 관리 | `/users` | 사용자 CRUD |
| LLM 리소스 | `/llm-resources` | LLM 프로바이더 엔드포인트 설정 (failover/fallback) |
| API 키 | `/api-keys` | 인증 키 관리 |

## 시작하기

### 사전 요구사항

- Node.js 20+
- pnpm

### 설치 및 실행

```bash
# 의존성 설치
pnpm install

# 환경 변수 설정
cp .env.example .env

# 개발 서버 실행 (포트 3000)
pnpm dev
```

브라우저에서 [http://localhost:3000](http://localhost:3000) 을 열어 확인합니다.

### 환경 변수

```env
NEXT_PUBLIC_API_URL=http://localhost:8000  # 클라이언트 사이드 및 WebSocket URL
API_URL=http://localhost:8000              # Next.js 리라이트 프록시용
```

`next.config.mjs`가 `/api/*` 요청을 `${API_URL}/api/*`로 프록시합니다.
클라이언트 사이드 axios는 `NEXT_PUBLIC_API_URL`을 직접 사용합니다 (폴백: `/api`).

## 개발 명령어

```bash
pnpm dev          # 개발 서버 실행 (포트 3000)
pnpm build        # 프로덕션 빌드 (standalone output)
pnpm start        # 프로덕션 서버 실행
pnpm lint         # ESLint 실행
pnpm format       # Prettier 포맷팅
pnpm format:check # 포맷팅 검사
pnpm knip         # 미사용 코드 분석
```

## Docker 배포

```bash
# 기본 빌드 (.env 파일 사용)
docker build --build-arg ENV_FILE=.env -t llm-admin .
docker run -p 3000:3000 llm-admin

# 특정 환경 파일로 빌드
docker build --build-arg ENV_FILE=.env.staging -t llm-admin .
```

빌드 시 `ENV_FILE` 인수로 지정한 파일이 컨테이너 내부의 `.env.production`으로 복사됩니다.

## 아키텍처

### 라우트 그룹

```
src/app/
├── (auth)/           # 공개 페이지 (sign-in, sign-up, forgot-password, otp)
├── (authenticated)/  # 인증 필요 페이지
│   │                 #   → access_token 쿠키 없으면 /sign-in 리다이렉트
│   ├── chats/
│   ├── gpts/
│   ├── chat-history/
│   ├── rag-documents/
│   ├── natural-search/
│   ├── evaluation/
│   ├── users/
│   ├── llm-resources/
│   └── api-keys/
└── (errors)/         # 독립형 에러 페이지 (401, 403, 500, 503)
```

### 인증

- JWT 토큰을 쿠키에 저장: `access_token`, `refresh_token`, `expires_at`
- 클라이언트 상태: Zustand (`src/stores/auth-store.ts`) — 로드 시 쿠키에서 초기화
- Axios 인터셉터(`src/api/axios.ts`)가 만료 전 토큰 자동 갱신 및 401 시 재시도 처리 (`/api/v1/auth/refresh` 호출)

### 피처 구조

각 피처는 `src/features/<feature-name>/index.tsx`를 진입점으로 가지며, `src/app/(authenticated)/` 페이지에서 단순히 import하여 렌더링합니다.

### API 레이어

`src/api/` 하위에 기능별 파일로 분리:

| 파일 | 설명 |
|------|------|
| `axios.ts` | 공유 Axios 인스턴스 (토큰 갱신 인터셉터) |
| `auth.ts` | 인증 API |
| `chat.ts` | `chatService.streamMessage()` — ReadableStream 기반 SSE |
| `custom-gpts.ts` | 커스텀 GPT CRUD |
| `rag.ts` | 문서 업로드 및 관리 |
| `users.ts` | 사용자 관리 |
| `api-keys.ts` | API 키 관리 |
| `llm-resources.ts` | LLM 리소스 설정 |

### WebSocket (AI 음성 평가 기능)

- `src/utils/websocket.ts` — `WebSocketClient` 클래스 (연결, 재연결, 메시지 프레이밍)
- `src/hooks/websocket/useWebSocket.ts` — React 훅 (`sendText`, `sendAudio`, `evaluate`, `reset`)
- `src/hooks/audio/` — 오디오 캡처, 음성 인식 훅 (Azure Speech SDK)
- WebSocket URL: `NEXT_PUBLIC_API_URL`에서 http→ws 자동 변환

### 레이아웃 시스템

사이드바 상태가 쿠키에 저장되어 서버 렌더링 시 사용:

| 쿠키 키 | 설명 |
|---------|------|
| `sidebar_state` | 사이드바 열림 여부 |
| `layout_collapsible` | 접힘 방식 (`icon` 기본값) |
| `layout_variant` | 레이아웃 변형 (`inset` 기본값) |

### 글로벌 프로바이더

`src/app/providers.tsx`에서 앱 전체를 감쌉니다:
- TanStack Query (dev에서 401/403 자동 재시도 비활성화, stale time 10초)
- DirectionProvider, FontProvider, ThemeProvider
- mutation 에러 toast 처리 (`src/lib/handle-server-error.ts`)

## 프로젝트 구조

```
src/
├── api/              # API 함수 (Axios 기반)
├── app/              # Next.js App Router 페이지
│   ├── (auth)/       # 공개 인증 페이지
│   ├── (authenticated)/ # 보호된 기능 페이지
│   └── (errors)/     # 에러 페이지
├── assets/           # 정적 자산 (브랜드 아이콘 등)
├── components/       # 공유 UI 컴포넌트
│   ├── layout/       # Header, Main, Sidebar 레이아웃 컴포넌트
│   └── ui/           # shadcn/ui 컴포넌트
├── config/           # 앱 설정 (폰트, 모델, UI)
├── context/          # React Context 프로바이더
├── features/         # 기능별 모듈
│   ├── chats/        # 채팅 (SSE 스트리밍)
│   ├── gpts/         # 커스텀 GPT
│   ├── chat-history/ # 채팅 이력
│   ├── rag-documents/ # RAG 문서
│   ├── natural-search/ # 자연어 검색
│   ├── evaluation/   # AI 음성 평가
│   ├── users/        # 사용자 관리
│   ├── llm-resources/ # LLM 리소스
│   ├── api-keys/     # API 키
│   └── dashboard/    # 대시보드
├── hooks/            # 공유 React 훅
│   ├── audio/        # 오디오 캡처, 음성 인식
│   └── websocket/    # WebSocket 훅
├── lib/              # 유틸리티 (logger, cookies, error handling)
├── stores/           # Zustand 스토어
├── styles/           # 전역 스타일 (Tailwind CSS v4 테마)
├── types/            # TypeScript 타입 정의
└── utils/            # 유틸리티 (WebSocketClient)
```
