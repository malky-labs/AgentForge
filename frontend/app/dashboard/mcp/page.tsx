'use client';

import React, { useState, useEffect } from 'react';
import { 
  Cpu, 
  Plus, 
  Trash2, 
  RefreshCw, 
  Database,
  Terminal,
  Activity,
  CheckCircle,
  XCircle,
  Save,
  X
} from 'lucide-react';
import { api } from '../../../lib/api';

interface McpServer {
  id: string;
  name: string;
  command: string;
  args: string;
  env: string;
  status: 'running' | 'error' | 'offline';
  created_at: string;
}

interface DiscoveredTool {
  name: string;
  description: string;
}

export default function McpPage() {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);

  // Form states
  const [name, setName] = useState('');
  const [command, setCommand] = useState('npx');
  const [args, setArgs] = useState('["-y", "@modelcontextprotocol/server-postgres", "--db-uri", "postgresql://localhost/mydb"]');
  const [env, setEnv] = useState('{}');

  const [reloadingIds, setReloadingIds] = useState<Record<string, boolean>>({});
  const [discoveredTools, setDiscoveredTools] = useState<Record<string, DiscoveredTool[]>>({});
  const [errorMsg, setErrorMsg] = useState('');

  const fetchServers = async () => {
    try {
      const data = await api.get('/mcp/servers');
      setServers(data);
    } catch (err) {
      console.error('Failed to fetch MCP servers', err);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    if (!name.trim() || !command.trim()) {
      setErrorMsg('Name and command are required.');
      setLoading(false);
      return;
    }

    try {
      // Validate JSON formats
      JSON.parse(args);
      JSON.parse(env);
    } catch (err) {
      setErrorMsg('Arguments and Env must be valid JSON strings.');
      setLoading(false);
      return;
    }

    try {
      await api.post('/mcp/servers', {
        name: name.trim(),
        command: command.trim(),
        args,
        env
      });
      setIsFormOpen(false);
      setName('');
      setCommand('npx');
      setArgs('[]');
      setEnv('{}');
      fetchServers();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to register MCP server.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this MCP configuration? All associated tools will be removed.')) return;
    try {
      await api.delete(`/mcp/servers/${id}`);
      fetchServers();
    } catch (err: any) {
      alert(err.message || 'Failed to delete server.');
    }
  };

  const handleReload = async (id: string) => {
    setReloadingIds((prev) => ({ ...prev, [id]: true }));
    try {
      const result = await api.post(`/mcp/servers/${id}/reload`);
      setDiscoveredTools((prev) => ({ ...prev, [id]: result.tools_discovered }));
      fetchServers();
    } catch (err: any) {
      alert(err.message || 'Failed to reload MCP server.');
    } finally {
      setReloadingIds((prev) => ({ ...prev, [id]: false }));
    }
  };

  return (
    <div className="flex-1 bg-black p-6 md:p-8 overflow-y-auto max-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2 flex items-center gap-3">
            <Cpu size={28} className="text-violet-400" />
            Model Context Protocol
          </h1>
          <p className="text-sm text-zinc-400">
            Connect external data sources, files, and scripting engines directly to your agents.
          </p>
        </div>

        <button
          onClick={() => setIsFormOpen(true)}
          className="px-4 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium hover:brightness-110 active:scale-[0.98] transition flex items-center gap-2 text-sm shadow-lg shadow-violet-600/25"
        >
          <Plus size={16} /> Register Server
        </button>
      </div>

      {/* Form panel */}
      {isFormOpen ? (
        <div className="glass-panel p-6 rounded-xl border border-zinc-800/80 max-w-2xl mx-auto relative shadow-2xl mb-8">
          <button
            onClick={() => setIsFormOpen(false)}
            className="absolute top-4 right-4 p-1 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-900 transition"
          >
            <X size={18} />
          </button>

          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Terminal size={20} className="text-violet-400" />
            Register MCP Stdio Server
          </h2>

          {errorMsg && (
            <div className="mb-4 p-3 rounded-lg bg-rose-950/20 border border-rose-800/50 text-rose-300 text-xs">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                  Server Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. postgres-tool"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-650 transition text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                  Binary / Executable
                </label>
                <input
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="e.g. npx or python"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-650 transition text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 flex justify-between">
                <span>Arguments (JSON Array)</span>
                <span className="text-[10px] text-zinc-550 italic lowercase">e.g. ["-y", "@modelcontextprotocol/server-postgres"]</span>
              </label>
              <textarea
                value={args}
                onChange={(e) => setArgs(e.target.value)}
                rows={3}
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 focus:outline-none focus:border-violet-650 transition text-sm font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 flex justify-between">
                <span>Environment (JSON Object)</span>
                <span className="text-[10px] text-zinc-550 italic lowercase">e.g. {"{"}"API_KEY": "secret"{"}"}</span>
              </label>
              <textarea
                value={env}
                onChange={(e) => setEnv(e.target.value)}
                rows={3}
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 focus:outline-none focus:border-violet-650 transition text-sm font-mono"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsFormOpen(false)}
                className="px-4 py-2.5 rounded-lg bg-zinc-900 border border-zinc-850 text-zinc-300 font-medium hover:bg-zinc-850 transition text-sm"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium hover:brightness-110 transition flex items-center gap-2 text-sm shadow-lg shadow-violet-600/20"
              >
                <Save size={16} />
                {loading ? 'Saving...' : 'Register Server'}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {/* Servers Listing */}
      <div className="space-y-6">
        {servers.length === 0 ? (
          <div className="text-center py-16 text-zinc-500 text-sm border border-dashed border-zinc-850 rounded-xl max-w-md mx-auto">
            <Cpu size={40} className="mx-auto text-zinc-600 mb-4" />
            <h3 className="text-base font-bold text-zinc-300 mb-1.5">No MCP servers registered</h3>
            <p className="text-xs text-zinc-500 px-6 leading-relaxed mb-6">
              Register stdio servers to dynamically expose file systems, database schemas, or APIs to your agents.
            </p>
          </div>
        ) : (
          servers.map((server) => {
            const isReloading = reloadingIds[server.id];
            const tools = discoveredTools[server.id] || [];
            return (
              <div 
                key={server.id}
                className="glass-panel p-6 rounded-xl border border-zinc-800/60 flex flex-col gap-6"
              >
                {/* Header info */}
                <div className="flex justify-between items-start gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-11 h-11 rounded-lg bg-zinc-950 border border-zinc-850 flex items-center justify-center text-zinc-400 shadow-inner">
                      <Database size={22} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5">
                        <h3 className="text-lg font-bold text-white leading-none">{server.name}</h3>
                        <span className={`
                          flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full border
                          ${server.status === 'running' 
                            ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-400' 
                            : server.status === 'error'
                              ? 'bg-rose-950/20 border-rose-900/40 text-rose-400'
                              : 'bg-zinc-900 border-zinc-800 text-zinc-500'}
                        `}>
                          {server.status === 'running' ? <CheckCircle size={10} /> : <XCircle size={10} />}
                          {server.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500 mt-2 font-mono truncate max-w-md">
                        {server.command} {JSON.parse(server.args).join(' ')}
                      </p>
                    </div>
                  </div>

                  {/* Reload and delete triggers */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleReload(server.id)}
                      disabled={isReloading}
                      className="px-3 py-1.5 rounded-lg border border-zinc-850 hover:border-violet-650 bg-zinc-950 text-zinc-400 hover:text-white text-xs transition flex items-center gap-1.5 disabled:opacity-40"
                    >
                      <RefreshCw size={12} className={isReloading ? 'animate-spin' : ''} />
                      {isReloading ? 'Booting...' : 'Reload & Discover'}
                    </button>
                    <button
                      onClick={() => handleDelete(server.id)}
                      className="p-2 rounded-lg text-zinc-400 hover:text-rose-400 hover:bg-rose-950/20 transition"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {/* Discovered Tools sub-list */}
                {tools.length > 0 && (
                  <div className="pt-4 border-t border-zinc-900">
                    <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
                      Discovered Tools ({tools.length})
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {tools.map((t) => (
                        <div key={t.name} className="p-3.5 rounded-lg bg-zinc-950/40 border border-zinc-900">
                          <span className="font-bold text-violet-300 text-sm">{t.name}</span>
                          <p className="text-zinc-500 text-xs leading-relaxed mt-1">{t.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
