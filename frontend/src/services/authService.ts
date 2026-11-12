import { apiFetch } from './api';
import { TokenResponse, User } from '../types';

export const authService = {
  async register(name: string, email: string, password: string): Promise<TokenResponse> {
    return apiFetch<TokenResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    return apiFetch<TokenResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async getMe(): Promise<User> {
    return apiFetch<User>('/api/auth/me', {
      method: 'GET',
    });
  },
};
