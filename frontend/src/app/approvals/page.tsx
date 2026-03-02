import ApprovalsPage from '@/features/approvals/pages/ApprovalsPage';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Approval Queue | Shopify Multi-Supplier',
  description: 'Manage autonomous agent fixes and optimizations',
};

export default function Page() {
  return <ApprovalsPage />;
}
