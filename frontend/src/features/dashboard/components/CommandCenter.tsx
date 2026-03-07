import React, { useEffect, useState } from 'react';
import { DashboardSummary } from './DashboardSummary';
import { FieldCoverageMatrix } from './FieldCoverageMatrix';
import { ChatWorkspace } from '../../chat/components/ChatWorkspace';

interface DashboardData {
  total_skus: number;
  avg_completeness: number;
  healthy_skus: number;
  unhealthy_skus: number;
  last_ingest_at: string | null;
  field_coverage: Record<string, number>;
  store_domain: string;
}

export const CommandCenter: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        // Using relative path for the API call
        const response = await fetch('/api/v1/ops/dashboard/summary');
        if (!response.ok) {
          throw new Error('Failed to fetch dashboard summary');
        }
        const result = await response.json();
        setData(result);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, []);

  return (
    <div className="max-w-[1600px] mx-auto p-6 lg:p-8">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Product Data Command Center</h1>
        <p className="text-sm text-gray-500 mt-1">Real-time catalog health and operational control.</p>
      </header>

      {error && (
        <div className="mb-8 p-4 bg-red-50 border border-red-100 text-red-700 rounded-lg text-sm">
          Error: {error}
        </div>
      )}

      {/* Main Stats Row */}
      {data && <DashboardSummary data={data} isLoading={loading} />}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Metrics & Visualizations (4 cols) */}
        <div className="lg:col-span-4 space-y-8">
          {data && (
            <FieldCoverageMatrix 
              coverage={data.field_coverage} 
              totalSkus={data.total_skus} 
              isLoading={loading} 
            />
          )}
          
          <div className="bg-blue-600 rounded-lg p-6 text-white shadow-lg shadow-blue-100">
            <h3 className="text-sm font-bold uppercase tracking-wider mb-2">Automated Insights</h3>
            <p className="text-blue-100 text-sm leading-relaxed">
              {data && data.unhealthy_skus > 0 
                ? `You have ${data.unhealthy_skus} products requiring attention. Use the chat to start an enrichment run for missing fields.`
                : "Your catalog is 100% healthy. All critical fields are populated across all SKUs."}
            </p>
            <button className="mt-4 px-4 py-2 bg-white text-blue-600 rounded text-xs font-bold uppercase hover:bg-blue-50 transition-colors">
              Start Auto-Fix Run
            </button>
          </div>
        </div>

        {/* Right Column: Chat Control Plane (8 cols) */}
        <div className="lg:col-span-8 bg-gray-50 border border-gray-200 rounded-xl overflow-hidden flex flex-col min-h-[600px] shadow-sm">
          <div className="bg-white border-b border-gray-200 p-4 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs font-bold uppercase tracking-widest text-gray-700">Operational Control Dock</span>
            </div>
            <span className="text-[10px] font-mono text-gray-400 uppercase">Authenticated Session</span>
          </div>
          <div className="flex-1 overflow-hidden flex flex-col">
            <ChatWorkspace />
          </div>
        </div>
      </div>
    </div>
  );
};
