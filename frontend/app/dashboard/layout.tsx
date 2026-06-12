'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { 
  MessageSquare, 
  Users, 
  Cpu, 
  GitBranch, 
  LogOut, 
  Activity,
  Menu,
  X
} from 'lucide-react';
import { useAppStore } from '../../lib/store';
import { getAuthToken } from '../../lib/api';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loadCurrentUser, logout } = useAppStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      router.push('/login');
    } else if (!user) {
      loadCurrentUser();
    }
  }, [user, router, loadCurrentUser]);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const navItems = [
    { name: 'AI Chat', href: '/dashboard/chat', icon: MessageSquare },
    { name: 'Agent Hub', href: '/dashboard/agents', icon: Users },
    { name: 'MCP Servers', href: '/dashboard/mcp', icon: Cpu },
    { name: 'Workflows', href: '/dashboard/workflows', icon: GitBranch },
  ];

  if (!user) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-violet-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black flex overflow-hidden">
      {/* Mobile Sidebar Toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden absolute top-4 left-4 z-50 p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-300 hover:text-white"
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Sidebar Panel */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 glass-panel border-r border-zinc-800/60 p-5 flex flex-col justify-between transition-transform duration-300 md:translate-x-0 md:static md:flex
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <div className="flex flex-col gap-8">
          {/* Logo Brand */}
          <Link href="/dashboard" className="flex items-center gap-3 px-2">
            <div className="w-8 h-8 bg-gradient-to-tr from-violet-600 to-indigo-600 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <span className="font-bold text-xl tracking-tight text-white">
              Agent<span className="text-violet-400">Forge</span>
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`
                    flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition duration-150
                    ${isActive 
                      ? 'bg-violet-950/40 text-violet-300 border border-violet-850/50' 
                      : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 border border-transparent'}
                  `}
                >
                  <Icon size={18} className={isActive ? 'text-violet-400' : ''} />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User Footer Profile */}
        <div className="space-y-4 pt-4 border-t border-zinc-800/60">
          <div className="flex items-center gap-3 px-2">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-violet-600 to-fuchsia-600 flex items-center justify-center font-bold text-sm text-white shadow-md">
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-semibold text-white truncate">
                {user.full_name || 'AgentForge User'}
              </span>
              <span className="text-xs text-zinc-500 truncate">
                {user.email}
              </span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-rose-400 hover:bg-rose-950/20 hover:text-rose-300 transition duration-150 border border-transparent"
          >
            <LogOut size={18} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 relative flex flex-col min-h-screen">
        {children}
      </main>
    </div>
  );
}
