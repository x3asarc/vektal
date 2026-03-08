import React from 'react';

interface PanelProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  icon?: React.ReactNode;
}

/**
 * Global Panel component utilizing the "Forensic OS" design identity.
 * Uses the .panel class defined in forensic-theme.css for 100% congruence.
 */
export const Panel: React.FC<PanelProps> = ({ children, className = '', title, icon }) => {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <div className="border-b border-[var(--surface-border)] px-4 py-3 bg-white/[0.02] flex items-center justify-between">
          <div className="flex items-center gap-3">
            {icon && <span className="text-[var(--brand-primary)] opacity-80">{icon}</span>}
            <h3 className="text-[10px] font-bold text-[var(--text-heading)] uppercase tracking-[0.25em] font-mono">
              {title}
            </h3>
          </div>
        </div>
      )}
      <div className={title ? 'p-6' : ''}>
        {children}
      </div>
    </section>
  );
};
