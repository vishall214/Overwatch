import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Eye, Lock, User as UserIcon } from "lucide-react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  if (isAuthenticated) {
    navigate("/dashboard", { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!username.trim()) {
      setError("Username is required");
      return;
    }
    const ok = await login(username, password);
    if (ok) {
      navigate("/dashboard", { replace: true });
    } else {
      setError("Invalid credentials");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-ow-bg">
      {/* Ambient */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-ow-accent/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/3 right-1/3 w-96 h-96 bg-ow-teal/8 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-ow-accent to-ow-accent-dim flex items-center justify-center shadow-glow">
            <Eye className="w-7 h-7 text-ow-bg" />
          </div>
          <h1 className="text-2xl font-bold tracking-widest text-ow-accent">
            OVERWATCH
          </h1>
          <p className="text-sm text-ow-mist/40 mt-1">Sign in to access the dashboard</p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl glass-panel-heavy p-8 shadow-2xl space-y-5"
        >
          <div>
            <label className="block text-xs text-ow-mist/50 uppercase tracking-wider mb-2">Username</label>
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.06)] focus-within:border-ow-accent/30 transition-colors">
              <UserIcon className="w-4 h-4 text-ow-mist/40" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                className="bg-transparent text-sm text-ow-light/80 placeholder:text-ow-mist/25 outline-none w-full"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-ow-mist/50 uppercase tracking-wider mb-2">Password</label>
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-ow-teal/8 border border-[rgba(255,255,255,0.06)] focus-within:border-ow-accent/30 transition-colors">
              <Lock className="w-4 h-4 text-ow-mist/40" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                className="bg-transparent text-sm text-ow-light/80 placeholder:text-ow-mist/25 outline-none w-full"
              />
            </div>
          </div>

          {error && (
            <div className="text-xs text-ow-alert-intrusion bg-ow-alert-intrusion/10 border border-ow-alert-intrusion/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 rounded-xl bg-gradient-to-r from-ow-accent to-ow-accent-dim text-sm font-semibold text-ow-bg
                       hover:shadow-glow-hover transition-all"
          >
            Sign In
          </button>

          <p className="text-center text-xs text-ow-mist/25">
            Demo mode — enter any username to proceed
          </p>

          <div className="mt-3 text-center">
            <Link
              to="/signup"
              className="inline-block px-4 py-2 rounded-md border border-ow-accent/20 text-ow-accent text-sm font-medium hover:bg-ow-accent/8 transition-colors"
            >
              Signup
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
