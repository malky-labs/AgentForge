'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../lib/store';
import { getAuthToken } from '../lib/api';

export default function LoginPage() {
  const router = useRouter();
  const { login, register, error, loading } = useAppStore();

  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [localError, setLocalError] = useState('');

  useEffect(() => {
    // If already logged in, redirect
    if (getAuthToken()) {
      router.push('/dashboard');
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError('');
    setSuccessMsg('');

    if (!email || !password || (isSignUp && !fullName)) {
      setLocalError('Please fill in all fields.');
      return;
    }

    try {
      if (isSignUp) {
        await register(email, password, fullName);
        setSuccessMsg('Registration successful! Please log in below.');
        setIsSignUp(false);
        setPassword('');
      } else {
        await login(email, password);
        router.push('/dashboard');
      }
    } catch (err: any) {
      // Errors handled by store or caught here
      setLocalError(err.message || 'An error occurred. Please try again.');
    }
  };

  return (
    <div className="relative min-h-screen bg-black flex items-center justify-center px-4 overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-violet-900/10 rounded-full filter blur-[120px] pointer-events-none" />

      <div className="relative z-10 glass-panel max-w-md w-full p-8 rounded-2xl shadow-2xl transition-all duration-300">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold tracking-tight text-white mb-2">
            {isSignUp ? 'Create Account' : 'Welcome Back'}
          </h2>
          <p className="text-sm text-zinc-400">
            {isSignUp 
              ? 'Join AgentForge to run custom local workflows.' 
              : 'Sign in to access your local AI workspace.'}
          </p>
        </div>

        {/* Alerts */}
        {(localError || error) && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/30 border border-rose-800/50 text-rose-300 text-xs font-medium">
            {localError || error}
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/50 text-emerald-300 text-xs font-medium">
            {successMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {isSignUp && (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="John Doe"
                className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-600 transition"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-600 transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-600 transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium hover:brightness-110 active:scale-[0.98] transition disabled:opacity-50 disabled:pointer-events-none mt-2 shadow-lg shadow-violet-600/20"
          >
            {loading ? 'Processing...' : isSignUp ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm">
          <span className="text-zinc-500">
            {isSignUp ? 'Already have an account? ' : "Don't have an account? "}
          </span>
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setLocalError('');
              setSuccessMsg('');
            }}
            className="text-violet-400 hover:text-violet-300 font-semibold transition"
          >
            {isSignUp ? 'Sign In' : 'Create One'}
          </button>
        </div>
      </div>
    </div>
  );
}
