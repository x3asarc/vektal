import { ReactNode } from "react";
import { ForensicShell } from "@/shell/components/ForensicShell";

type AppLayoutProps = {
  children: ReactNode;
};

export default function AppLayout({ children }: AppLayoutProps) {
  return <ForensicShell>{children}</ForensicShell>;
}
