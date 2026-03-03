import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  sendDefaultPii: true,
  enableLogs: true,
  tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.1"),
  environment: process.env.SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,
  release: process.env.SENTRY_RELEASE,
});
