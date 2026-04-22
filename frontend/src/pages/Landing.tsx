import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import {
  ArrowRight,
  Camera,
  ShieldAlert,
  Sparkles,
  SearchCheck,
  Eye,
  AlertTriangle,
  BrainCircuit,
  Radio,
  MonitorPlay,
  Bell,
  BarChart3,
} from "lucide-react";

gsap.registerPlugin(ScrollTrigger);

/* ─── Data ─── */

const problems = [
  {
    icon: Eye,
    title: "Manual Monitoring",
    desc: "Operators can't watch every feed — threats slip through blind spots.",
  },
  {
    icon: AlertTriangle,
    title: "Missed Threats",
    desc: "Delayed response means incidents escalate before anyone reacts.",
  },
  {
    icon: BrainCircuit,
    title: "No Real Intelligence",
    desc: "Raw footage lacks context — no risk scoring, no correlation.",
  },
];

const solutions = [
  {
    icon: ShieldAlert,
    title: "Detection",
    desc: "Identifies suspicious behavior and zone violations as they happen.",
  },
  {
    icon: Sparkles,
    title: "Intelligence",
    desc: "Converts alert streams into clear risk context and operator-ready insights.",
  },
  {
    icon: SearchCheck,
    title: "Investigation",
    desc: "Links related events, timelines, and evidence for fast decision making.",
  },
];

const flowSteps = [
  { icon: Camera, label: "Camera" },
  { icon: ShieldAlert, label: "Detection" },
  { icon: Bell, label: "Alerts" },
  { icon: SearchCheck, label: "Investigation" },
];

const techStack = [
  { name: "React", color: "#61dafb" },
  { name: "FastAPI", color: "#009688" },
  { name: "YOLO", color: "#ff6f00" },
  { name: "PostgreSQL", color: "#336791" },
];

const previews = [
  {
    title: "Monitor",
    icon: MonitorPlay,
    rows: [
      { label: "Camera Feed", w: "100%" },
      { label: "Zone Overlay", w: "60%" },
    ],
  },
  {
    title: "Alerts",
    icon: Bell,
    rows: [
      { label: "Critical — Intrusion Zone A", w: "90%" },
      { label: "High — Loitering Detected", w: "75%" },
      { label: "Medium — Crowd Threshold", w: "55%" },
    ],
  },
  {
    title: "Analytics",
    icon: BarChart3,
    rows: [
      { label: "Threats over time", w: "85%" },
      { label: "Zone heatmap", w: "70%" },
    ],
  },
];

/* ─── Component ─── */

export default function Landing() {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      /* ── Hero stagger ── */
      const heroTl = gsap.timeline({ defaults: { ease: "power3.out" } });
      heroTl
        .fromTo("[data-hero-badge]", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5 })
        .fromTo("[data-hero-title]", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.6 }, "-=0.25")
        .fromTo("[data-hero-sub]", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5 }, "-=0.25")
        .fromTo("[data-hero-cta]", { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.45 }, "-=0.2");

      /* ── Hero parallax blobs ── */
      gsap.to("[data-blob-1]", {
        yPercent: 25,
        ease: "none",
        scrollTrigger: { trigger: "[data-hero]", start: "top top", end: "bottom top", scrub: true },
      });
      gsap.to("[data-blob-2]", {
        yPercent: 18,
        ease: "none",
        scrollTrigger: { trigger: "[data-hero]", start: "top top", end: "bottom top", scrub: true },
      });

      /* ── Section reveals ── */
      gsap.utils.toArray<HTMLElement>("[data-section]").forEach((section) => {
        const reveals = section.querySelectorAll("[data-reveal]");
        gsap.set(reveals, { opacity: 0, y: 28 });
        ScrollTrigger.create({
          trigger: section,
          start: "top 88%",
          once: true,
          onEnter: () => {
            gsap.to(reveals, {
              opacity: 1,
              y: 0,
              duration: 0.6,
              stagger: 0.1,
              ease: "power2.out",
            });
          },
        });
      });

      /* ── Card staggers ── */
      gsap.utils.toArray<HTMLElement>("[data-stagger-group]").forEach((group) => {
        const children = Array.from(group.children) as HTMLElement[];
        gsap.set(children, { opacity: 0, y: 24 });
        ScrollTrigger.create({
          trigger: group,
          start: "top 90%",
          once: true,
          onEnter: () => {
            gsap.to(children, {
              opacity: 1,
              y: 0,
              duration: 0.5,
              stagger: 0.12,
              ease: "power2.out",
            });
          },
        });
      });

      /* ── System Flow scrub animation ── */
      const flowSection = document.querySelector("[data-flow-section]");
      if (flowSection) {
        const steps = flowSection.querySelectorAll("[data-flow-step]");
        const connectors = flowSection.querySelectorAll("[data-flow-line]");

        const flowTl = gsap.timeline({
          scrollTrigger: {
            trigger: flowSection,
            start: "top 65%",
            end: "bottom 35%",
            scrub: 1,
          },
        });

        steps.forEach((step, i) => {
          flowTl.to(step, {
            borderColor: "rgba(20, 184, 166, 0.5)",
            boxShadow: "0 0 30px rgba(20, 184, 166, 0.2), 0 0 60px rgba(20, 184, 166, 0.08)",
            duration: 0.25,
          });
          if (i < connectors.length) {
            flowTl.to(
              connectors[i],
              {
                scaleX: 1,
                opacity: 1,
                duration: 0.2,
              },
              "-=0.1"
            );
          }
        });
      }

      /* Ensure ScrollTrigger recalculates after layout settles */
      requestAnimationFrame(() => ScrollTrigger.refresh());
    }, rootRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={rootRef} className="relative min-h-screen overflow-x-hidden app-shell-bg">
      {/* ── Background blobs ── */}
      <div
        data-blob-1
        className="pointer-events-none fixed -top-24 left-1/3 h-[30rem] w-[30rem] rounded-full bg-accent/20 blur-[140px]"
      />
      <div
        data-blob-2
        className="pointer-events-none fixed bottom-10 right-1/4 h-[24rem] w-[24rem] rounded-full bg-accentCyan/20 blur-[120px]"
      />
      <div className="pointer-events-none fixed inset-0 hero-gradient opacity-60" />

      {/* ═══════════════════ HEADER ═══════════════════ */}
      <header className="relative z-20 mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5 md:px-8">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl glass-card">
            <Camera className="h-5 w-5 text-accent" />
          </span>
          <span className="text-lg font-semibold tracking-[0.2em] text-textPrimary">OVERWATCH</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link to="/login" className="btn-secondary !px-4 !py-2">
            Sign In
          </Link>
          <Link to="/signup" className="btn-primary !px-4 !py-2">
            Sign Up
          </Link>
        </div>
      </header>

      {/* ═══════════════════ 1. HERO ═══════════════════ */}
      <section
        data-hero
        className="relative z-10 flex min-h-[calc(100vh-72px)] items-center justify-center px-6 pb-14 pt-8 md:px-8"
      >
        <div className="max-w-4xl text-center">
          <div
            data-hero-badge
            className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-1.5 text-xs uppercase tracking-[0.18em] text-accentCyan"
          >
            <Radio className="h-3.5 w-3.5" />
            AI Surveillance Platform
          </div>

          <h1
            data-hero-title
            className="mt-6 text-4xl font-extrabold leading-tight text-textPrimary sm:text-5xl md:text-6xl"
          >
            Real-Time AI
            <br />
            <span className="bg-gradient-to-r from-accent to-accentCyan bg-clip-text text-transparent">
              Surveillance Intelligence
            </span>
          </h1>

          <p data-hero-sub className="mx-auto mt-5 max-w-2xl text-base text-textSecondary md:text-lg">
            Detect, analyze, and respond to threats in real time.
          </p>

          <div data-hero-cta className="mt-9 flex items-center justify-center">
            <Link to="/dashboard" className="btn-primary min-w-[200px]">
              Open Dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════════════ 2. WHAT IS OVERWATCH ═══════════════════ */}
      <section data-section className="landing-section">
        <div className="grid items-center gap-10 md:grid-cols-2">
          <div>
            <p data-reveal className="landing-section-label">
              What is OVERWATCH
            </p>
            <h2 data-reveal className="landing-section-title">
              One system for detection,
              <br />
              intelligence, and response
            </h2>
            <p data-reveal className="mt-4 max-w-md text-sm leading-relaxed text-textSecondary">
              OVERWATCH connects live camera feeds to AI-powered detection, generates real-time
              alerts, and gives operators the investigative tools to act — all in a single unified
              interface.
            </p>
          </div>

          {/* Mini UI preview */}
          <div data-reveal className="preview-mock">
            <div className="preview-mock-bar">
              <span className="preview-mock-dot bg-red-500/70" />
              <span className="preview-mock-dot bg-yellow-500/70" />
              <span className="preview-mock-dot bg-green-500/70" />
              <span className="ml-2 text-[10px] text-textMuted">overwatch — monitor</span>
            </div>
            <div className="p-4 space-y-3">
              <div className="flex gap-3">
                <div className="h-24 flex-1 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
                  <Camera className="h-6 w-6 text-accent/50" />
                </div>
                <div className="w-28 space-y-2">
                  <div className="h-5 rounded bg-accent/10 border border-accent/20" />
                  <div className="h-5 rounded bg-white/[0.04] border border-white/[0.06]" />
                  <div className="h-5 rounded bg-white/[0.04] border border-white/[0.06]" />
                </div>
              </div>
              <div className="flex gap-2">
                <div className="h-3 flex-1 rounded-full bg-accent/20" />
                <div className="h-3 w-16 rounded-full bg-accentCyan/15" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════ 3. PROBLEM / GAP ═══════════════════ */}
      <section data-section className="landing-section">
        <div className="text-center">
          <p data-reveal className="landing-section-label">
            The Problem
          </p>
          <h2 data-reveal className="landing-section-title">
            Traditional surveillance is broken
          </h2>
        </div>

        <div data-stagger-group className="mt-10 grid gap-5 md:grid-cols-3">
          {problems.map((p) => (
            <article
              key={p.title}
              className="glass-card p-5 transition-all duration-300 hover:scale-[1.02]"
            >
              <span className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-red-500/15 text-red-400">
                <p.icon className="h-5 w-5" />
              </span>
              <h3 className="text-lg font-semibold text-textPrimary">{p.title}</h3>
              <p className="mt-2 text-sm text-textSecondary">{p.desc}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ═══════════════════ 4. HOW IT SOLVES ═══════════════════ */}
      <section data-section className="landing-section">
        <div className="text-center">
          <p data-reveal className="landing-section-label">
            The Solution
          </p>
          <h2 data-reveal className="landing-section-title">
            Detection → Intelligence → Investigation
          </h2>
        </div>

        <div data-stagger-group className="mt-10 grid gap-5 md:grid-cols-3">
          {solutions.map((s, i) => (
            <article
              key={s.title}
              className="glass-card p-5 transition-all duration-300 hover:scale-[1.02] relative group"
            >
              {/* connector arrow between cards (desktop only) */}
              {i < solutions.length - 1 && (
                <div className="hidden md:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 text-accent/50">
                  <ArrowRight className="h-4 w-4" />
                </div>
              )}
              <span className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-accent/20 text-accentCyan">
                <s.icon className="h-5 w-5" />
              </span>
              <h3 className="text-lg font-semibold text-textPrimary">{s.title}</h3>
              <p className="mt-2 text-sm text-textSecondary">{s.desc}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ═══════════════════ 5. SYSTEM FLOW (INTERACTIVE) ═══════════════════ */}
      <section data-section data-flow-section className="landing-section">
        <div className="text-center">
          <p data-reveal className="landing-section-label">
            System Flow
          </p>
          <h2 data-reveal className="landing-section-title">
            Camera to investigation in one connected path
          </h2>
        </div>

        <div className="mt-12 flex flex-col md:flex-row items-center justify-center gap-0 md:gap-0">
          {flowSteps.map((step, i) => (
            <div key={step.label} className="flex items-center">
              <div
                data-flow-step
                className="glass-card p-5 md:p-6 text-center min-w-[140px] transition-all duration-400"
              >
                <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-accent/15 text-accent">
                  <step.icon className="h-5 w-5" />
                </span>
                <p className="text-sm font-semibold text-textPrimary">{step.label}</p>
              </div>

              {/* Connector line */}
              {i < flowSteps.length - 1 && (
                <div
                  data-flow-line
                  className="hidden md:block w-12 h-[2px] bg-gradient-to-r from-accent/60 to-accentCyan/60 origin-left"
                  style={{ transform: "scaleX(0)", opacity: 0 }}
                />
              )}

              {/* Mobile vertical connector */}
              {i < flowSteps.length - 1 && (
                <div className="md:hidden flex flex-col items-center py-2">
                  <div className="w-[2px] h-6 bg-gradient-to-b from-accent/40 to-accentCyan/40" />
                  <ArrowRight className="h-3 w-3 text-accent/50 rotate-90" />
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════ 6. TECH STACK ═══════════════════ */}
      <section data-section className="landing-section">
        <div className="text-center">
          <p data-reveal className="landing-section-label">
            Built With
          </p>
          <h2 data-reveal className="landing-section-title">
            Production-grade technology stack
          </h2>
        </div>

        <div data-stagger-group className="mt-10 flex flex-wrap justify-center gap-4">
          {techStack.map((t) => (
            <div
              key={t.name}
              className="glass-card px-6 py-4 text-center min-w-[130px] transition-all duration-300 hover:scale-[1.03]"
            >
              <div
                className="mx-auto mb-2 h-3 w-3 rounded-full"
                style={{ background: t.color, boxShadow: `0 0 12px ${t.color}55` }}
              />
              <p className="text-sm font-semibold text-textPrimary">{t.name}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════ 7. SYSTEM PREVIEW ═══════════════════ */}
      <section data-section className="landing-section">
        <div className="text-center">
          <p data-reveal className="landing-section-label">
            System Preview
          </p>
          <h2 data-reveal className="landing-section-title">
            Built and operational
          </h2>
        </div>

        <div data-stagger-group className="mt-10 grid gap-5 md:grid-cols-3">
          {previews.map((preview) => (
            <div key={preview.title} className="preview-mock transition-all duration-300 hover:scale-[1.02]">
              <div className="preview-mock-bar">
                <span className="preview-mock-dot bg-red-500/70" />
                <span className="preview-mock-dot bg-yellow-500/70" />
                <span className="preview-mock-dot bg-green-500/70" />
                <span className="ml-2 text-[10px] text-textMuted">{preview.title.toLowerCase()}</span>
              </div>
              <div className="p-4 space-y-2.5">
                <div className="flex items-center gap-2 mb-3">
                  <preview.icon className="h-4 w-4 text-accent" />
                  <span className="text-xs font-semibold text-textPrimary">{preview.title}</span>
                </div>
                {preview.rows.map((row) => (
                  <div key={row.label} className="space-y-1">
                    <p className="text-[10px] text-textMuted">{row.label}</p>
                    <div
                      className="h-2 rounded-full bg-accent/15"
                      style={{ width: row.w }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════ 8. FINAL STATEMENT ═══════════════════ */}
      <section data-section className="landing-section pb-24">
        <div data-reveal className="text-center">
          <p className="text-2xl md:text-3xl font-bold text-textPrimary leading-snug">
            Designed for real-time
            <br />
            <span className="bg-gradient-to-r from-accent to-accentCyan bg-clip-text text-transparent">
              intelligent surveillance.
            </span>
          </p>
        </div>
      </section>
    </div>
  );
}
