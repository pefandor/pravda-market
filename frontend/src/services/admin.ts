/**
 * Admin API service
 *
 * Provides functions to interact with admin endpoints.
 * Requires ADMIN_TOKEN for authentication.
 */

import type { Market } from '@/types/api';

// Admin token stored in session (set via UI)
let adminToken: string | null = null;

export function setAdminToken(token: string): void {
  adminToken = token;
  sessionStorage.setItem('admin_token', token);
}

export function getAdminToken(): string | null {
  if (!adminToken) {
    adminToken = sessionStorage.getItem('admin_token');
  }
  return adminToken;
}

export function clearAdminToken(): void {
  adminToken = null;
  sessionStorage.removeItem('admin_token');
}

async function adminFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAdminToken();
  if (!token) {
    throw new Error('Admin token not set');
  }

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const url = `${apiUrl}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Неверный admin token');
    }
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// ============================================================================
// Market Management
// ============================================================================

export interface AdminMarket extends Market {
  id: number;
  title: string;
  resolved: boolean;
  outcome: 'yes' | 'no' | null;
}

export async function getMarkets(): Promise<AdminMarket[]> {
  return adminFetch<AdminMarket[]>('/admin/markets');
}

export async function resolveMarket(
  marketId: number,
  outcome: 'yes' | 'no'
): Promise<{ message: string }> {
  return adminFetch<{ message: string }>(`/admin/markets/${marketId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ outcome }),
  });
}

// ============================================================================
// User Management
// ============================================================================

export interface AdminUser {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  balance_rubles: number;
  created_at: string;
}

export async function getUsers(): Promise<AdminUser[]> {
  return adminFetch<AdminUser[]>('/admin/users');
}

export async function depositToUser(
  telegramId: number,
  amount: number
): Promise<{ success: boolean; new_balance_rubles: number }> {
  return adminFetch<{ success: boolean; new_balance_rubles: number }>(
    `/admin/users/${telegramId}/deposit`,
    {
      method: 'POST',
      body: JSON.stringify({ amount }),
    }
  );
}
