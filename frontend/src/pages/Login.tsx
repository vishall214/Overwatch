import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Eye, Lock, User as UserIcon } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email.trim()) {
      setError("Email is required");
      return;
    }

    try {
      await login(email, password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid credentials");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg">
      {/* Ambient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-accent/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/3 right-1/3 w-96 h-96 bg-threat-info/10 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-accent flex items-center justify-center">
            <Eye className="w-7 h-7 text-bg" />
          </div>
          <h1 className="text-2xl font-bold tracking-widest text-accent">
            OVERWATCH
          </h1>
          <p className="text-sm text-textSecondary mt-1">Sign in to access the dashboard</p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="panel-base rounded-2xl p-8 space-y-5"
        >
          <div>
            <label className="block text-xs text-textMuted uppercase tracking-wider mb-2">Email</label>
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface border border-border focus-within:border-accent transition-colors">
              <UserIcon className="w-4 h-4 text-textMuted" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="bg-transparent text-sm text-textPrimary placeholder:text-textMuted outline-none w-full"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-textMuted uppercase tracking-wider mb-2">Password</label>
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface border border-border focus-within:border-accent transition-colors">
              <Lock className="w-4 h-4 text-textMuted" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="bg-transparent text-sm text-textPrimary placeholder:text-textMuted outline-none w-full"
              />
            </div>
          </div>

          {error && (
            <div className="text-xs text-threat-critical bg-threat-critical/10 border border-threat-critical/30 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 rounded-xl bg-accent text-sm font-semibold text-bg hover:bg-accent/90 transition-colors"
          >
            Sign In
          </button>

          <div className="mt-3 text-center">
            <Link
              to="/signup"
              className="inline-block px-4 py-2 rounded-md border border-border text-accent text-sm font-medium hover:bg-card transition-colors"
            >
              Signup
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
