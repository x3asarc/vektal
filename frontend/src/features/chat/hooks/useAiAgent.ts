"use client";

import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useMemo } from 'react';

export function useAiAgent() {
  const { messages, input, setInput, handleSubmit, status, error, reload, stop } = useChat({
    transport: new DefaultChatTransport({
      api: '/api/chat',
    }),
    // Support for tools can be added here
  });

  const isLoading = status === 'submitted' || status === 'streaming';
  
  // Map AI SDK messages to our ChatUiMessage format if needed, 
  // but for now we'll just use the SDK's messages directly in the workspace.
  
  return {
    messages,
    input,
    setInput,
    handleSendMessage: (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!input.trim() || isLoading) return;
      handleSubmit(e);
    },
    isLoading,
    status,
    error: error?.message || null,
    reload,
    stop
  };
}
