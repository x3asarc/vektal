import React from 'react';

interface DashboardSummaryProps {
  data: {
    total_skus: number;
    avg_completeness: number;
    healthy_skus: number;
    unhealthy_skus: number;
    last_ingest_at: string | null;
    store_domain: string;
  };
  isLoading?: boolean;
}

export const DashboardSummary: React.FC<DashboardSummaryProps> = ({ data, isLoading }) => {
  if (isLoading) {
    return <div className="animate-pulse h-32 bg-gray-100 rounded-lg"></div>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {/* Total SKUs */}
      <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Total Catalog size</div>
        <div className="text-2xl font-bold text-gray-900">{data.total_skus.toLocaleString()}</div>
        <div className="text-xs text-gray-400 mt-1">{data.store_domain}</div>
      </div>

      {/* Avg Completeness */}
      <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Avg. Completeness</div>
        <div className="flex items-end gap-2">
          <div className="text-2xl font-bold text-blue-600">{data.avg_completeness.toFixed(1)}%</div>
        </div>
        <div className="w-full bg-gray-100 h-1.5 rounded-full mt-2 overflow-hidden">
          <div 
            className="bg-blue-500 h-full transition-all duration-500" 
            style={{ width: `${data.avg_completeness}%` }}
          />
        </div>
      </div>

      {/* Healthy SKUs */}
      <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Healthy SKUs (≥90%)</div>
        <div className="text-2xl font-bold text-green-600">{data.healthy_skus.toLocaleString()}</div>
        <div className="text-xs text-green-500 mt-1">✓ Ready for production</div>
      </div>

      {/* Unhealthy SKUs */}
      <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm border-l-4 border-l-red-500">
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">Action Required</div>
        <div className="text-2xl font-bold text-red-600">{data.unhealthy_skus.toLocaleString()}</div>
        <div className="text-xs text-red-400 mt-1">! Critical data missing</div>
      </div>
    </div>
  );
};
