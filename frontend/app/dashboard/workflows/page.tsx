'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  ReactFlow, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState, 
  addEdge,
  Connection,
  Edge,
  Node
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { 
  GitBranch, 
  Plus, 
  Save, 
  Play, 
  Trash2, 
  Cpu, 
  User, 
  Terminal,
  Activity,
  CheckCircle,
  XCircle,
  Loader
} from 'lucide-react';
import { useAppStore, Agent } from '../../../lib/store';
import { api } from '../../../lib/api';

// --- Custom Node Styles ---
const nodeTypes = {
  agentNode: ({ data, id }: any) => {
    const { agents, updateNodeData } = data;
    return (
      <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/90 text-left min-w-[240px] shadow-xl relative">
        <div className="flex items-center gap-2 mb-3 border-b border-zinc-900 pb-2">
          <User size={14} className="text-violet-400" />
          <span className="text-xs font-bold text-white uppercase tracking-wider">Agent Node</span>
        </div>
        
        <div className="space-y-3">
          <div>
            <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Select Persona</label>
            <select
              value={data.agentId || ''}
              onChange={(e) => updateNodeData(id, { agentId: e.target.value })}
              className="w-full bg-black border border-zinc-850 text-xs rounded px-2 py-1.5 text-zinc-300 focus:outline-none focus:border-violet-650"
            >
              <option value="" disabled>Select agent</option>
              {agents.map((a: Agent) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Node Prompt</label>
            <textarea
              value={data.prompt || ''}
              onChange={(e) => updateNodeData(id, { prompt: e.target.value })}
              rows={2}
              placeholder="Prompt input directives..."
              className="w-full bg-black border border-zinc-850 text-[11px] rounded px-2 py-1.5 text-zinc-300 focus:outline-none focus:border-violet-650 font-sans"
            />
          </div>
        </div>
      </div>
    );
  },
  
  toolNode: ({ data, id }: any) => {
    const { updateNodeData } = data;
    return (
      <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/90 text-left min-w-[240px] shadow-xl">
        <div className="flex items-center gap-2 mb-3 border-b border-zinc-900 pb-2">
          <Terminal size={14} className="text-emerald-400" />
          <span className="text-xs font-bold text-white uppercase tracking-wider">Tool Node</span>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Select Tool</label>
            <select
              value={data.toolName || 'python_sandbox'}
              onChange={(e) => updateNodeData(id, { toolName: e.target.value })}
              className="w-full bg-black border border-zinc-850 text-xs rounded px-2 py-1.5 text-zinc-300 focus:outline-none"
            >
              <option value="python_sandbox">Python Sandbox</option>
            </select>
          </div>

          <div>
            <label className="block text-[10px] text-zinc-500 font-semibold mb-1 uppercase">Script / Input Code</label>
            <textarea
              value={data.arguments?.code || ''}
              onChange={(e) => updateNodeData(id, { arguments: { code: e.target.value } })}
              rows={3}
              placeholder="print('Execution result...')"
              className="w-full bg-black border border-zinc-850 text-[10px] rounded px-2 py-1.5 text-emerald-450 focus:outline-none font-mono"
            />
          </div>
        </div>
      </div>
    );
  }
};

interface Workflow {
  id: string;
  name: string;
  description: string;
  graph_json: string;
}

interface RunLog {
  id: string;
  state: 'pending' | 'running' | 'completed' | 'failed';
  error_message?: string;
  started_at: string;
}

export default function WorkflowsPage() {
  const { agents, fetchAgents } = useAppStore();

  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const [runsList, setRunsList] = useState<RunLog[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchWorkflows = async () => {
    try {
      const list = await api.get('/workflows');
      setWorkflows(list);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchExecutions = async (wfId: string) => {
    try {
      const history = await api.get(`/workflows/${wfId}/executions`);
      setRunsList(history);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchWorkflows();
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    if (selectedWorkflow) {
      try {
        const graph = JSON.parse(selectedWorkflow.graph_json);
        // Map custom helper functions to nodes
        const restoredNodes = (graph.nodes || []).map((node: Node) => ({
          ...node,
          data: {
            ...node.data,
            agents,
            updateNodeData
          }
        }));
        setNodes(restoredNodes);
        setEdges(graph.edges || []);
        fetchExecutions(selectedWorkflow.id);
      } catch (err) {
        setNodes([]);
        setEdges([]);
      }
    } else {
      setNodes([]);
      setEdges([]);
      setRunsList([]);
    }
  }, [selectedWorkflow, agents, setNodes, setEdges]);

  // Node input data sync callback
  const updateNodeData = useCallback((nodeId: string, newData: any) => {
    setNodes((nds) => 
      nds.map((node) => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              ...newData
            }
          };
        }
        return node;
      })
    );
  }, [setNodes]);

  const onConnect = useCallback((params: Connection | Edge) => {
    setEdges((eds) => addEdge(params, eds));
  }, [setEdges]);

  const handleCreateWorkflow = async () => {
    const title = prompt('Enter workflow name:') || `Workflow ${workflows.length + 1}`;
    try {
      const data = await api.post('/workflows', {
        name: title,
        graph_json: JSON.stringify({ nodes: [], edges: [] })
      });
      fetchWorkflows();
      setSelectedWorkflow(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddNode = (type: 'agentNode' | 'toolNode') => {
    if (!selectedWorkflow) return;
    const newId = `node-${Date.now()}`;
    const newNode: Node = {
      id: newId,
      type,
      position: { x: 100 + nodes.length * 40, y: 150 + nodes.length * 40 },
      data: {
        agentId: '',
        prompt: type === 'agentNode' ? 'Enter task...' : '',
        toolName: type === 'toolNode' ? 'python_sandbox' : '',
        arguments: type === 'toolNode' ? { code: 'print("hello")' } : {},
        agents,
        updateNodeData
      }
    };
    setNodes((nds) => [...nds, newNode]);
  };

  const handleSaveGraph = async () => {
    if (!selectedWorkflow) return;
    setLoading(true);
    try {
      // Serialize nodes and edges
      const graph_json = JSON.stringify({ nodes, edges });
      await api.put(`/workflows/${selectedWorkflow.id}`, {
        name: selectedWorkflow.name,
        graph_json
      });
      alert('Workflow saved successfully.');
      fetchWorkflows();
    } catch (err: any) {
      alert(err.message || 'Failed to save workflow.');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!selectedWorkflow) return;
    try {
      await api.post(`/workflows/${selectedWorkflow.id}/execute`);
      alert('Workflow run initiated in background.');
      fetchExecutions(selectedWorkflow.id);
    } catch (err: any) {
      alert(err.message || 'Failed to execute workflow.');
    }
  };

  const handleDeleteWorkflow = async (id: string) => {
    if (!confirm('Are you sure you want to delete this workflow blueprint?')) return;
    try {
      await api.delete(`/workflows/${id}`);
      setSelectedWorkflow(null);
      fetchWorkflows();
    } catch (err: any) {
      alert(err.message || 'Failed to delete workflow.');
    }
  };

  return (
    <div className="flex-1 flex bg-black h-screen overflow-hidden">
      {/* Side Blueprints List panel */}
      <div className="w-80 border-r border-zinc-800/60 bg-zinc-950/20 flex flex-col justify-between hidden sm:flex shrink-0">
        <div className="p-4 flex flex-col gap-4 overflow-hidden flex-1">
          <button
            onClick={handleCreateWorkflow}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg border border-dashed border-zinc-800 text-sm font-medium text-zinc-400 hover:border-violet-650 hover:text-violet-300 transition"
          >
            <Plus size={16} />
            Create Workflow
          </button>

          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {workflows.map((wf) => {
              const isActive = selectedWorkflow?.id === wf.id;
              return (
                <button
                  key={wf.id}
                  onClick={() => setSelectedWorkflow(wf)}
                  className={`
                    w-full text-left flex items-center justify-between px-3 py-3 rounded-lg text-sm transition group
                    ${isActive 
                      ? 'bg-zinc-900 border border-zinc-800/80 text-white' 
                      : 'text-zinc-450 hover:bg-zinc-950 hover:text-zinc-200 border border-transparent'}
                  `}
                >
                  <div className="flex items-center gap-3 truncate">
                    <GitBranch size={16} className={isActive ? 'text-violet-400' : 'text-zinc-500'} />
                    <span className="truncate">{wf.name}</span>
                  </div>
                  
                  <Trash2 
                    size={14} 
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteWorkflow(wf.id);
                    }}
                    className="text-zinc-650 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity" 
                  />
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Canvas Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-hidden justify-between relative bg-black/40">
        
        {/* Editor controls Header */}
        <div className="h-16 border-b border-zinc-800/65 flex items-center justify-between px-6 z-10 glass-panel">
          <span className="font-bold text-white text-sm md:text-base">
            {selectedWorkflow ? selectedWorkflow.name : 'Select or Create Workflow'}
          </span>

          {selectedWorkflow && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleAddNode('agentNode')}
                className="px-3 py-1.5 rounded-lg border border-zinc-850 hover:border-zinc-750 bg-zinc-950 text-zinc-300 hover:text-white text-xs transition"
              >
                + Add Agent Node
              </button>
              <button
                onClick={() => handleAddNode('toolNode')}
                className="px-3 py-1.5 rounded-lg border border-zinc-850 hover:border-zinc-750 bg-zinc-950 text-zinc-300 hover:text-white text-xs transition"
              >
                + Add Tool Node
              </button>
              
              <div className="w-[1px] h-6 bg-zinc-800/60 mx-1" />

              <button
                onClick={handleSaveGraph}
                disabled={loading}
                className="px-3.5 py-1.5 rounded-lg bg-zinc-900 border border-zinc-850 hover:border-violet-650 text-zinc-300 hover:text-white text-xs transition flex items-center gap-1.5"
              >
                <Save size={13} /> Save
              </button>
              <button
                onClick={handleExecute}
                className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 text-white text-xs transition flex items-center gap-1.5 shadow-lg shadow-violet-600/15"
              >
                <Play size={13} fill="currentColor" /> Run Execution
              </button>
            </div>
          )}
        </div>

        {/* React Flow Board */}
        <div className="flex-1 relative bg-black">
          {!selectedWorkflow ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center max-w-sm mx-auto z-10">
              <GitBranch size={36} className="text-violet-500 mb-4 animate-pulse-glow" />
              <h3 className="text-lg font-bold text-white mb-2">Visual Workflow Orchestrator</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">
                Choose a workflow design from the sidebar or build a new agent execution graph from scratch.
              </p>
            </div>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              className="bg-black/90"
            >
              <Background color="#1f1f23" gap={16} size={1} />
              <Controls className="bg-zinc-900 border border-zinc-800 fill-zinc-400" />
            </ReactFlow>
          )}
        </div>

        {/* Executions Logs Footer Drawer */}
        {selectedWorkflow && runsList.length > 0 && (
          <div className="h-44 border-t border-zinc-850 bg-zinc-950/40 p-4 overflow-y-auto z-10 glass-panel">
            <h4 className="text-xs font-semibold text-zinc-450 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Activity size={12} className="text-violet-400" />
              Recent Execution Logs ({runsList.length})
            </h4>
            
            <div className="space-y-2">
              {runsList.map((run) => (
                <div key={run.id} className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950 border border-zinc-900 text-xs">
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-zinc-500 text-[10px]">{run.id.slice(0, 8)}</span>
                    <span className="text-zinc-400">Triggered: {new Date(run.started_at).toLocaleString()}</span>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {run.state === 'running' ? (
                      <span className="flex items-center gap-1 text-yellow-500 font-semibold">
                        <Loader size={12} className="animate-spin" /> In Progress
                      </span>
                    ) : run.state === 'completed' ? (
                      <span className="flex items-center gap-1 text-emerald-400 font-semibold">
                        <CheckCircle size={12} /> Complete
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-rose-400 font-semibold" title={run.error_message}>
                        <XCircle size={12} /> Failed: {run.error_message || 'Unknown error'}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
