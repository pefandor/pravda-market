/**
 * Markets API service
 * Handles market-related API calls
 */

import { api } from './api';
import type { Market, Orderbook } from '@/types/api';

/**
 * Get all active markets
 */
export async function getMarkets(): Promise<Market[]> {
  return api.get<Market[]>('/markets');
}

/**
 * Get market by ID
 */
export async function getMarket(marketId: number): Promise<Market> {
  return api.get<Market>(`/markets/${marketId}`);
}

/**
 * Get orderbook for a specific market
 */
export async function getOrderbook(marketId: number): Promise<Orderbook> {
  return api.get<Orderbook>(`/markets/${marketId}/orderbook`);
}
