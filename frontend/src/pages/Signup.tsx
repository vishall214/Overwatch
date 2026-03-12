import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, User, Eye, EyeOff, Loader, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Signup() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      setError('Name is required');
      return false;
    }
    if (!formData.email.includes('@')) {
      setError('Valid email is required');
      return false;
    }
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);
    try {
      // Call the register function (will be implemented with real auth)
      await register(formData.email, formData.password, formData.name);
      setSuccess(true);
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Signup failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ow-bg flex items-center justify-center px-4 sm:px-6 lg:px-8 py-12">
      {/* Background grid */}
      <div className="absolute inset-0 bg-grid-teal/5 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-br from-ow-accent/5 via-transparent to-ow-accent/5 pointer-events-none" />

      <div className="relative w-full max-w-md">
        {/* Container */}
        <div className="glass-panel border border-ow-accent/10 rounded-2xl p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-black text-ow-light mb-2">
              Signup
            </h1>
            <p className="text-ow-mist/60 text-sm">
              Join OVERWATCH and start monitoring in minutes
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name Field */}
            <div className="group">
              <label htmlFor="name" className="block text-xs font-semibold text-ow-mist/70 mb-2.5 uppercase tracking-wide">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-3 w-4 h-4 text-ow-accent/50 group-focus-within:text-ow-accent transition-colors" />
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="John Doe"
                  className="w-full pl-10 pr-4 py-2.5 bg-ow-surface/60 border border-ow-accent/10 rounded-lg
                           text-ow-light placeholder:text-ow-mist/30
                           focus:outline-none focus:border-ow-accent/40 focus:bg-ow-surface/80 transition-all
                           hover:border-ow-accent/20"
                />
              </div>
            </div>

            {/* Email Field */}
            <div className="group">
              <label htmlFor="email" className="block text-xs font-semibold text-ow-mist/70 mb-2.5 uppercase tracking-wide">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3 w-4 h-4 text-ow-accent/50 group-focus-within:text-ow-accent transition-colors" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-ow-surface/60 border border-ow-accent/10 rounded-lg
                           text-ow-light placeholder:text-ow-mist/30
                           focus:outline-none focus:border-ow-accent/40 focus:bg-ow-surface/80 transition-all
                           hover:border-ow-accent/20"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="group">
              <label htmlFor="password" className="block text-xs font-semibold text-ow-mist/70 mb-2.5 uppercase tracking-wide">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3 w-4 h-4 text-ow-accent/50 group-focus-within:text-ow-accent transition-colors" />
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-10 py-2.5 bg-ow-surface/60 border border-ow-accent/10 rounded-lg
                           text-ow-light placeholder:text-ow-mist/30
                           focus:outline-none focus:border-ow-accent/40 focus:bg-ow-surface/80 transition-all
                           hover:border-ow-accent/20"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-3 text-ow-mist/50 hover:text-ow-accent transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              <p className="text-xs text-ow-mist/50 mt-2">Minimum 8 characters</p>
            </div>

            {/* Confirm Password Field */}
            <div className="group">
              <label htmlFor="confirmPassword" className="block text-xs font-semibold text-ow-mist/70 mb-2.5 uppercase tracking-wide">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3 w-4 h-4 text-ow-accent/50 group-focus-within:text-ow-accent transition-colors" />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirm ? 'text' : 'password'}
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-10 py-2.5 bg-ow-surface/60 border border-ow-accent/10 rounded-lg
                           text-ow-light placeholder:text-ow-mist/30
                           focus:outline-none focus:border-ow-accent/40 focus:bg-ow-surface/80 transition-all
                           hover:border-ow-accent/20"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3.5 top-3 text-ow-mist/50 hover:text-ow-accent transition-colors"
                >
                  {showConfirm ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <span className="text-sm text-red-400">{error}</span>
              </div>
            )}

            {/* Success Message */}
            {success && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-ow-accent/10 border border-ow-accent/30">
                <CheckCircle className="w-4 h-4 text-ow-accent flex-shrink-0" />
                <span className="text-sm text-ow-accent">Account created! Redirecting...</span>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || success}
              className="w-full py-2.5 rounded-lg bg-gradient-to-r from-ow-accent to-ow-accent-dim
                       text-ow-bg font-semibold text-sm
                       hover:shadow-glow-hover disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Creating Account...
                </>
              ) : success ? (
                <>
                  <CheckCircle className="w-4 h-4" />
                  Success!
                </>
              ) : (
                  'Signup'
                )}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="h-px flex-1 bg-gradient-to-r from-ow-accent/0 via-ow-accent/20 to-ow-accent/0" />
          </div>

          {/* Login Link */}
          <p className="text-center text-sm text-ow-mist/60">
            Already have an account?{' '}
            <Link
              to="/login"
              className="text-ow-accent font-semibold hover:text-ow-accent-dim transition-colors"
            >
              Sign In
            </Link>
          </p>
        </div>

        {/* Footer Link */}
        <p className="text-center text-xs text-ow-mist/40 mt-6">
          By creating an account, you agree to our{' '}
          <button className="text-ow-accent/60 hover:text-ow-accent transition-colors">
            Terms of Service
          </button>
        </p>
      </div>
    </div>
  );
}
