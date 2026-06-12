'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getAuthToken } from '../lib/api';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      router.push('/dashboard');
    }
  }, [router]);

  return (
    <div className="relative min-h-screen bg-black flex flex-col items-center justify-center px-4 overflow-hidden">
      {/* Decorative gradient glowing spots */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary-glow rounded-full filter blur-[100px] pointer-events-none animate-pulse-glow" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-96 h-96 bg-indigo-900/20 rounded-full filter blur-[100px] pointer-events-none" />

      {/* Hero card panel */}
      <div className="relative z-10 glass-panel max-w-2xl w-full p-8 md:p-12 rounded-2xl text-center flex flex-col items-center shadow-2xl">
        <div className="w-16 h-16 bg-gradient-to-tr from-violet-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-violet-500/20 mb-6">
          <svg className="w-9 h-9 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>

        <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4">
          Welcome to <span className="text-gradient">AgentForge</span>
        </h1>
        
        <p className="text-gray-400 text-lg mb-8 max-w-lg leading-relaxed">
          The privacy-first, local-focused AI operating platform. Design, execute, and monitor multi-agent loops and workflows on your own hardware.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 w-full justify-center">
          <Link 
            href="/login" 
            className="px-8 py-3 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium hover:brightness-110 transition shadow-lg shadow-violet-600/30"
          >
            Get Started
          </Link>
          <a 
            href="https://github.com/malky-labs/AgentForge" 
            target="_blank" 
            rel="noopener noreferrer" 
            className="px-8 py-3 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 font-medium hover:bg-zinc-850 hover:text-white transition"
          >
            GitHub Repository
          </a>
        </div>
      </div>
      
      {/* Footer */}
      <div className="absolute bottom-6 text-zinc-650 text-xs tracking-wider z-10">
        POWERED BY OLLAMA & NEXT.JS
      </div>
    </div>
  );
}
