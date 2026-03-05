import { OnboardingWizard } from "@/features/onboarding/components/OnboardingWizard";

export default function OnboardingPage() {
  return (
    <div className="page-wrap">
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded title-icon">settings_suggest</span>
          Onboarding
        </h1>
        <p className="page-subtitle">Connect your store and configure your supplier integrations.</p>
      </div>
      <div className="page-body page-body--narrow">
        <OnboardingWizard />
      </div>
    </div>
  );
}
