/**
 * Centralized HTTP client for PolicyDesk Frontend.
 * Reads API base URL from `import.meta.env.VITE_API_BASE_URL` and automatically
 * attaches the Bearer JWT token stored in localStorage.
 */

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

export const TOKEN_STORAGE_KEY = 'policydesk_access_token';
export const USER_STORAGE_KEY = 'policydesk_user';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredAuth(token: string, user: unknown): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredAuth(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(USER_STORAGE_KEY);
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorData = await response.json();
      if (typeof errorData.detail === 'string') {
        errorDetail = errorData.detail;
      } else if (Array.isArray(errorData.detail) && errorData.detail.length > 0) {
        errorDetail = errorData.detail
          .map((e: { msg?: string }) => e.msg || JSON.stringify(e))
          .join('; ');
      }
    } catch {
      // Fallback to HTTP status text if JSON parsing fails
      errorDetail = response.statusText || errorDetail;
    }

    if (response.status === 401 && !endpoint.includes('/api/auth/login')) {
      clearStoredAuth();
      window.dispatchEvent(new CustomEvent('policydesk:unauthorized'));
    }

    throw new ApiError(errorDetail, response.status);
  }

  return (await response.json()) as T;
}
