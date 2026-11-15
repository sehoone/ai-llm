/** @type {import('next').NextConfig} */
// 관리자 UI는 `/admin` 하위로 격리 (ADR-0020) — nginx가 `/admin`→web, `/`→portal로 라우팅.
// basePath는 Next의 라우트·자산에만 적용되고, 브라우저 axios는 동일 출처 `/api`를 호출한다.
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  basePath: '/admin',
  async rewrites() {
    return [
      {
        // basePath: false → dev 서버에서도 `/api/*`를 루트로 매칭(브라우저가 /admin/api가 아닌 /api 호출).
        source: '/api/:path*',
        destination: `${process.env.API_URL || 'http://localhost:8000'}/api/:path*`,
        basePath: false,
      },
    ];
  },
};

export default nextConfig;
