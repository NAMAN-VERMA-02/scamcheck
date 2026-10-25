import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "ScamCheck Research Workbench",
  description:
    "Evidence-first English/Hinglish scam analysis with a reproducible benchmark lab and seeded robustness testing.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <header className="topbar">
          <div className="topbar-inner">
            <span className="brand" aria-label="ScamCheck Research Workbench">
              <span className="brand-mark" aria-hidden="true">
                ◆
              </span>
              ScamCheck <span className="brand-sub">Research Workbench</span>
            </span>
            <Nav />
          </div>
        </header>
        <main id="main" className="shell">
          {children}
        </main>
        <footer className="footer">
          <p>
            Research prototype. Verdicts are evidence summaries, not guarantees. Messages you analyse are not stored.
            All examples and benchmark data are synthetic.
          </p>
        </footer>
      </body>
    </html>
  );
}
