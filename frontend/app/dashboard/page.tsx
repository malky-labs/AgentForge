'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { 
  MessageSquare, 
  Users, 
  Cpu, 
  GitBranch, 
  Activity, 
  CheckCircle, 
  XCircle,
  ArrowRight
} from 'lucide-react';
import { useAppStore } from '../../lib/store';
import { api } from '../../lib/api';

export default function DashboardPage() {
  const { user, models, fetchModels } = useAppStore();
  const [ollamaHealthy, setOllamaHealthy] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkStatus() {
      try {
        await fetchModels();
        const health = await api.get('/health');
        setOllamaHealthy(health.status === 'healthy');
      } catch (err) {
        setOllamaHealthy(false);
      } finally {
        setLoading(false);
      }
    }
    checkStatus();
  }, [fetchModels]);

  const quickActions = [
    { 
      name: 'Launch AI Chat', 
      desc: 'Start streaming completions with local LLMs', 
      href: '/dashboard/chat', 
      icon: MessageSquare,
      color: 'from-violet-500/20 to-purple-500/20',
      border: 'hover:border-violet-500/50'
    },
    { 
      name: 'Configure Agents', 
      desc: 'Customize system instructions and temperature profile', 
      href: '/dashboard/agents', 
      icon: Users,
      color: 'from-indigo-500/20 to-blue-500/20',
      border: 'hover:border-indigo-500/50'
    },
    { 
      name: 'Model Context Protocol', 
      desc: 'Connect databases and file access servers', 
      href: '/dashboard/mcp', 
      icon: Cpu,
      color: 'from-emerald-500/20 to-teal-500/20',
      border: 'hover:border-emerald-500/50'
    },
    { 
      name: 'Visual Workflows', 
      desc: 'Orchestrate multi-agent execution graphs', 
      href: '/dashboard/workflows', 
      icon: GitBranch,
      color: 'from-pink-500/20 to-rose-500/20',
      border: 'hover:border-pink-500/50'
    },
  ];

  return (
    <div className="flex-1 bg-black p-6 md:p-8 overflow-y-auto max-h-screen">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-10">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2">
            Welcome back, <span className="text-gradient">{user?.full_name || 'Operator'}</span>
          </h1>
          <p className="text-sm text-zinc-400">
            Monitor and run your orchestrations in privacy on local servers.
          </p>
        </div>
        
        {/* Status widget */}
        <div className="flex items-center gap-3 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-2.5">
          <Activity size={16} className="text-zinc-500 animate-pulse" />
          <span className="text-xs font-semibold text-zinc-400">OLLAMA STATUS:</span>
          {loading ? (
            <span className="text-xs text-zinc-500">Checking...</span>
          ) : ollamaHealthy ? (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold">
              <CheckCircle size={14} /> ONLINE
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-rose-400 font-semibold">
              <XCircle size={14} /> OFFLINE
            </span>
          )}
        </div>
      </div>

      {/* Grid of Quick Actions */}
      <h2 className="text-lg font-bold text-zinc-200 mb-4 px-1">Quick Workspace Links</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Link 
              key={action.name}
              href={action.href}
              className={`
                group relative p-6 rounded-xl bg-gradient-to-br ${action.color} border border-zinc-850 glass-card ${action.border} transition flex items-start justify-between gap-4
              `}
            >
              <div className="space-y-2.5">
                <div className="w-10 h-10 rounded-lg bg-zinc-900 flex items-center justify-center border border-zinc-850 group-hover:scale-105 transition-transform duration-200">
                  <Icon className="text-zinc-300" size={20} />
                </div>
                <h3 className="text-lg font-bold text-white group-hover:text-violet-300 transition-colors duration-200">
                  {action.name}
                </h3>
                <p className="text-zinc-400 text-sm leading-relaxed max-w-sm">
                  {action.desc}
                </p>
              </div>
              <ArrowRight size={18} className="text-zinc-500 group-hover:text-white group-hover:translate-x-1.5 transition-all duration-200 mt-2" />
            </Link>
          );
        })}
      </div>

      {/* System info panel */}
      <div className="glass-panel p-6 rounded-xl border border-zinc-800/60">
        <h2 className="text-lg font-bold text-zinc-200 mb-4">Local System Models ({models.length})</h2>
        {models.length === 0 ? (
          <div className="text-center py-8 text-zinc-500 text-sm border border-dashed border-zinc-800 rounded-lg">
            No local GGUF models discovered. Please make sure Ollama is active and pull a model.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <div key={model.name} className="p-4 rounded-lg bg-zinc-950 border border-zinc-850/60 flex flex-col justify-between">
                <div>
                  <h4 className="font-bold text-sm text-zinc-300 truncate">{model.name}</h4>
                  <p className="text-xs text-zinc-500 mt-1">
                    Family: {model.details?.family || 'unknown'} • Format: {model.details?.format || 'gguf'}
                  </p>
                </div>
                {model.size_bytes && (
                  <span className="text-xs text-zinc-650 self-end mt-3">
                    {(model.size_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
