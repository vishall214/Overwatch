import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, Lock, Mail } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const emailError = useMemo(() => {
    if (!submitted) return "";
    if (!email.trim()) return "Email is required";
    if (!email.includes("@")) return "Enter a valid email";
    return "";
  }, [email, submitted]);

  const passwordError = useMemo(() => {
    if (!submitted) return "";
    if (!password.trim()) return "Password is required";
    return "";
  }, [password, submitted]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    setError("");

    if (emailError || passwordError) return;

    try {
      await login(email, password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid credentials");
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10 app-shell-bg">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/4 top-1/4 h-80 w-80 rounded-full bg-accent/20 blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 h-72 w-72 rounded-full bg-accentCyan/20 blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-md page-transition">
        <div className="mb-6 text-center">
          <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-xl glass-card">
            <Eye className="h-6 w-6 text-accent" />
          </span>
          <h1 className="mt-4 text-2xl font-bold tracking-[0.2em] text-textPrimary">OVERWATCH</h1>
          <p className="mt-2 text-sm text-textSecondary">Sign in to continue monitoring</p>
        </div>

        <form onSubmit={handleSubmit} className="glass-card rounded-xl p-6 space-y-4 transition-all duration-300 ease-out hover:scale-[1.01]">
          <div>
            <label htmlFor="email" className="mb-2 block text-xs font-medium uppercase tracking-[0.14em] text-textSecondary">
              Email
            </label>
            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 transition-all duration-300 ease-out focus-within:border-accentCyan focus-within:shadow-[0_0_16px_rgba(34,211,238,0.25)]">
              <Mail className="h-4 w-4 text-textMuted" />
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                className="w-full bg-transparent text-sm text-textPrimary placeholder:text-textMuted outline-none"
              />
            </div>
            {emailError ? <p className="mt-1 text-xs text-threat-high">{emailError}</p> : null}
          </div>

          <div>
            <label htmlFor="password" className="mb-2 block text-xs font-medium uppercase tracking-[0.14em] text-textSecondary">
              Password
            </label>
            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 transition-all duration-300 ease-out focus-within:border-accentCyan focus-within:shadow-[0_0_16px_rgba(34,211,238,0.25)]">
              <Lock className="h-4 w-4 text-textMuted" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                className="w-full bg-transparent text-sm text-textPrimary placeholder:text-textMuted outline-none"
              />
            </div>
            {passwordError ? <p className="mt-1 text-xs text-threat-high">{passwordError}</p> : null}
          </div>

          {error ? <p className="rounded-lg border border-threat-critical/40 bg-threat-critical/20 px-3 py-2 text-xs text-threat-critical">{error}</p> : null}

          <button type="submit" className="btn-primary w-full">
            Sign In
          </button>

          <p className="text-center text-sm text-textSecondary">
            No account yet?{" "}
            <Link to="/signup" className="font-semibold text-accentCyan transition-all duration-300 ease-out hover:text-textPrimary">
              Create account
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
