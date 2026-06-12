'use client';

import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Webhook, 
  Plus, 
  Trash2, 
  CheckCircle, 
  DownloadCloud, 
  Loader, 
  History, 
  Terminal,
  Activity
} from 'lucide-react';
import { api } from '../../../lib/api';

interface Subscription {
  id: string;
  target_url: string;
  event_type: string;
  secret_token?: string;
  created_at: string;
}

interface DeliveryLog {
  id: string;
  event_type: string;
  payload: string;
  response_status?: number;
  response_body?: string;
  created_at: string;
}

export default function SettingsPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [deliveryLogs, setDeliveryLogs] = useState<DeliveryLog[]>([]);
  const [selectedSub, setSelectedSub] = useState<Subscription | null>(null);

  // Webhook form state
  const [targetUrl, setTargetUrl] = useState('');
  const [eventType, setEventType] = useState('*');
  const [secretToken, setSecretToken] = useState('');
  const [addingSub, setAddingSub] = useState(false);

  // Ollama model pull state
  const [modelToPull, setModelToPull] = useState('');
  const [pullProgress, setPullProgress] = useState('');
  const [pulling, setPulling] = useState(false);

  useEffect(() => {
    fetchSubscriptions();
  }, []);

  useEffect(() => {
    if (selectedSub) {
      fetchDeliveryLogs(selectedSub.id);
    } else {
      setDeliveryLogs([]);
    }
  }, [selectedSub]);

  const fetchSubscriptions = async () => {
    try {
      const res = await api.get('/webhooks/subscriptions');
      setSubscriptions(res);
      if (res.length > 0) {
        setSelectedSub(res[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchDeliveryLogs = async (subId: string) => {
    try {
      const res = await api.get(`/webhooks/subscriptions/${subId}/deliveries`);
      setDeliveryLogs(res);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetUrl.trim()) return;

    setAddingSub(true);
    try {
      const newSub = await api.post('/webhooks/subscriptions', {
        target_url: targetUrl.trim(),
        event_type: eventType,
        secret_token: secretToken.trim() || null
      });
      setSubscriptions((prev) => [...prev, newSub]);
      setSelectedSub(newSub);
      setTargetUrl('');
      setSecretToken('');
    } catch (err) {
      console.error(err);
    } finally {
      setAddingSub(false);
    }
  };

  const handleDeleteSub = async (subId: string) => {
    if (!confirm('Are you sure you want to delete this subscription?')) return;
    try {
      await api.delete(`/webhooks/subscriptions/${subId}`);
      setSubscriptions((prev) => prev.filter((s) => s.id !== subId));
      if (selectedSub?.id === subId) {
        setSelectedSub(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handlePullModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modelToPull.trim()) return;

    setPulling(true);
    setPullProgress('Connecting to Ollama library...');
    
    try {
      // Direct pull API connection
      // For simplicity, we trigger the endpoint. In production, we stream the WS or keep checking.
      const res = await api.post('/hub/pull', { model: modelToPull.trim() });
      setPullProgress(`Pull completed successfully! Initialized: ${modelToPull}`);
    } catch (err: any) {
      setPullProgress(`Error: ${err.message || 'Failed to pull model.'}`);
    } finally {
      setPulling(false);
      setModelToPull('');
    }
  };

  return (
    <div className="flex-1 bg-black p-6 md:p-8 overflow-y-auto max-h-screen">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2 flex items-center gap-3">
          <SettingsIcon className="text-violet-500" /> Platform Settings
        </h1>
        <p className="text-sm text-zinc-400">
          Configure developer webhooks, trigger callbacks, and pull models from the Ollama repository.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Side: Webhooks Manager */}
        <div className="space-y-6">
          <div className="glass-panel p-6 rounded-xl border border-zinc-800/60 space-y-4">
            <h3 className="text-lg font-bold text-zinc-200 flex items-center gap-2">
              <Webhook size={18} className="text-violet-400" /> Register Developer Webhooks
            </h3>
            
            <form onSubmit={handleCreateSubscription} className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-500">Payload Destination URL</label>
                <input
                  type="url"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  placeholder="https://api.yourdomain.com/callbacks"
                  className="w-full bg-zinc-950 border border-zinc-850 rounded-lg px-3.5 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-650"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-500">Event Trigger</label>
                  <select
                    value={eventType}
                    onChange={(e) => setEventType(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-850 rounded-lg px-3 py-2 text-sm text-zinc-350 focus:outline-none focus:border-violet-650"
                  >
                    <option value="*">All Events (*)</option>
                    <option value="agent.completed">Agent Completed</option>
                    <option value="agent.failed">Agent Failed</option>
                    <option value="workflow.completed">Workflow Completed</option>
                    <option value="workflow.failed">Workflow Failed</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-zinc-500">Secret Token (HMAC Signature)</label>
                  <input
                    type="text"
                    value={secretToken}
                    onChange={(e) => setSecretToken(e.target.value)}
                    placeholder="my-secret-key"
                    className="w-full bg-zinc-950 border border-zinc-850 rounded-lg px-3.5 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-650"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={addingSub || !targetUrl.trim()}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 text-white text-sm font-semibold rounded-lg transition"
              >
                {addingSub ? <Loader size={16} className="animate-spin" /> : <Plus size={16} />} Save Subscription
              </button>
            </form>
          </div>

          {/* Subscriptions List */}
          <div className="glass-panel p-6 rounded-xl border border-zinc-800/60 space-y-4">
            <h3 className="text-lg font-bold text-zinc-200">Active Subscriptions</h3>
            {subscriptions.length === 0 ? (
              <div className="text-center py-6 text-zinc-500 text-sm">
                No webhook subscriptions registered yet.
              </div>
            ) : (
              <div className="space-y-2">
                {subscriptions.map((sub) => {
                  const isSelected = selectedSub?.id === sub.id;
                  return (
                    <div 
                      key={sub.id} 
                      onClick={() => setSelectedSub(sub)}
                      className={`
                        p-3 rounded-lg border cursor-pointer flex items-center justify-between gap-4 transition
                        ${isSelected 
                          ? 'bg-zinc-900/40 border-zinc-800' 
                          : 'bg-zinc-950/20 border-transparent hover:bg-zinc-950'}
                      `}
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-zinc-300 truncate">{sub.target_url}</p>
                        <p className="text-xs text-zinc-550 mt-1">Event: {sub.event_type} {sub.secret_token ? '• Signed (HMAC)' : ''}</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSub(sub.id);
                        }}
                        className="p-1 text-zinc-500 hover:text-rose-400 transition"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Ollama Library Puller & Webhook Delivery Logs */}
        <div className="space-y-6">
          {/* Pull local LLM models */}
          <div className="glass-panel p-6 rounded-xl border border-zinc-800/60 space-y-4">
            <h3 className="text-lg font-bold text-zinc-200 flex items-center gap-2">
              <DownloadCloud size={18} className="text-violet-400" /> Pull Ollama Library Models
            </h3>
            
            <form onSubmit={handlePullModel} className="flex gap-3">
              <input
                type="text"
                value={modelToPull}
                onChange={(e) => setModelToPull(e.target.value)}
                placeholder="e.g., mistral, phi3, all-minilm"
                className="flex-1 bg-zinc-950 border border-zinc-850 rounded-xl px-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-violet-650"
                required
              />
              <button
                type="submit"
                disabled={pulling || !modelToPull.trim()}
                className="px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold rounded-xl text-sm transition hover:brightness-110 disabled:opacity-50"
              >
                Pull Model
              </button>
            </form>

            {pullProgress && (
              <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-850 flex items-start gap-3 text-xs text-zinc-400 font-mono">
                {pulling ? <Loader size={14} className="animate-spin text-violet-400 shrink-0 mt-0.5" /> : <Terminal size={14} className="text-zinc-500 shrink-0 mt-0.5" />}
                <span className="whitespace-pre-wrap">{pullProgress}</span>
              </div>
            )}
          </div>

          {/* Webhook Delivery Logs */}
          <div className="glass-panel p-6 rounded-xl border border-zinc-800/60 space-y-4">
            <h3 className="text-lg font-bold text-zinc-200 flex items-center gap-2">
              <History size={18} className="text-violet-400" /> Webhook Deliveries ({deliveryLogs.length})
            </h3>

            {!selectedSub ? (
              <div className="text-center py-6 text-zinc-500 text-sm">
                Select a subscription on the left to see delivery history.
              </div>
            ) : deliveryLogs.length === 0 ? (
              <div className="text-center py-6 text-zinc-500 text-sm">
                No events delivered to this webhook endpoint yet.
              </div>
            ) : (
              <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
                {deliveryLogs.map((log) => {
                  const success = log.response_status && log.response_status >= 200 && log.response_status < 300;
                  return (
                    <div key={log.id} className="p-3 rounded-lg bg-zinc-950 border border-zinc-850/60 flex items-start justify-between gap-3 text-xs">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-zinc-300">{log.event_type}</span>
                          <span className="text-zinc-650">•</span>
                          <span className="text-zinc-500">{new Date(log.created_at).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-zinc-500 font-mono truncate max-w-xs">{log.payload}</p>
                      </div>
                      <span className={`
                        font-semibold rounded px-1.5 py-0.5 shrink-0
                        ${success ? 'bg-emerald-950/20 text-emerald-400 border border-emerald-900/20' : 'bg-rose-950/20 text-rose-400 border border-rose-900/20'}
                      `}>
                        {log.response_status || 'ERR'}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
