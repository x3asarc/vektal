import React from 'react';

interface KPIProps {
  label: string;
  value: string | number;
  subValue?: string;
  variant?: 'default' | 'success' | 'warning' | 'error';
  isLoading?: boolean;
}

/**
 * Global KPI component utilizing the "Forensic OS" design identity.
 * Uses the .forensic-kpi class from forensic-theme.css.
 */
export const KPI: React.FC<KPIProps> = ({ label, value, subValue, variant = 'default', isLoading }) => {
  if (isLoading) {
    return <div className="animate-pulse h-24 bg-[var(--surface-card)] border border-[var(--surface-border)]"></div>;
  }

  const colors = {
    default: "text-[var(--text-heading)]",
    success: "text-[var(--brand-secondary)]",
    warning: "text-[var(--brand-warning)]",
    error: "text-red-500"
  };

  return (
    <div className="forensic-kpi relative">
      {/* Visual Pip for KPI */}
      <div className="absolute top-0 left-0 w-1 h-1 bg-[var(--brand-primary)] opacity-40"></div>
      
      <h3>{label}</h3>
      <div className="flex items-baseline gap-2">
        <p className={`font-mono text-xl font-bold ${colors[variant]}`}>
          {value}
        </p>
        {subValue && (
          <span className="text-[10px] font-mono text-[var(--text-dim)] uppercase tracking-wider">
            {subValue}
          </span>
        )}
      </div>
    </div>
  );
};
