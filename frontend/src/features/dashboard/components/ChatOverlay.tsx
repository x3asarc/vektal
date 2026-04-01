"use client";

import React from "react";
import { ChatWorkspace } from "../../chat/components/ChatWorkspace";
import { Button } from "../../../components/ui/Button";

interface ChatOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ChatOverlay: React.FC<ChatOverlayProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 md:p-10 animate-in fade-in duration-300">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-[var(--surface-void)]/80 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Chat Container */}
      <div className="relative w-full max-w-5xl h-full max-h-[90vh] bg-[var(--surface-raised)] border border-[var(--surface-border)] shadow-2xl flex flex-col animate-in zoom-in-95 slide-in-from-bottom-4 duration-300">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--surface-border)] bg-[var(--surface-raised)]">
          <div className="flex items-center gap-3">
            <span className="material-symbols-rounded text-[var(--brand-primary)]">terminal</span>
            <h2 className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-[var(--text-heading)]">
              Operational_Control_Dock v1.0
            </h2>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="!p-1 h-auto">
            <span className="material-symbols-rounded text-sm">close</span>
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <ChatWorkspace />
        </div>
        
        {/* Footer info */}
        <div className="px-6 py-2 bg-[var(--surface-void)] border-t border-[var(--surface-border)] flex justify-between items-center">
          <span className="text-[8px] font-mono text-[var(--text-dim)] uppercase tracking-tighter">
            Encryption: AES-256-GCM // Tenant: ISOLATED
          </span>
          <span className="text-[8px] font-mono text-[var(--brand-primary)] uppercase tracking-widest animate-pulse">
            System_Ready
          </span>
        </div>
      </div>
    </div>
  );
};
