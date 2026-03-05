import { notFound } from "next/navigation";
import { FrontendTestConsole } from "@/features/test/FrontendTestConsole";

export default function TestPage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  return (
    <main className="page-wrap">
      <header className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded title-icon">lab_profile</span>
          Frontend Test Console
        </h1>
        <p className="page-subtitle">Diagnostic endpoint for live localhost validation.</p>
      </header>
      <section className="page-body">
        <FrontendTestConsole />
      </section>
    </main>
  );
}
