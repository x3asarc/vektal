import React from 'react';
import { KPI } from '../../../components/ui/KPI';

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
  const missingCritical = data.total_skus > 0 ? (data.unhealthy_skus / data.total_skus) * 100 : 0;
  const seoReadiness = data.avg_completeness * 0.85;

  return (
    <div className="forensic-dashboard-grid mb-6 animate-in fade-in duration-500">
      <KPI 
        label="CATALOG_COMPLETENESS" 
        value={`${data.avg_completeness.toFixed(1)}%`}
        subValue="+1.2%"
        variant="default"
        isLoading={isLoading}
      />
      <KPI 
        label="MISSING_CRITICAL" 
        value={`${missingCritical.toFixed(1)}%`}
        subValue="ACTION_REQUIRED"
        variant={missingCritical > 20 ? 'error' : 'warning'}
        isLoading={isLoading}
      />
      <KPI 
        label="PRODUCTION_READY" 
        value={data.healthy_skus.toLocaleString()}
        subValue="VERIFIED"
        variant="success"
        isLoading={isLoading}
      />
      <KPI 
        label="SEO_READINESS_SCORE" 
        value={`${seoReadiness.toFixed(1)}%`}
        variant="default"
        isLoading={isLoading}
      />
    </div>
  );
};
