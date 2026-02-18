import type { Metadata } from "next";
import { ReactNode } from "react";
import "@/app/globals.css";
import { Providers } from "@/shell/providers";

export const metadata: Metadata = {
  title: "Shopify Multi-Supplier Platform",
  description: "Phase 7 frontend foundation",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" className="dark" style={{ colorScheme: "dark" }}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
          rel="stylesheet"
        />
      </head>
      <body suppressHydrationWarning style={{ background: "#0a0a0f" }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
