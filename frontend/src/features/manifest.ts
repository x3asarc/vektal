export type RequiredState = "A" | "A+V" | "A+V+S";

export type WidgetContract = {
  id: string;
  requiredState: RequiredState;
  renderEntry: string;
  metadataHints?: string[];
};

export type FeatureManifest = {
  id: string;
  routePrefix: string;
  requiredState: RequiredState;
  renderEntry: string;
  widgets?: WidgetContract[];
};

export const FEATURE_MANIFEST: FeatureManifest[] = [
  {
    id: "onboarding",
    routePrefix: "/onboarding",
    requiredState: "A+V",
    renderEntry: "@/features/onboarding/components/OnboardingWizard",
  },
  {
    id: "jobs",
    routePrefix: "/jobs",
    requiredState: "A+V+S",
    renderEntry: "@/features/jobs/components/GlobalJobTracker",
    widgets: [
      {
        id: "jobs-health-summary",
        requiredState: "A+V+S",
        renderEntry: "@/features/jobs/components/GlobalJobTracker",
        metadataHints: ["status", "recovery-actions"],
      },
    ],
  },
  {
    id: "chat",
    routePrefix: "/chat",
    requiredState: "A+V+S",
    renderEntry: "@/shell/components/ChatSurface",
  },
];
