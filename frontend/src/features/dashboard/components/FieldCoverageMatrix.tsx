import React from 'react';

interface FieldCoverageMatrixProps {
  coverage: Record<string, number>;
  totalSkus: number;
  isLoading?: boolean;
}

export const FieldCoverageMatrix: React.FC<FieldCoverageMatrixProps> = ({ coverage, totalSkus, isLoading }) => {
  if (isLoading) {
    return <div className="animate-pulse h-48 bg-gray-100 rounded-lg"></div>;
  }

  const fields = Object.keys(coverage);

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
      <h3 className="text-sm font-bold text-gray-900 mb-4 uppercase tracking-tighter">Field Coverage Matrix</h3>
      <div className="space-y-4">
        {fields.map(field => {
          const count = coverage[field];
          const percentage = totalSkus > 0 ? (count / totalSkus) * 100 : 0;
          
          return (
            <div key={field} className="group">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-mono text-gray-600 uppercase">{field}</span>
                <span className="text-xs font-mono font-bold text-gray-900">{percentage.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-50 h-4 border border-gray-100 rounded flex overflow-hidden">
                <div 
                  className={`h-full transition-all duration-700 ${
                    percentage > 90 ? 'bg-green-400' : percentage > 50 ? 'bg-yellow-400' : 'bg-red-400'
                  }`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5 text-right font-mono">
                {count.toLocaleString()} / {totalSkus.toLocaleString()} products
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-6 pt-4 border-t border-gray-100">
        <p className="text-[11px] text-gray-500 italic">
          * This matrix shows the percentage of products that have a non-empty value for each specific field.
        </p>
      </div>
    </div>
  );
};
