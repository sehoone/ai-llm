/** @type {import('next').NextConfig} */
// 사용자 포털(ADR-0020) — 단일 도메인에서 nginx가 `/`로 라우팅. web(관리자)은 `/admin`.
// 브라우저는 동일 출처 `/api`를 호출하고, 로컬 dev는 아래 rewrite가 API로 프록시한다.
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
