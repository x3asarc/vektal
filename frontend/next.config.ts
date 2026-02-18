import type { NextConfig } from "next";

const apiProxyOrigin = (process.env.NEXT_PRIVATE_API_PROXY_ORIGIN ?? "http://localhost:5000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: process.cwd(),
  },
  // Next.js expects async rewrites in config shape.
  // eslint-disable-next-line @typescript-eslint/require-await
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiProxyOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
