import React, { useEffect, useState } from 'react';
import { DashboardSummary } from './DashboardSummary';
import { FieldCoverageMatrix } from './FieldCoverageMatrix';
import { ChatWorkspace } from '../../chat/components/ChatWorkspace';
import { Button } from '../../../components/ui/Button';
import { Panel } from '../../../components/ui/Panel';
import { OperationalErrorCard } from "@/components/OperationalErrorCard";
import { apiRequest, ApiClientError } from "@/lib/api/client";
import { stableDiagnosticId } from "@/lib/diagnostics";
import type { NormalizedApiError } from "@/shared/contracts";

interface DashboardData {
  total_skus: number;
  avg_completeness: number;
  healthy_skus: number;
  unhealthy_skus: number;
  last_ingest_at: string | null;
  field_coverage: Record<string, number>;
  store_domain: string;
}

const ACTIVITY_LOG = [
  { time: '10:41:02', source: 'SHOPIFY', event: 'SKU-12033 TITLE_MUTATION', status: 'PERSISTED' },
  { time: '10:35:19', source: 'VEKTAL', event: 'ENRICH_RUN #882_APPLY', status: 'VERIFIED' },
  { time: '10:22:44', source: 'SHOPIFY', event: 'SKU-09002 PRICE_DELTA', status: 'PERSISTED' },
];

export const CommandCenter: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isUnauthorized, setIsUnauthorized] = useState(false);
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [storeRequired, setStoreRequired] = useState(false);
  const [error, setError] = useState<NormalizedApiError | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        setIsUnauthorized(false);
        setStoreRequired(false);
        setError(null);
        const result = await apiRequest<DashboardData>('/api/v1/ops/dashboard/summary');
        setData(result);
      } catch (err: unknown) {
        if (err instanceof ApiClientError) {
          if (err.normalized.status === 401) {
            setIsUnauthorized(true);
            return;
          }
          if (err.normalized.status === 409) {
            setStoreRequired(true);
            return;
          }
          setError(err.normalized);
          return;
        }
        const detail = err instanceof Error ? err.message : "Dashboard request failed.";
        setError({
          type: "urn:frontend:dashboard-error",
          title: "Dashboard request failed",
          status: 0,
          detail,
          fieldErrors: {},
          scope: "global",
          severity: "degrading",
          canRetry: true,
        });
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, []);

  if (isUnauthorized) {
    return (
      <div className="page-wrap h-full flex items-center justify-center bg-[var(--surface-void)]">
        <Panel className="max-w-md w-full p-8 text-center border-red-900/40">
          <div className="w-12 h-12 border border-red-500/50 flex items-center justify-center mx-auto mb-6">
            <span className="material-symbols-rounded text-red-500 filled-icon">lock</span>
          </div>
          <h2 className="page-title !text-sm mb-4">SESSION_AUTH_REQUIRED</h2>
          <p className="page-subtitle !text-[10px] mb-8 leading-relaxed">
            Operational session expired or credentials missing. Re-authentication required for terminal access.
          </p>
          <Button 
            onClick={() => window.location.href = '/auth/login'}
            className="w-full"
            variant="primary"
          >
            AUTHENTICATE_SESSION
          </Button>
        </Panel>
      </div>
    );
  }

  if (storeRequired) {
    return (
      <div className="page-wrap h-full flex items-center justify-center bg-[var(--surface-void)]">
        <Panel className="max-w-md w-full p-8 text-center border-amber-400/40">
          <div className="w-12 h-12 border border-amber-400/50 flex items-center justify-center mx-auto mb-6">
            <span className="material-symbols-rounded text-amber-300 filled-icon">storefront</span>
          </div>
          <h2 className="page-title !text-sm mb-4">STORE_CONNECTION_REQUIRED</h2>
          <p className="page-subtitle !text-[10px] mb-8 leading-relaxed">
            Connect a Shopify store to unlock dashboard telemetry and ingest metrics.
          </p>
          <Button
            onClick={() => window.location.href = '/onboarding'}
            className="w-full"
            variant="primary"
          >
            OPEN_ONBOARDING
          </Button>
        </Panel>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-wrap h-full flex items-center justify-center bg-[var(--surface-void)]">
        <OperationalErrorCard
          title={error.title}
          detail={error.detail}
          diagnosticId={stableDiagnosticId(error.detail)}
          retryLabel="Retry dashboard"
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  return (
    <div className="page-wrap h-full overflow-hidden flex flex-col bg-transparent">
      <header className="page-header flex justify-between items-start">
        <div className="flex flex-col gap-1">
          <h1 className="page-title flex items-center gap-3">
            <span className="material-symbols-rounded text-[var(--brand-primary)]">space_dashboard</span>
            Dashboard
            <span className="text-[9px] font-mono text-[var(--brand-primary)] bg-[var(--brand-primary-dim)] px-2 py-0.5 border border-[var(--brand-primary)]/30 tracking-[0.2em] ml-2">ACTIVE_CONSOLE</span>
          </h1>
          <p className="page-subtitle">
            Operational Command Center // System Identity: {data?.store_domain || 'BASTELSCHACHTEL.AT'}
          </p>
        </div>
        
        <div className="flex flex-col items-end gap-3">
          <div className="flex gap-3">
            <Button variant="ghost" size="sm">RECONCILE_STATE</Button>
            <Button 
              variant={terminalOpen ? "secondary" : "primary"} 
              size="sm"
              onClick={() => setTerminalOpen(!terminalOpen)}
            >
              {terminalOpen ? "CLOSE_TERMINAL" : "OPEN_TERMINAL"}
            </Button>
          </div>
          <div className="flex gap-4 items-center">
            <div className="flex items-center gap-2">
              <div className="w-1 h-1 rounded-full bg-green-400 shadow-[0_0_5px_#4ade80]"></div>
              <span className="text-[9px] font-mono text-[var(--text-dim)] uppercase tracking-wider">Node: PRD-CLUSTER-01</span>
            </div>
            <div className="flex items-center gap-2 text-[var(--brand-primary)] opacity-60">
              <span className="material-symbols-rounded text-[14px]">cloud_sync</span>
              <span className="text-[9px] font-mono uppercase tracking-widest">Sync: {data?.last_ingest_at || '10:42:11'}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="page-body">
        {/* State 1: Dashboard Base Info */}
        <DashboardSummary data={data || {
          total_skus: 0,
          avg_completeness: 0,
          healthy_skus: 0,
          unhealthy_skus: 0,
          last_ingest_at: null,
          store_domain: ''
        }} isLoading={loading} />

        {/* State 2: Conditional Terminal View */}
        {terminalOpen ? (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="lg:col-span-4 flex flex-col gap-6">
              <FieldCoverageMatrix 
                coverage={data?.field_coverage || {}} 
                totalSkus={data?.total_skus || 0} 
                isLoading={loading} 
              />
              
              <Panel title="AUTOMATED_INSIGHTS">
                <p className="text-[10px] font-mono text-[var(--text-body)] mb-6 leading-relaxed">
                  {data && data.unhealthy_skus > 0 
                    ? `ANOMALY_DETECTED: ${data.unhealthy_skus} UNITS WITH CRITICAL ATTRIBUTE GAPS. RECOMMENDATION: INITIATE SEO_METADATA_SYNTHESIS.`
                    : "STATUS: NOMINAL. CATALOG ATTRIBUTE PERSISTENCE VERIFIED ACROSS ALL TRACKED DOMAINS."}
                </p>
                <Button className="w-full" variant="ghost">
                  EXECUTE_REMEDIATION_RUN
                </Button>
              </Panel>
            </div>

            <div className="lg:col-span-8 flex flex-col gap-6">
              <Panel title="OPERATIONAL_CONTROL_DOCK" className="flex flex-col h-[520px] p-0 overflow-hidden">
                <div className="flex-1 overflow-hidden relative">
                  {/* We force the ChatWorkspace into a docked mode by overriding its internal fixed heights if needed, 
                      but since we use overflow-hidden and flex-1 here, it should adapt. */}
                  <ChatWorkspace />
                </div>
              </Panel>

              <Panel title="RECONCILIATION_LOG" className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[var(--surface-border)] bg-white/2">
                        <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">TIMESTAMP</th>
                        <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">SOURCE</th>
                        <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">EVENT_TYPE</th>
                        <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">STATUS</th>
                        <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">ACTION</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--surface-border)]">
                      {ACTIVITY_LOG.map((item, i) => (
                        <tr key={i} className="hover:bg-white/2 transition-colors">
                          <td className="px-4 py-3 font-mono text-[9px] text-[var(--text-dim)]">{item.time}</td>
                          <td className="px-4 py-3">
                            <span className={`px-1.5 py-0.5 border text-[8px] font-bold ${
                              item.source === 'SHOPIFY' ? 'border-purple-900/50 text-purple-400' : 'border-blue-900/50 text-blue-400'
                            }`}>
                              {item.source}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-[9px] text-[var(--text-heading)]">{item.event}</td>
                          <td className="px-4 py-3 font-mono text-[8px] text-[var(--text-dim)] font-bold">{item.status}</td>
                          <td className="px-4 py-3">
                            <button className="text-[9px] font-bold text-[var(--brand-primary)] hover:underline uppercase tracking-widest transition-colors font-mono">INSPECT</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="p-4 flex gap-6 border-t border-[var(--surface-border)]">
                  <button className="text-[9px] font-bold text-[var(--text-heading)] uppercase tracking-widest border-b border-[var(--text-heading)] pb-0.5 hover:opacity-70 transition-opacity font-mono">VIEW_TIMELINE</button>
                  <button className="text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest hover:text-[var(--text-heading)] transition-colors font-mono">ROLLBACK_REGISTRY</button>
                </div>
              </Panel>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            <Panel title="AUTOMATED_INSIGHTS">
              <p className="text-[10px] font-mono text-[var(--text-body)] mb-6 leading-relaxed">
                {data && data.unhealthy_skus > 0 
                  ? `ANOMALY_DETECTED: ${data.unhealthy_skus} UNITS WITH CRITICAL ATTRIBUTE GAPS. RECOMMENDATION: INITIATE SEO_METADATA_SYNTHESIS.`
                  : "STATUS: NOMINAL. CATALOG ATTRIBUTE PERSISTENCE VERIFIED ACROSS ALL TRACKED DOMAINS."}
              </p>
              <Button variant="ghost" className="w-fit">
                EXECUTE_REMEDIATION_RUN
              </Button>
            </Panel>

            <Panel title="RECONCILIATION_LOG" className="p-0">
               <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--surface-border)] bg-white/2">
                      <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">TIMESTAMP</th>
                      <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">SOURCE</th>
                      <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">EVENT_TYPE</th>
                      <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">STATUS</th>
                      <th className="px-4 py-3 text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest font-mono">ACTION</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--surface-border)]">
                    {ACTIVITY_LOG.map((item, i) => (
                      <tr key={i} className="hover:bg-white/2 transition-colors">
                        <td className="px-4 py-3 font-mono text-[9px] text-[var(--text-dim)]">{item.time}</td>
                        <td className="px-4 py-3">
                          <span className={`px-1.5 py-0.5 border text-[8px] font-bold ${
                            item.source === 'SHOPIFY' ? 'border-purple-900/50 text-purple-400' : 'border-blue-900/50 text-blue-400'
                          }`}>
                            {item.source}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-[9px] text-[var(--text-heading)]">{item.event}</td>
                        <td className="px-4 py-3 font-mono text-[8px] text-[var(--text-dim)] font-bold">{item.status}</td>
                        <td className="px-4 py-3">
                          <button className="text-[9px] font-bold text-[var(--brand-primary)] hover:underline uppercase tracking-widest transition-colors font-mono">INSPECT</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="p-4 flex gap-6 border-t border-[var(--surface-border)]">
                <button className="text-[9px] font-bold text-[var(--text-heading)] uppercase tracking-widest border-b border-[var(--text-heading)] pb-0.5 hover:opacity-70 transition-opacity font-mono">VIEW_TIMELINE</button>
                <button className="text-[9px] font-bold text-[var(--text-dim)] uppercase tracking-widest hover:text-[var(--text-heading)] transition-colors font-mono">ROLLBACK_REGISTRY</button>
              </div>
            </Panel>
          </div>
        )}

        <Panel title="OPERATIONAL_LAUNCHPAD" className="p-0">
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y divide-[var(--surface-border)] border-collapse">
            {[
              'RUN_SEARCH_SWEEP', 
              'START_ENRICH_DRY_RUN', 
              'FIX_CRITICAL_GAPS', 
              'JOBS_TELEMETRY'
            ].map(label => (
              <button 
                key={label}
                className="px-4 py-8 bg-transparent text-[var(--text-dim)] text-[9px] font-bold uppercase tracking-[0.2em] hover:bg-white/5 hover:text-[var(--text-heading)] transition-all text-center font-mono"
              >
                {label}
              </button>
            ))}
          </div>
        </Panel>
      </main>
    </div>
  );
};
