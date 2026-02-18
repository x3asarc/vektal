import { RuleSuggestionsInbox } from "@/features/settings/components/RuleSuggestionsInbox";
import { StrategyQuiz } from "@/features/settings/components/StrategyQuiz";

export default function SettingsPage() {
  return (
    <div className="page-wrap settings-page">
      <div className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded" style={{ marginRight: 8 }}>settings</span>
          Settings
        </h1>
        <p className="page-subtitle">Strategy configuration and rule management.</p>
      </div>
      <div className="page-body" style={{ maxWidth: 720 }}>
        <StrategyQuiz />
        <RuleSuggestionsInbox />
      </div>
    </div>
  );
}
