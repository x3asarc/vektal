import { ApprovalQueue } from '../components/ApprovalQueue';

export default function ApprovalsPage() {
  return (
    <main className="page-wrap">
      <header className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded title-icon">approval_delegation</span>
          Autonomous Approval Queue
        </h1>
        <p className="page-subtitle">Review high-impact autonomous changes before commit.</p>
      </header>
      <section className="page-body">
        <ApprovalQueue />
      </section>
    </main>
  );
}
