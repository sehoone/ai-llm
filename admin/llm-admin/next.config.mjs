/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // If you are using Clerk, you might need to add this
  // images: {
  //   domains: ['images.clerk.dev'],
  // },
};

export default nextConfig;
