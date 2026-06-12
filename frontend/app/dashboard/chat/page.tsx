'use client';

import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, 
  Send, 
  Plus, 
  Bot, 
  User as UserIcon,
  Sparkles,
  Loader
} from 'lucide-react';
import { useAppStore, Conversation, Message } from '../../../lib/store';
import { api } from '../../../lib/api';

export default function ChatPage() {
  const {
    conversations,
    activeConversation,
    messages,
    models,
    agents,
    fetchConversations,
    selectConversation,
    createConversation,
    fetchModels,
    fetchAgents,
    addMessage
  } = useAppStore();

  const [input, setInput] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // Load catalogs on mount
  useEffect(() => {
    fetchConversations();
    fetchModels();
    fetchAgents();
  }, [fetchConversations, fetchModels, fetchAgents]);

  // Connect websocket on activeConversation change
  useEffect(() => {
    if (activeConversation) {
      // Clean up previous websocket
      if (wsRef.current) {
        wsRef.current.close();
      }

      // Establish new connection
      const socket = api.connectWebSocket(activeConversation.id);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log('Chat WebSocket connected');
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'token') {
            setIsStreaming(true);
            setStreamingContent((prev) => prev + data.content);
          } else if (data.type === 'done') {
            setIsStreaming(false);
            // Append final assistant message to store
            addMessage({
              id: data.message_id,
              sender_type: 'assistant',
              content: data.content
            });
            setStreamingContent('');
          } else if (data.type === 'error') {
            setIsStreaming(false);
            addMessage({
              sender_type: 'system',
              content: data.content
            });
            setStreamingContent('');
          }
        } catch (err) {
          console.error('WebSocket message parsing error:', err);
        }
      };

      socket.onerror = (err) => {
        console.error('WebSocket connection error:', err);
      };

      socket.onclose = () => {
        console.log('Chat WebSocket disconnected');
      };
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [activeConversation, addMessage]);

  // Scroll to bottom on new message or stream chunk
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleCreateChat = async () => {
    const title = prompt('Enter chat title:') || `New Chat ${conversations.length + 1}`;
    try {
      const newConv = await createConversation(title);
      selectConversation(newConv);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const userMessageContent = input.trim();
    setInput('');
    
    // Add user message to UI local state immediately
    addMessage({
      sender_type: 'user',
      content: userMessageContent
    });

    // Send payload over websocket
    const payload = {
      content: userMessageContent,
      agent_id: selectedAgentId || null
    };

    wsRef.current.send(JSON.stringify(payload));
  };

  return (
    <div className="flex-1 flex bg-black h-screen overflow-hidden">
      {/* Chats List Sidebar Sub-Panel */}
      <div className="w-80 border-r border-zinc-800/60 bg-zinc-950/20 flex flex-col justify-between hidden sm:flex">
        <div className="p-4 flex flex-col gap-4 overflow-hidden flex-1">
          <button
            onClick={handleCreateChat}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg border border-dashed border-zinc-800 text-sm font-medium text-zinc-400 hover:border-violet-650 hover:text-violet-300 transition"
          >
            <Plus size={16} />
            New Conversation
          </button>

          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
            {conversations.map((conv) => {
              const isActive = activeConversation?.id === conv.id;
              return (
                <button
                  key={conv.id}
                  onClick={() => selectConversation(conv)}
                  className={`
                    w-full text-left flex items-center gap-3 px-3 py-3 rounded-lg text-sm transition
                    ${isActive 
                      ? 'bg-zinc-900 border border-zinc-800/80 text-white' 
                      : 'text-zinc-450 hover:bg-zinc-950 hover:text-zinc-200 border border-transparent'}
                  `}
                >
                  <MessageSquare size={16} className={isActive ? 'text-violet-400' : 'text-zinc-500'} />
                  <span className="truncate">{conv.title}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Info panel */}
        <div className="p-4 border-t border-zinc-800/60 text-xs text-zinc-600 tracking-wider text-center">
          LOCAL MULTI-AGENT STUDIO
        </div>
      </div>

      {/* Main Conversation Window */}
      <div className="flex-1 flex flex-col h-full overflow-hidden justify-between relative bg-black/40">
        
        {/* Chat Header */}
        <div className="h-16 border-b border-zinc-800/65 flex items-center justify-between px-6 z-10 glass-panel">
          <div className="flex items-center gap-3">
            <span className="font-bold text-white text-sm md:text-base truncate">
              {activeConversation ? activeConversation.title : 'Select or Create Chat'}
            </span>
          </div>

          {/* Configuration tools */}
          {activeConversation && (
            <div className="flex items-center gap-4">
              {/* Agent Persona Selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-500 font-semibold uppercase tracking-wider hidden md:inline">
                  Persona:
                </span>
                <select
                  value={selectedAgentId}
                  onChange={(e) => setSelectedAgentId(e.target.value)}
                  className="bg-zinc-950 border border-zinc-850 text-xs rounded-lg px-2.5 py-1.5 text-zinc-300 focus:outline-none focus:border-violet-650"
                >
                  <option value="">Default Assistant</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name} ({agent.model_name})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Message Logs */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {!activeConversation ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
              <Sparkles size={36} className="text-violet-500 mb-4 animate-pulse-glow" />
              <h3 className="text-lg font-bold text-white mb-2">Ready to Forge</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">
                Choose a conversation from the sidebar or launch a new chat to begin local LLM streaming.
              </p>
              <button
                onClick={handleCreateChat}
                className="mt-5 px-5 py-2.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-medium hover:brightness-110 transition flex items-center gap-2 text-sm"
              >
                <Plus size={16} /> Create New Chat
              </button>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => {
                const isUser = msg.sender_type === 'user';
                const isSystem = msg.sender_type === 'system';
                return (
                  <div 
                    key={index}
                    className={`flex items-start gap-4 max-w-3xl ${isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'}`}
                  >
                    <div className={`
                      w-8 h-8 rounded-lg flex items-center justify-center border shadow-sm shrink-0
                      ${isUser 
                        ? 'bg-zinc-900 border-zinc-800 text-zinc-300' 
                        : isSystem 
                          ? 'bg-rose-950/20 border-rose-800/30 text-rose-450' 
                          : 'bg-violet-950/35 border-violet-800/40 text-violet-400'}
                    `}>
                      {isUser ? <UserIcon size={16} /> : <Bot size={16} />}
                    </div>

                    <div className={`
                      px-4 py-3 rounded-xl text-sm leading-relaxed whitespace-pre-wrap
                      ${isUser 
                        ? 'bg-zinc-950 border border-zinc-800 text-zinc-200' 
                        : isSystem 
                          ? 'bg-rose-950/20 border border-rose-900/30 text-rose-300' 
                          : 'glass-card border border-zinc-800/40 text-zinc-200'}
                    `}>
                      {msg.content}
                    </div>
                  </div>
                );
              })}

              {/* Real-time Streaming Response bubble */}
              {isStreaming && streamingContent && (
                <div className="flex items-start gap-4 max-w-3xl mr-auto">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center border border-violet-850/40 bg-violet-950/35 text-violet-400 shrink-0">
                    <Bot size={16} />
                  </div>
                  <div className="px-4 py-3 rounded-xl text-sm leading-relaxed glass-card border border-zinc-800/40 text-zinc-200 whitespace-pre-wrap">
                    {streamingContent}
                    <span className="inline-block w-1.5 h-4 ml-1 bg-violet-500 animate-pulse" />
                  </div>
                </div>
              )}

              {/* Streaming loading indicator */}
              {isStreaming && !streamingContent && (
                <div className="flex items-start gap-4 max-w-3xl mr-auto">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center border border-zinc-800 bg-zinc-900 text-zinc-400 shrink-0">
                    <Loader size={16} className="animate-spin" />
                  </div>
                  <div className="px-4 py-3 rounded-xl text-sm leading-relaxed text-zinc-500 italic">
                    Agent is thinking...
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </>
          )}
        </div>

        {/* Chat input form */}
        {activeConversation && (
          <div className="p-4 bg-zinc-950/25 border-t border-zinc-850 z-10 glass-panel">
            <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-3 relative">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isStreaming ? "Wait for response..." : "Ask your local agent anything..."}
                disabled={isStreaming}
                className="flex-1 bg-zinc-950 border border-zinc-850 rounded-xl px-4 py-3 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-violet-650 transition disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isStreaming || !input.trim()}
                className="px-4 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 text-white transition disabled:opacity-30 flex items-center justify-center"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}
