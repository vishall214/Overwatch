import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CheckCircle, Eye, EyeOff, Lock, Mail } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const emailError = useMemo(() => {
    if (!submitted) return "";
    if (!formData.email.trim()) return "Email is required";
    if (!formData.email.includes("@")) return "Enter a valid email";
    return "";
  }, [formData.email, submitted]);

  const passwordError = useMemo(() => {
    if (!submitted) return "";
    if (!formData.password.trim()) return "Password is required";
    if (formData.password.length < 8) return "Minimum 8 characters";
    return "";
  }, [formData.password, submitted]);

  const confirmError = useMemo(() => {
    if (!submitted) return "";
    if (!formData.confirmPassword.trim()) return "Confirm your password";
    if (formData.password !== formData.confirmPassword) return "Passwords do not match";
    return "";
  }, [formData.confirmPassword, formData.password, submitted]);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setFormData((previous) => ({ ...previous, [name]: value }));
    setError("");
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    setError("");

    if (emailError || passwordError || confirmError) return;

    setLoading(true);
    try {
      await register(formData.email, formData.password);
      setSuccess(true);
      setTimeout(() => navigate("/dashboard"), 1200);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed. Please try again.");
    } finally {
      setLoading(false);
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
          <h1 className="text-2xl font-bold tracking-[0.18em] text-textPrimary">CREATE ACCOUNT</h1>
          <p className="mt-2 text-sm text-textSecondary">Set up your operator access</p>
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
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
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
                name="password"
                type={showPassword ? "text" : "password"}
                value={formData.password}
                onChange={handleChange}
                placeholder="Minimum 8 characters"
                className="w-full bg-transparent text-sm text-textPrimary placeholder:text-textMuted outline-none"
              />
              <button type="button" onClick={() => setShowPassword((value) => !value)} className="text-textMuted transition-all duration-300 ease-out hover:text-textPrimary">
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {passwordError ? <p className="mt-1 text-xs text-threat-high">{passwordError}</p> : null}
          </div>

          <div>
            <label htmlFor="confirmPassword" className="mb-2 block text-xs font-medium uppercase tracking-[0.14em] text-textSecondary">
              Confirm Password
            </label>
            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 transition-all duration-300 ease-out focus-within:border-accentCyan focus-within:shadow-[0_0_16px_rgba(34,211,238,0.25)]">
              <Lock className="h-4 w-4 text-textMuted" />
              <input
                id="confirmPassword"
                name="confirmPassword"
                type={showConfirm ? "text" : "password"}
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Repeat password"
                className="w-full bg-transparent text-sm text-textPrimary placeholder:text-textMuted outline-none"
              />
              <button type="button" onClick={() => setShowConfirm((value) => !value)} className="text-textMuted transition-all duration-300 ease-out hover:text-textPrimary">
                {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {confirmError ? <p className="mt-1 text-xs text-threat-high">{confirmError}</p> : null}
          </div>

          {error ? <p className="rounded-lg border border-threat-critical/40 bg-threat-critical/20 px-3 py-2 text-xs text-threat-critical">{error}</p> : null}
          {success ? (
            <p className="inline-flex items-center gap-2 rounded-lg border border-threat-low/40 bg-threat-low/20 px-3 py-2 text-xs text-threat-low">
              <CheckCircle className="h-3.5 w-3.5" />
              Account created. Redirecting...
            </p>
          ) : null}

          <button type="submit" disabled={loading || success} className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60">
            {loading ? "Creating account..." : success ? "Success" : "Create Account"}
          </button>

          <p className="text-center text-sm text-textSecondary">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-accentCyan transition-all duration-300 ease-out hover:text-textPrimary">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
