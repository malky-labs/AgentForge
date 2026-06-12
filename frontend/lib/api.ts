const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('agentforge_token');
  }
  return null;
}

export function setAuthToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('agentforge_token', token);
  }
}

export function removeAuthToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('agentforge_token');
  }
}

async function request(method: string, path: string, body?: any, isForm = false) {
  const token = getAuthToken();
  const headers: HeadersInit = {};

  if (!isForm) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config: RequestInit = {
    method,
    headers,
  };

  if (body) {
    if (isForm) {
      config.body = body;
    } else {
      config.body = JSON.stringify(body);
    }
  }

  const response = await fetch(`${BASE_URL}${path}`, config);

  if (response.status === 401) {
    removeAuthToken();
    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(errorData.detail || 'API Request failed');
  }

  return response.json();
}

export const api = {
  get: (path: string) => request('GET', path),
  post: (path: string, body?: any) => request('POST', path, body),
  postForm: (path: string, formData: FormData) => request('POST', path, formData, true),
  put: (path: string, body?: any) => request('PUT', path, body),
  delete: (path: string) => request('DELETE', path),
  
  // Return websocket connection
  connectWebSocket: (conversationId: string): WebSocket => {
    const token = getAuthToken();
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Match server URL
    const wsUrl = `ws://localhost:8000/api/v1/ws/chat/${conversationId}?token=${token || ''}`;
    return new WebSocket(wsUrl);
  }
};
