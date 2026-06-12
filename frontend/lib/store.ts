import { create } from 'zustand';
import { api, setAuthToken, removeAuthToken } from './api';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
}

export interface Message {
  id?: string;
  sender_type: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at?: string;
}

export interface Model {
  name: string;
  size_bytes?: number;
  details?: {
    format: string;
    family: string;
    parameter_size?: string;
  };
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model_name: string;
  temperature: number;
}

interface AppState {
  user: User | null;
  token: string | null;
  conversations: Conversation[];
  activeConversation: Conversation | null;
  messages: Message[];
  models: Model[];
  agents: Agent[];
  activeAgent: Agent | null;
  loading: boolean;
  error: string | null;

  // Auth Actions
  setUser: (user: User | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  loadCurrentUser: () => Promise<void>;

  // Chat Actions
  fetchConversations: () => Promise<void>;
  selectConversation: (conv: Conversation | null) => Promise<void>;
  createConversation: (title: string) => Promise<Conversation>;
  addMessage: (msg: Message) => void;
  clearMessages: () => void;

  // System Catalog Actions
  fetchModels: () => Promise<void>;
  fetchAgents: () => Promise<void>;
  setActiveAgent: (agent: Agent | null) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('agentforge_token') : null,
  conversations: [],
  activeConversation: null,
  messages: [],
  models: [],
  agents: [],
  activeAgent: null,
  loading: false,
  error: null,

  setUser: (user) => set({ user }),

  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      
      const data = await api.postForm('/auth/token', formData);
      setAuthToken(data.access_token);
      set({ token: data.access_token });
      
      // Load user profile
      const userProfile = await api.get('/auth/me');
      set({ user: userProfile, loading: false });
    } catch (err: any) {
      set({ error: err.message || 'Login failed', loading: false });
      throw err;
    }
  },

  register: async (email, password, fullName) => {
    set({ loading: true, error: null });
    try {
      await api.post('/auth/register', { email, password, full_name: fullName });
      set({ loading: false });
    } catch (err: any) {
      set({ error: err.message || 'Registration failed', loading: false });
      throw err;
    }
  },

  logout: () => {
    removeAuthToken();
    set({ user: null, token: null, conversations: [], activeConversation: null, messages: [] });
  },

  loadCurrentUser: async () => {
    try {
      const userProfile = await api.get('/auth/me');
      set({ user: userProfile });
    } catch (err) {
      removeAuthToken();
      set({ user: null, token: null });
    }
  },

  fetchConversations: async () => {
    try {
      const convs = await api.get('/conversations');
      set({ conversations: convs });
    } catch (err: any) {
      console.error('Error fetching conversations:', err);
    }
  },

  selectConversation: async (conv) => {
    set({ activeConversation: conv, messages: [] });
    if (conv) {
      try {
        const msgs = await api.get(`/conversations/${conv.id}/messages`);
        set({ messages: msgs });
      } catch (err: any) {
        set({ error: err.message || 'Failed to load messages' });
      }
    }
  },

  createConversation: async (title) => {
    try {
      const conv = await api.post(`/conversations?title=${encodeURIComponent(title)}`);
      set((state) => ({
        conversations: [conv, ...state.conversations],
      }));
      return conv;
    } catch (err: any) {
      set({ error: err.message || 'Failed to create conversation' });
      throw err;
    }
  },

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  clearMessages: () => set({ messages: [] }),

  fetchModels: async () => {
    try {
      const response = await api.get('/hub/models');
      set({ models: response.models || [] });
    } catch (err) {
      console.error('Failed to fetch Ollama models', err);
    }
  },

  fetchAgents: async () => {
    try {
      const list = await api.get('/agents');
      set({ agents: list });
    } catch (err) {
      console.error('Failed to fetch agents list', err);
    }
  },

  setActiveAgent: (agent) => set({ activeAgent: agent }),
}));
