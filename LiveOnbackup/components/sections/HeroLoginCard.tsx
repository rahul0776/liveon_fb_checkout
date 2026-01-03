import { Button } from "@/components/ui/Button";
import { Lock } from "lucide-react";

export function HeroLoginCard() {
  return (
    <div
      id="login"
      className="relative w-full max-w-sm overflow-hidden rounded-3xl border border-white/15 bg-white/[0.08] p-6 text-white shadow-[0_30px_60px_-28px_rgba(10,16,28,0.9)]"
    >
      <div className="absolute inset-0 opacity-50">
        <div className="grid-glow" />
      </div>
      <div className="relative z-10 space-y-6">
        <div className="space-y-2 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.08] px-3 py-1 text-xs uppercase tracking-[0.32em] text-white/60">
            <Lock className="h-3.5 w-3.5" />
            Secure login
          </div>
          <h3 className="text-xl font-semibold">Link your Facebook</h3>
          <p className="text-sm text-white/70">
            Start a backup in seconds. We never store your password — authentication happens directly with Facebook.
          </p>
        </div>

        <form className="space-y-4">
          <div className="space-y-2 text-left">
            <label htmlFor="email" className="text-xs uppercase tracking-[0.28em] text-white/55">
              Email or phone
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              className="w-full rounded-lg border border-white/18 bg-white/[0.08] px-4 py-2.5 text-sm text-white/90 placeholder:text-white/40 focus:border-[#f6c35d] focus:outline-none focus:ring-2 focus:ring-[#f6c35d]/40"
            />
          </div>
          <div className="space-y-2 text-left">
            <label htmlFor="password" className="text-xs uppercase tracking-[0.28em] text-white/55">
              Facebook password
            </label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              className="w-full rounded-lg border border-white/18 bg-white/[0.08] px-4 py-2.5 text-sm text-white/90 placeholder:text-white/40 focus:border-[#f6c35d] focus:outline-none focus:ring-2 focus:ring-[#f6c35d]/40"
            />
          </div>

          <Button type="submit" className="w-full justify-center shadow-ring">
            Link Facebook securely
          </Button>
        </form>

        <p className="text-center text-xs text-white/50">
          By continuing you agree to our privacy promise. We use encrypted OAuth tokens and never store your credentials.
        </p>
      </div>
    </div>
  );
}








