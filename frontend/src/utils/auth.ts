export const TOKEN_KEY = 'admin_jwt_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers || {});
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  
  const response = await fetch(input, { ...init, headers });
  
  // If we get a 401, clear the token and redirect to login
  if (response.status === 401) {
    clearToken();
    window.location.href = '/admin/login';
  }
  
  return response;
}

export interface AuthStatus {
  setup_required: boolean;
  locked: boolean;
  last_login: string | null;
}

export async function checkAuthStatus(): Promise<AuthStatus> {
  const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
  const response = await fetch(`${API_BASE}/api/auth/status`);
  return response.json();
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  message: string;
  expires_hours?: number;
}

export async function setupPassword(password: string): Promise<AuthResponse> {
  const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
  const response = await fetch(`${API_BASE}/api/auth/setup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password })
  });
  
  const data = await response.json();
  
  if (response.ok && data.success && data.token) {
    setToken(data.token);
  }
  
  return data;
}

export async function login(password: string, rememberMe: boolean = false): Promise<AuthResponse> {
  const API_BASE = process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8000';
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password, remember_me: rememberMe })
  });
  
  const data = await response.json();
  
  if (response.ok && data.success && data.token) {
    setToken(data.token);
  }
  
  return data;
}

export function logout(): void {
  clearToken();
  window.location.href = '/admin/login';
}
