import Link from "next/link";

export function SiteFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-white/10 bg-[#0f253d]/80">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-12 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-0">
        <div className="max-w-xl space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.32em] text-white/50">
            LiveOn
            <span className="inline-block h-1 w-1 rounded-full bg-[#f6c35d]" />
            Preserve
          </div>
          <h2 className="text-2xl font-semibold text-white sm:text-3xl">
            Ready to archive the stories you never want to lose?
          </h2>
          <p className="text-sm text-white/65 sm:text-base">
            Start a secure Facebook backup in minutes, revisit your memories in a timeline designed just for you, and download everything in one polished package.
          </p>
        </div>

        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <Link
            href="#help"
            className="inline-flex items-center justify-center rounded-lg border border-white/15 px-5 py-2.5 text-sm font-semibold text-white/85 transition hover:border-white/30 hover:text-white"
          >
            Visit Help Center
          </Link>
          <Link
            href="#login"
            className="inline-flex items-center justify-center rounded-lg bg-[#f6c35d] px-5 py-2.5 text-sm font-semibold text-[#0f253d] shadow-ring transition hover:brightness-110"
          >
            Start Backup
          </Link>
        </div>
      </div>

      <div className="border-t border-white/10 bg-black/20">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 text-xs text-white/50 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-0">
          <p className="tracking-wide">
            © {year} LiveOn · Crafted by MinedCo. All rights reserved.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link href="#faq" className="transition hover:text-white">
              FAQ
            </Link>
            <Link href="#contact" className="transition hover:text-white">
              Contact
            </Link>
            <Link href="mailto:hello@liveon.app" className="transition hover:text-white">
              hello@liveon.app
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
