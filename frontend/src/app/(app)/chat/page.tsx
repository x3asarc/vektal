import { Suspense } from "react";
import { ChatWorkspace } from "@/features/chat/components/ChatWorkspace";

export const CHAT_WORKSPACE_SECTIONS = [
  "session-timeline",
  "composer",
  "action-controls",
  "bulk-panel",
] as const;

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="chat-page" data-testid="chat-workspace-loading" />}>
      <ChatWorkspace />
    </Suspense>
  );
}
