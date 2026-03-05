import { Suspense } from "react";
import { ChatWorkspace } from "@/features/chat/components/ChatWorkspace";

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="chat-page" data-testid="chat-workspace-loading" />}>
      <ChatWorkspace />
    </Suspense>
  );
}
