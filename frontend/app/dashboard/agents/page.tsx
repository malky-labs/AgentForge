'use client';

import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Plus, 
  Trash2, 
  Edit3, 
  Sliders, 
  MessageSquare,
  Bot,
  Save,
  X
} from 'lucide-react';
import { useAppStore, Agent } from '../../../lib/store';
import { api } from '../../../lib/api';

export default function AgentsPage() {
  const { 
    agents, 
    models, 
    fetchAgents, 
    fetchModels 
  } = useAppStore();

  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  
  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [modelName, setModelName] = useState('');
  const [temperature, setTemperature] = useState(0.7);

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    fetchAgents();
    fetchModels();
  }, [fetchAgents, fetchModels]);

  const handleOpenCreate = () => {
    setEditingAgent(null);
    setName('');
    setDescription('');
    setSystemPrompt('You are a professional assistant.');
    // Set fallback model
    if (models.length > 0) {
      setModelName(models[0].name);
    } else {
      setModelName('llama3:8b');
    }
    setTemperature(0.7);
    setIsFormOpen(true);
    setErrorMsg('');
  };

  const handleOpenEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setName(agent.name);
    setDescription(agent.description || '');
    setSystemPrompt(agent.system_prompt);
    setModelName(agent.model_name);
    setTemperature(agent.temperature);
    setIsFormOpen(true);
    setErrorMsg('');
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    if (!name.trim() || !systemPrompt.trim() || !modelName.trim()) {
      setErrorMsg('Name, system prompt, and model must be specified.');
      setLoading(false);
      return;
    }

    const payload = {
      name: name.trim(),
      description: description.trim() || undefined,
      system_prompt: systemPrompt.trim(),
      model_provider: 'ollama',
      model_name: modelName,
      temperature,
    };

    try {
      if (editingAgent) {
        await api.put(`/agents/${editingAgent.id}`, payload);
      } else {
        await api.post('/agents', payload);
      }
      setIsFormOpen(false);
      fetchAgents();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to save agent profile.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this agent persona?')) return;
    try {
      await api.delete(`/agents/${id}`);
      fetchAgents();
    } catch (err: any) {
      alert(err.message || 'Failed to delete agent.');
    }
  };

  return (
    <div className="flex-1 bg-black p-6 md:p-8 overflow-y-auto max-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2 flex items-center gap-3">
            <Users size={28} className="text-violet-400" />
            Agent Persona Studio
          </h1>
          <p className="text-sm text-zinc-400">
            Define custom system directives and local LLM parameter overrides.
          </p>
        </div>
        
        <button
          onClick={handleOpenCreate}
          className="px-4 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium hover:brightness-110 active:scale-[0.98] transition flex items-center gap-2 text-sm shadow-lg shadow-violet-600/25"
        >
          <Plus size={16} /> Forge Persona
        </button>
      </div>

      {/* Main Grid / Form Layout */}
      {isFormOpen ? (
        /* Agent Form Panel */
        <div className="glass-panel p-6 rounded-xl border border-zinc-800/80 max-w-2xl mx-auto relative shadow-2xl">
          <button
            onClick={() => setIsFormOpen(false)}
            className="absolute top-4 right-4 p-1 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-900 transition"
          >
            <X size={18} />
          </button>

          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Bot size={20} className="text-violet-400" />
            {editingAgent ? 'Configure Persona' : 'Forge New Persona'}
          </h2>

          {errorMsg && (
            <div className="mb-4 p-3 rounded-lg bg-rose-950/20 border border-rose-800/50 text-rose-300 text-xs">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSave} className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. SearchForge"
                  className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-650 transition text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                  Model Selector
                </label>
                <select
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 focus:outline-none focus:border-violet-650 transition text-sm"
                >
                  <option value="" disabled>Select model</option>
                  {models.map((model) => (
                    <option key={model.name} value={model.name}>
                      {model.name}
                    </option>
                  ))}
                  {models.length === 0 && (
                    <option value="llama3:8b">llama3:8b (default fallback)</option>
                  )}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
                Short Description
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary of what this agent excels at"
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-650 transition text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5 flex justify-between">
                <span>System Directive Prompt</span>
                <span className="text-zinc-550 text-[10px] lowercase italic">Injected first into inference conversation</span>
              </label>
              <textarea
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                rows={5}
                placeholder="You are a professional research agent. You must query local files first..."
                className="w-full px-3.5 py-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-violet-650 transition text-sm font-mono leading-relaxed"
              />
            </div>

            {/* Slider for Temperature */}
            <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-850/60">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                  <Sliders size={14} className="text-violet-400" />
                  Temperature: {temperature}
                </span>
                <span className="text-[10px] text-zinc-500 italic">
                  {temperature <= 0.3 ? 'Deterministic' : temperature >= 0.8 ? 'Creative' : 'Balanced'}
                </span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.5"
                step="0.05"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full accent-violet-600 bg-zinc-850 h-1.5 rounded-lg cursor-pointer"
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
                {loading ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        /* Agent Listing cards */
        <>
          {agents.length === 0 ? (
            <div className="text-center py-16 text-zinc-500 text-sm border border-dashed border-zinc-850 rounded-xl max-w-md mx-auto">
              <Bot size={40} className="mx-auto text-zinc-600 mb-4 animate-pulse-glow" />
              <h3 className="text-base font-bold text-zinc-300 mb-1.5">No custom personas forged</h3>
              <p className="text-xs text-zinc-500 px-6 leading-relaxed mb-6">
                Personas store distinct models, system instructions, and generation temperatures for quick access in chats or workflows.
              </p>
              <button
                onClick={handleOpenCreate}
                className="px-4 py-2 rounded-lg bg-violet-650 text-white font-semibold hover:bg-violet-600 text-xs shadow-md transition"
              >
                Create First Persona
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {agents.map((agent) => (
                <div 
                  key={agent.id}
                  className="glass-card p-5 rounded-xl border border-zinc-850 flex flex-col justify-between group shadow-lg"
                >
                  <div className="space-y-4">
                    <div className="flex justify-between items-start gap-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-violet-950/25 border border-violet-850/45 text-violet-400 flex items-center justify-center font-bold">
                          <Bot size={20} />
                        </div>
                        <div className="min-w-0">
                          <h3 className="font-bold text-white truncate text-base">{agent.name}</h3>
                          <span className="text-[10px] font-mono bg-zinc-900 border border-zinc-850 px-2 py-0.5 rounded text-zinc-450 mt-1 inline-block truncate max-w-[150px]">
                            {agent.model_name}
                          </span>
                        </div>
                      </div>

                      {/* Config Options buttons */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        <button
                          onClick={() => handleOpenEdit(agent)}
                          className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900 transition"
                        >
                          <Edit3 size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(agent.id)}
                          className="p-1.5 rounded-lg text-zinc-450 hover:text-rose-400 hover:bg-rose-950/15 transition"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>

                    <p className="text-zinc-400 text-sm leading-relaxed line-clamp-2 min-h-[40px]">
                      {agent.description || 'No description provided.'}
                    </p>
                  </div>

                  {/* Summary parameters footer */}
                  <div className="border-t border-zinc-850/60 pt-4 mt-5 flex items-center justify-between text-xs text-zinc-500">
                    <span className="flex items-center gap-1.5">
                      <Sliders size={12} className="text-zinc-500" />
                      Temp: {agent.temperature}
                    </span>
                    <span className="capitalize">
                      ollama
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
