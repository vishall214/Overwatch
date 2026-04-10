import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Camera, ChevronDown, SearchCheck, ShieldAlert, Sparkles } from "lucide-react";

const capabilities = [
  {
    icon: ShieldAlert,
    title: "Detection",
    description: "Continuously identifies suspicious behavior and zone violations as they happen.",
  },
  {
    icon: Sparkles,
    title: "Intelligence",
    description: "Converts alert streams into clear risk context and operator-ready insights.",
  },
  {
    icon: SearchCheck,
    title: "Investigation",
    description: "Links related events, timelines, and evidence for fast decision making.",
  },
];

const flow = ["Camera", "Detection", "Alerts", "Investigation"];

export default function Landing() {
  const capabilitiesRef = useRef<HTMLElement | null>(null);
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const revealTargets = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
          }
        });
      },
      { threshold: 0.18 }
    );

    revealTargets.forEach((target) => observer.observe(target));

    return () => observer.disconnect();
  }, []);

  const scrollToCapabilities = () => {
    capabilitiesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden app-shell-bg page-transition">
      <div
        className="pointer-events-none absolute inset-0 hero-gradient opacity-80"
        style={{ transform: `translateY(${scrollY * 0.08}px)` }}
      />
      <div
        className="pointer-events-none absolute -top-24 left-1/3 h-[30rem] w-[30rem] rounded-full bg-accent/20 blur-[140px]"
        style={{ transform: `translateY(${scrollY * 0.14}px)` }}
      />
      <div
        className="pointer-events-none absolute bottom-10 right-1/4 h-[24rem] w-[24rem] rounded-full bg-accentCyan/20 blur-[120px]"
        style={{ transform: `translateY(${scrollY * 0.1}px)` }}
      />

      <header className="relative z-10 mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5 md:px-8">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl glass-card">
            <Camera className="h-5 w-5 text-accent" />
          </span>
          <span className="text-lg font-semibold tracking-[0.2em] text-textPrimary">OVERWATCH</span>
        </Link>

        <Link to="/login" className="btn-secondary !px-4 !py-2">
          Sign In
        </Link>
      </header>

      <section className="relative z-10 flex min-h-[calc(100vh-72px)] items-center justify-center px-6 pb-14 pt-8 md:px-8">
        <div className="max-w-4xl text-center">
          <div data-reveal className="reveal-block inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-1.5 text-xs uppercase tracking-[0.18em] text-accentCyan">
            <Sparkles className="h-3.5 w-3.5" />
            AI Surveillance Platform
          </div>

          <h1 data-reveal className="reveal-block mt-6 text-4xl font-extrabold leading-tight text-textPrimary sm:text-5xl md:text-6xl">
            Real-Time AI Surveillance Intelligence
          </h1>

          <p data-reveal className="reveal-block mx-auto mt-5 max-w-2xl text-base text-textSecondary md:text-lg">
            Detect, analyze, and respond to threats in real time.
          </p>

          <div data-reveal className="reveal-block mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to="/monitor" className="btn-primary min-w-[176px]">
              Enter System
              <ArrowRight className="h-4 w-4" />
            </Link>
            <button type="button" onClick={scrollToCapabilities} className="btn-secondary min-w-[176px]">
              View Demo
            </button>
          </div>

          <button
            type="button"
            onClick={scrollToCapabilities}
            className="mt-12 inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-textMuted transition-all duration-300 ease-out hover:text-textPrimary"
          >
            Scroll to explore
            <ChevronDown className="h-4 w-4" />
          </button>
        </div>
      </section>

      <section ref={capabilitiesRef} className="relative z-10 mx-auto w-full max-w-6xl px-6 py-20 md:px-8" data-reveal>
        <div className="reveal-block is-visible text-center">
          <p className="text-xs uppercase tracking-[0.18em] text-accentCyan">Capabilities</p>
          <h2 className="mt-2 text-3xl font-bold text-textPrimary">Built for fast operational clarity</h2>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {capabilities.map((item, index) => (
            <article
              key={item.title}
              data-reveal
              className="reveal-block glass-card p-5 transition-all duration-300 ease-out hover:scale-[1.02]"
              style={{ transitionDelay: `${index * 90}ms` }}
            >
              <span className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-accent/20 text-accentCyan">
                <item.icon className="h-5 w-5" />
              </span>
              <h3 className="text-lg font-semibold text-textPrimary">{item.title}</h3>
              <p className="mt-2 text-sm text-textSecondary">{item.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto w-full max-w-6xl px-6 py-20 md:px-8" data-reveal>
        <div className="reveal-block text-center">
          <p className="text-xs uppercase tracking-[0.18em] text-accentCyan">System Flow</p>
          <h2 className="mt-2 text-3xl font-bold text-textPrimary">Camera to investigation in one connected path</h2>
        </div>

        <div className="mt-10 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
          {flow.map((step, index) => (
            <div key={step} className="contents">
              <div
                data-reveal
                className="reveal-block glass-card p-4 text-center transition-all duration-300 ease-out hover:scale-[1.02]"
                style={{ transitionDelay: `${index * 90}ms` }}
              >
                <p className="text-sm font-semibold text-textPrimary">{step}</p>
              </div>
              {index < flow.length - 1 ? (
                <div className="hidden items-center justify-center text-accentCyan md:flex">
                  <ArrowRight className="h-4 w-4" />
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      <section className="relative z-10 mx-auto flex w-full max-w-4xl justify-center px-6 py-24 md:px-8" data-reveal>
        <div className="reveal-block glass-card w-full p-8 text-center">
          <h2 className="text-2xl font-bold text-textPrimary">Ready to secure your environment?</h2>
          <p className="mt-2 text-sm text-textSecondary">Start monitoring with a single, unified operator workflow.</p>
          <Link to="/monitor" className="btn-primary mt-7">
            Start Monitoring
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
