/**
 * User API service
 * Handles user profile and balance API calls
 */

import { api } from './api';
import type { LedgerEntry, UserProfile } from '@/types/api';

/**
 * Get current user profile (authenticated via Telegram initData)
 */
export async function getUserProfile(): Promise<UserProfile> {
  return api.get<UserProfile>('/user/profile');
}

/**
 * Get current user info (alias for /user/profile)
 */
export async function getCurrentUser(): Promise<UserProfile> {
  return api.get<UserProfile>('/user/me');
}

/**
 * Get user's ledger entries (transaction history)
 */
export async function getUserLedger(): Promise<LedgerEntry[]> {
  return api.get<LedgerEntry[]>('/ledger/transactions');
}

/**
 * Get user balance
 */
export async function getUserBalance(): Promise<{ balance: number }> {
  const profile = await getUserProfile();
  return { balance: profile.balance };
}
