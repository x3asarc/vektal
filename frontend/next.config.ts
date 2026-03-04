import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const apiProxyOrigin = (process.env.NEXT_PRIVATE_API_PROXY_ORIGIN ?? "http://localhost:5000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Required for Docker production builds
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

export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,
  silent: true,
});
