import React from 'react';
import { Panel } from '../../../components/ui/Panel';

interface FieldCoverageMatrixProps {
  coverage: Record<string, number>;
  totalSkus: number;
  isLoading?: boolean;
}

export const FieldCoverageMatrix: React.FC<FieldCoverageMatrixProps> = ({ coverage, totalSkus, isLoading }) => {
  if (isLoading) {
    return <div className="animate-pulse h-64 bg-[var(--surface-card)] border border-[var(--surface-border)]"></div>;
  }

  const fields = Object.keys(coverage);

  return (
    <Panel title="FIELD_COVERAGE_MATRIX">
      <div className="space-y-6">
        {fields.map(field => {
          const count = coverage[field];
          const percentage = totalSkus > 0 ? (count / totalSkus) * 100 : 0;
          
          return (
            <div key={field} className="group">
              <div className="flex justify-between items-end mb-2">
                <span className="text-[9px] font-mono text-[var(--text-dim)] uppercase tracking-widest">{field}</span>
                <span className="text-[10px] font-mono font-bold text-[var(--text-heading)] bg-[var(--surface-void)] px-1.5 border border-[var(--surface-border)]">
                  {percentage.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-[var(--surface-void)] h-1 border border-[var(--surface-border)] overflow-hidden">
                <div 
                  className={`h-full transition-all duration-1000 ${
                    percentage > 90 ? 'bg-[var(--brand-secondary)]' : percentage > 50 ? 'bg-[var(--brand-warning)]' : 'bg-red-500'
                  }`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <div className="text-[8px] text-[var(--text-dim)] mt-1.5 text-right font-mono uppercase tracking-tighter opacity-40">
                SAMPLED: {count.toLocaleString()} / {totalSkus.toLocaleString()} UNITS
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-6 pt-4 border-t border-[var(--surface-border)] opacity-30">
        <p className="text-[8px] text-[var(--text-dim)] font-mono uppercase leading-relaxed tracking-widest">
          [!] MATRIX_SIG: PERSISTENCE_VERIFIED
        </p>
      </div>
    </Panel>
  );
};
