# AI Admin Dashboard

## 기술스텍

- **Framework**: [Next.js 16+](https://nextjs.org/)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS 4](https://tailwindcss.com/)
- **UI Library**: [Shadcn UI](https://ui.shadcn.com) (Radix UI)
- **Icons**: [Lucide React](https://lucide.dev/), [Radix UI Icons](https://icons.radix-ui.com/)
- **State Management**: [Zustand](https://github.com/pmndrs/zustand)
- **Data Fetching**: [TanStack Query](https://tanstack.com/query/latest), [Axios](https://axios-http.com/)
- **Tables**: [TanStack Table](https://tanstack.com/table/v8)
- **Forms**: [React Hook Form](https://react-hook-form.com/) + [Zod](https://zod.dev/)
- **Charts**: [Recharts](https://recharts.org/)
- **Utils**: [date-fns](https://date-fns.org/), [Input OTP](https://input-otp.rodneyLab.com/)

## 프로젝트 구조

```
src/
├── api/                 # API related code
├── app/                 # Next.js App Router pages & layouts
│   ├── (auth)/          # Authentication routes
│   ├── (authenticated)/ # Protected dashboard routes
│   ├── (errors)/        # Error pages
│   └── clerk/           # Clerk authentication pages
├── assets/              # Static assets (icons, images)
├── components/          # Shared UI components
│   ├── ui/              # Shadcn UI primitives
│   └── ...              # Custom components
├── config/              # Configuration files
├── context/             # React Context providers
├── features/            # Feature-based modules
│   ├── apps/            # App integrations
│   ├── auth/            # Authentication features
│   ├── chats/           # Chat features
│   ├── dashboard/       # Dashboard features
│   ├── errors/          # Error handling features
│   ├── settings/        # Settings features
│   ├── tasks/           # Task management features
│   └── users/           # User management features
├── hooks/               # Custom React hooks
├── lib/                 # Utility functions & configurations
├── routes/              # Route definitions
├── stores/              # Zustand state stores
└── styles/              # Global styles
```

## Getting Started

### Prerequisites

- Node.js 18+
- pnpm (recommended) or npm/yarn

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   ```

2. **Install dependencies**

   ```bash
   pnpm i
   ```

3. **Environment Setup**

   Copy the example environment file and configure your variables.

   ```bash
   cp .env.example .env.local
   ```

4. **Run the development server**

   ```bash
   pnpm dev
   ```

   Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Scripts

- `pnpm dev`: Starts the development server.
- `pnpm build`: Builds the application for production.
- `pnpm start`: Runs the built production application.
- `pnpm lint`: Runs ESLint to check for code quality issues.
- `pnpm format`: Formats code using Prettier.

## 참고소스
- https://github.com/satnaing/shadcn-admin (해당 프로젝트를 base로 프레임워크를 next.js로 변경해서 사용)

## Docker 배포

### 필수 조건
- 프로젝트 루트에 환경 변수 파일(`.env.production` 등)이 있어야 합니다. (예: `.env.example` 복사 후 수정)

### 기본 배포 (Production)
기본적으로 `.env.production` 파일을 사용하여 빌드합니다.

```bash
docker-compose up -d --build
```

### 특정 환경 설정 파일로 배포
다른 환경 설정 파일(예: `.env.staging`)을 사용하여 배포하려면 `docker-compose.yml`을 수정하거나 아래와 같이 빌드 인자를 전달하세요.

```bash
docker-compose build --build-arg ENV_FILE=.env.production
docker-compose up -d
```
