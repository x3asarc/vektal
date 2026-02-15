import { ChatWorkspace } from "@/features/chat/components/ChatWorkspace";

export const CHAT_WORKSPACE_SECTIONS = [
  "session-timeline",
  "composer",
  "action-controls",
  "bulk-panel",
] as const;

export default function ChatPage() {
  return <ChatWorkspace />;
}
