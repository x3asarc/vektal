"use client";

import React, { useRef, useEffect } from "react";
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { Button } from "@/components/ui/Button";
import { MessageBlockRenderer } from "./MessageBlockRenderer";

export function AiChatWorkspace() {
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const { messages, input, handleInputChange, handleSubmit, status, error } = useChat({
    transport: new DefaultChatTransport({
      api: '/api/chat',
    }),
  });

  const isLoading = status === 'submitted' || status === 'streaming';

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-[var(--surface-raised)] overflow-hidden">
      {/* Header bar */}
      <header className="px-6 py-4 border-b border-[var(--surface-border)] bg-[var(--surface-raised)] flex justify-between items-center">
        <div className="flex items-center gap-3">
          <span className="material-symbols-rounded text-[var(--brand-primary)] animate-pulse">
            robot_2
          </span>
          <h1 className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-[var(--text-heading)]">
            Forensic_Brain_v4.0
          </h1>
        </div>
        <div className="flex items-center gap-2">
           <span className={`w-2 h-2 rounded-full ${isLoading ? 'bg-amber-400 animate-pulse' : 'bg-green-400'}`}></span>
           <span className="text-[10px] font-mono text-[var(--text-dim)] uppercase tracking-widest">
             {isLoading ? 'Processing' : 'Standby'}
           </span>
        </div>
      </header>

      {/* Message Timeline */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-10 opacity-40">
            <span className="material-symbols-rounded text-4xl mb-4">terminal</span>
            <p className="text-[11px] font-mono uppercase tracking-[0.1em] max-w-xs">
              System initialized. Awaiting operational instruction...
            </p>
          </div>
        ) : (
          messages.map((m) => (
            <div 
              key={m.id} 
              className={`flex flex-col gap-2 ${m.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-[var(--text-dim)]">
                  {m.role === 'user' ? 'Operator' : 'Agent'}
                </span>
                {m.role === 'assistant' && (
                  <span className="text-[8px] border border-[var(--brand-primary)]/30 text-[var(--brand-primary)] px-1 rounded">
                    L3_FORENSIC
                  </span>
                )}
              </div>
              <div 
                className={`max-w-[85%] p-4 border ${
                  m.role === 'user' 
                    ? 'bg-[var(--brand-primary)]/5 border-[var(--brand-primary)]/20 text-[var(--text-heading)]' 
                    : 'bg-white/3 border-[var(--surface-border)] text-[var(--text-body)]'
                }`}
              >
                <div className="text-[12px] font-mono leading-relaxed whitespace-pre-wrap">
                  {m.content}
                </div>
              </div>
            </div>
          ))
        )}
        
        {error && (
          <div className="p-4 border border-red-900/40 bg-red-950/20 text-red-400 text-[10px] font-mono uppercase tracking-widest">
            ERROR: {error.message || "Transport failure. Check console for details."}
          </div>
        )}
      </div>

      {/* Input Area */}
      <footer className="p-6 border-t border-[var(--surface-border)] bg-[var(--surface-void)]/30">
        <form 
          onSubmit={handleSubmit}
          className="relative flex items-end gap-3"
        >
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={handleInputChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim() && !isLoading) {
                    const formEvent = new Event('submit', { cancelable: true, bubbles: true });
                    e.currentTarget.form?.dispatchEvent(formEvent);
                  }
                }
              }}
              placeholder="Query catalog, initiate repairs, or scan for anomalies..."
              className="w-full bg-[var(--surface-raised)] border border-[var(--surface-border)] p-4 pr-12 text-[12px] font-mono text-[var(--text-heading)] focus:outline-none focus:border-[var(--brand-primary)]/50 transition-colors resize-none scrollbar-none"
              rows={2}
              disabled={isLoading}
            />
            <div className="absolute right-3 bottom-3 flex items-center gap-2">
               <span className="text-[8px] font-mono text-[var(--text-dim)] opacity-40 uppercase">Shift+Enter for newline</span>
            </div>
          </div>
          <Button 
            type="submit" 
            variant="primary" 
            className="h-[58px] w-[58px] flex items-center justify-center !p-0"
            disabled={!input.trim() || isLoading}
          >
            {isLoading ? (
              <span className="material-symbols-rounded animate-spin">sync</span>
            ) : (
              <span className="material-symbols-rounded">send</span>
            )}
          </Button>
        </form>
        <div className="mt-4 flex justify-between items-center opacity-40">
           <span className="text-[8px] font-mono uppercase tracking-[0.2em]">Transport: AI_SDK_V4_SSE</span>
           <span className="text-[8px] font-mono uppercase tracking-[0.2em]">Protocol: VERCEL_DATA_STREAM</span>
        </div>
      </footer>
    </div>
  );
}
