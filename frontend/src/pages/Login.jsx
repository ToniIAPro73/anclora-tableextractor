import React from "react";
import { Table2, ScanText, CalendarClock, ShieldCheck, ArrowRight } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LangToggle } from "@/components/LangToggle";
import { useLang } from "@/contexts/LangContext";

export default function Login() {
  const { t } = useLang();

  const handleLogin = () => {
    const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
    window.location.href = `${backendUrl}/api/auth/google/start?redirect=%2Fupload`;
  };

  const features = [
    { icon: ScanText, text: t("auth.feature1") },
    { icon: CalendarClock, text: t("auth.feature2") },
    { icon: ShieldCheck, text: t("auth.feature3") },
  ];

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="absolute right-5 top-5 z-20 flex items-center gap-2.5">
        <LangToggle />
        <ThemeToggle />
      </div>

      {/* glow accents */}
      <div className="pointer-events-none absolute -left-40 -top-40 h-96 w-96 rounded-full bg-primary/20 blur-[120px]" />
      <div className="pointer-events-none absolute -bottom-40 -right-20 h-96 w-96 rounded-full bg-primary/10 blur-[120px]" />

      <div className="relative z-10 mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-6 py-16 lg:grid-cols-2">
        {/* Left: brand + pitch */}
        <div className="fade-up">
          <div className="mb-8 flex items-center gap-3">
            <span className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/30">
              <Table2 className="h-6 w-6 text-primary" strokeWidth={1.8} />
              <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-primary shadow-[0_0_10px_rgba(56,189,248,0.9)]" />
            </span>
            <span className="text-xl font-bold tracking-tight" style={{ fontFamily: "Manrope, sans-serif" }}>
              Anclora <span className="text-primary">TableExtract</span>
            </span>
          </div>

          <h1 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl" style={{ fontFamily: "Manrope, sans-serif" }}>
            {t("auth.title")}
          </h1>
          <p className="mt-5 max-w-md text-base leading-relaxed text-muted-foreground">
            {t("auth.subtitle")}
          </p>

          <ul className="mt-8 space-y-3">
            {features.map((f, i) => {
              const Icon = f.icon;
              return (
                <li key={i} className="flex items-center gap-3 text-sm">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" strokeWidth={1.8} />
                  </span>
                  <span className="text-foreground/90">{f.text}</span>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Right: auth card */}
        <div className="fade-up flex justify-center lg:justify-end" style={{ animationDelay: "80ms" }}>
          <div className="w-full max-w-sm rounded-3xl border border-border bg-card p-8 shadow-2xl shadow-primary/5">
            <h2 className="text-xl font-semibold tracking-tight">{t("common.appName")}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{t("common.tagline")}</p>

            <button
              data-testid="google-login-button"
              onClick={handleLogin}
              className="group mt-8 flex w-full items-center justify-center gap-3 rounded-xl bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition hover:opacity-95 active:scale-[0.98]"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path fill="#FFC107" d="M43.6 20.5h-1.9V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 4.1 29.3 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22 22-9.8 22-22c0-1.5-.2-2.6-.4-3.5z" />
                <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 4.1 29.3 2 24 2 15.5 2 8.2 6.8 6.3 14.7z" />
                <path fill="#4CAF50" d="M24 46c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 37.4 26.7 38 24 38c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C8.1 41.1 15.4 46 24 46z" />
                <path fill="#1976D2" d="M43.6 20.5H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.5l6.2 5.2C41.4 36 44 30.5 44 24c0-1.5-.2-2.6-.4-3.5z" />
              </svg>
              {t("auth.signIn")}
              <ArrowRight className="h-4 w-4 opacity-0 transition group-hover:translate-x-1 group-hover:opacity-100" />
            </button>

            <p className="mt-6 text-center text-xs leading-relaxed text-muted-foreground">
              {t("auth.terms")}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
