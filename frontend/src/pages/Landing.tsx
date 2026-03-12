import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Eye, Shield, Brain, Cpu, Activity, ChevronRight, Radar, Lock } from "lucide-react";

gsap.registerPlugin(ScrollTrigger);

const features = [
  {
    icon: Shield,
    title: "Intrusion Detection",
    desc: "AI-powered zone breach detection with instant alerts and snapshot capture.",
    color: "from-ow-alert-intrusion to-red-600",
  },
  {
    icon: Eye,
    title: "Loitering Analysis",
    desc: "Behavioral analysis identifies individuals lingering in restricted areas.",
    color: "from-ow-alert-loitering to-orange-600",
  },
  {
    icon: Radar,
    title: "Crowd Monitoring",
    desc: "Real-time crowd density estimation with configurable thresholds.",
    color: "from-ow-alert-crowd to-blue-600",
  },
  {
    icon: Brain,
    title: "Deep Learning Pipeline",
    desc: "YOLOv8-based inference with multi-stage asynchronous processing.",
    color: "from-ow-teal to-ow-accent-dim",
  },
  {
    icon: Lock,
    title: "Face Recognition",
    desc: "Real-time face matching against registered identity database.",
    color: "from-ow-accent to-ow-accent-dim",
  },
  {
    icon: Activity,
    title: "Live Analytics",
    desc: "Real-time dashboards with alert statistics and pipeline metrics.",
    color: "from-ow-mist to-ow-teal",
  },
];

const techStack = [
  { name: "YOLOv8", detail: "Object Detection" },
  { name: "FastAPI", detail: "Backend Runtime" },
  { name: "DeepSORT", detail: "Multi-Object Tracking" },
  { name: "InsightFace", detail: "Face Recognition" },
  { name: "React", detail: "Dashboard UI" },
  { name: "SQLite", detail: "Alert Storage" },
];

export default function Landing() {
  const heroRef = useRef<HTMLDivElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);
  const techRef = useRef<HTMLDivElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Subtle particle field
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf: number;
    const particles: { x: number; y: number; vx: number; vy: number; r: number; a: number }[] = [];
    const COUNT = 50;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    for (let i = 0; i < COUNT; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        r: Math.random() * 1.5 + 0.5,
        a: Math.random() * 0.25 + 0.05,
      });
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(43,182,201,${p.a})`;
        ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  useEffect(() => {
    const ctx = gsap.context(() => {
      // Hero animation
      const heroTl = gsap.timeline();
      heroTl
        .fromTo(".hero-badge", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" })
        .fromTo(".hero-title", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.8, ease: "power3.out" }, "-=0.3")
        .fromTo(".hero-subtitle", { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.6, ease: "power3.out" }, "-=0.4")
        .fromTo(".hero-cta", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.5, ease: "power3.out" }, "-=0.3")
        .fromTo(".hero-visual", { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 1, ease: "power2.out" }, "-=0.5");

      // Feature cards
      gsap.utils.toArray<HTMLElement>(".feature-card").forEach((card, i) => {
        gsap.fromTo(
          card,
          { opacity: 0, y: 60 },
          {
            opacity: 1,
            y: 0,
            duration: 0.6,
            delay: i * 0.1,
            ease: "power3.out",
            scrollTrigger: {
              trigger: card,
              start: "top 85%",
              toggleActions: "play none none none",
            },
          }
        );
      });

      // Tech section
      gsap.fromTo(
        ".tech-card",
        { opacity: 0, y: 40 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          stagger: 0.08,
          ease: "power3.out",
          scrollTrigger: {
            trigger: techRef.current,
            start: "top 80%",
            toggleActions: "play none none none",
          },
        }
      );

      // CTA section
      gsap.fromTo(
        ctaRef.current,
        { opacity: 0, y: 40 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          ease: "power3.out",
          scrollTrigger: {
            trigger: ctaRef.current,
            start: "top 85%",
            toggleActions: "play none none none",
          },
        }
      );
    });

    return () => ctx.revert();
  }, []);

  return (
    <div className="min-h-screen bg-ow-bg overflow-x-hidden">
      {/* Particle canvas */}
      <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none z-0" />

      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-ow-accent/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-ow-teal/8 rounded-full blur-[120px]" />
      </div>

      {/* ──── Nav ──── */}
      <nav className="relative z-20 flex items-center justify-between px-8 py-5 max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-ow-accent to-ow-accent-dim flex items-center justify-center shadow-glow">
            <Eye className="w-5 h-5 text-ow-bg" />
          </div>
          <span className="text-xl font-bold tracking-widest text-ow-accent">
            OVERWATCH
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="px-4 py-2 text-sm text-ow-mist/60 hover:text-ow-light/90 transition-colors"
          >
            Sign In
          </Link>
          <Link
            to="/signup"
            className="px-4 py-2 rounded-xl border border-ow-accent/20 text-sm font-semibold text-ow-accent
                       hover:border-ow-accent/40 hover:bg-ow-accent/8 transition-all"
          >
            Signup
          </Link>
          <Link
            to="/dashboard"
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-ow-accent to-ow-accent-dim text-sm font-semibold text-ow-bg
                       hover:shadow-glow-hover transition-all"
          >
            Open Dashboard
          </Link>
        </div>
      </nav>

      {/* ──── Hero Section ──── */}
      <section ref={heroRef} className="relative z-10 max-w-7xl mx-auto px-8 pt-20 pb-32">
        <div className="text-center max-w-4xl mx-auto">
          <div className="hero-badge inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-ow-accent/12 border border-ow-accent/25 mb-8">
            <Cpu className="w-3.5 h-3.5 text-ow-accent" />
            <span className="text-xs font-semibold text-ow-accent uppercase tracking-wide">AI Vision Monitoring</span>
          </div>

          <h1 className="hero-title text-6xl md:text-7xl font-black leading-tight mb-6">
            <span className="text-ow-light"> An AI Powered</span>
            <br />
            <span className="bg-gradient-to-r from-ow-accent via-ow-accent-dim to-ow-accent bg-clip-text text-transparent">
              Surveillance and Monitoring system
            </span>
            <br />
            <span className="text-ow-light/80"></span>
          </h1>

          <p className="hero-subtitle text-lg text-ow-mist/60 max-w-2xl mx-auto mb-10 leading-relaxed">
            Real-time threat detection, behavioral analysis, and intelligent monitoring
            for modern environments.
          </p>

          <div className="hero-cta flex items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="group px-8 py-3.5 rounded-xl glass-panel border border-ow-accent/30 text-sm font-semibold text-ow-accent
                         hover:bg-ow-accent/15 hover:shadow-glow-hover hover:border-ow-accent/50 transition-all flex items-center gap-2"
            >
              Open Dashboard
              <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link
              to="/signup"
              className="px-8 py-3.5 rounded-xl border border-ow-accent/20 text-sm font-semibold text-ow-accent
                         hover:border-ow-accent/40 hover:bg-ow-accent/8 transition-all"
            >
              Signup
            </Link>
          </div>

        </div>

        {/* Hero visual — glass dashboard preview */}
        <div className="hero-visual mt-20 rounded-3xl glass-panel-heavy p-6 shadow-2xl max-w-5xl mx-auto">
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2 h-64 rounded-2xl bg-gradient-to-br from-ow-surface to-ow-bg border border-[rgba(255,255,255,0.04)] flex items-center justify-center">
              <div className="text-center">
                <Eye className="w-12 h-12 text-ow-accent/20 mx-auto mb-3" />
                <p className="text-sm text-ow-mist/20">Live Camera Feed</p>
              </div>
            </div>
            <div className="space-y-4">
              <div className="h-[120px] rounded-2xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)] p-4">
                <div className="text-xs text-ow-mist/30 uppercase tracking-wider mb-2">Alerts</div>
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-4 rounded bg-ow-teal/10" />
                  ))}
                </div>
              </div>
              <div className="h-[120px] rounded-2xl bg-ow-teal/8 border border-[rgba(255,255,255,0.04)] p-4">
                <div className="text-xs text-ow-mist/30 uppercase tracking-wider mb-2">Status</div>
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-4 rounded bg-ow-teal/10" />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──── Features ──── */}
      <section ref={featuresRef} className="relative z-10 max-w-7xl mx-auto px-8 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-ow-light/90 mb-4">Detection Capabilities</h2>
          <p className="text-ow-mist/50 max-w-xl mx-auto">
            Multi-modal threat detection powered by state-of-the-art deep learning models.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="feature-card group rounded-2xl glass-panel
                         p-6 hover:bg-ow-teal/15 hover:border-ow-accent/15 transition-all duration-300 cursor-default"
            >
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${f.color} flex items-center justify-center mb-4
                              group-hover:shadow-lg transition-shadow`}>
                <f.icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-ow-light/90 mb-2">{f.title}</h3>
              <p className="text-sm text-ow-mist/45 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ──── Tech Stack ──── */}
      <section ref={techRef} className="relative z-10 max-w-7xl mx-auto px-8 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-ow-light/90 mb-4">Technology Stack</h2>
          <p className="text-ow-mist/50 max-w-xl mx-auto">
            Built on proven, production-grade frameworks and models.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {techStack.map((t) => (
            <div
              key={t.name}
              className="tech-card text-center p-5 rounded-2xl glass-panel
                         hover:bg-ow-teal/15 hover:border-ow-accent/15 transition-all duration-200"
            >
              <div className="text-sm font-semibold text-ow-light/80 mb-1">{t.name}</div>
              <div className="text-xs text-ow-mist/35">{t.detail}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ──── CTA ──── */}
      <section ref={ctaRef} className="relative z-10 max-w-4xl mx-auto px-8 py-24 text-center">
        <div className="rounded-3xl bg-gradient-to-br from-ow-accent/8 to-ow-teal/10 backdrop-blur-xl border border-ow-accent/10 p-12">
          <h2 className="text-3xl font-bold text-ow-light/90 mb-4">Ready to Monitor?</h2>
          <p className="text-ow-mist/50 mb-8 max-w-lg mx-auto">
            Access the live dashboard, configure detection modules, and start protecting your environment.
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-ow-accent to-ow-accent-dim
                       text-sm font-semibold text-ow-bg hover:shadow-glow-hover transition-all"
          >
            Launch Dashboard
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[rgba(255,255,255,0.05)] py-8 text-center">
        <p className="text-xs text-ow-mist/20 font-mono">OVERWATCH Surveillance System — v2.0</p>
      </footer>
    </div>
  );
}
