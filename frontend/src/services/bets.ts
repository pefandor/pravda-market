/**
 * Bets API service
 * Handles bet/order-related API calls
 */

import { api } from './api';
import type {
  Order,
  Trade,
  CreateBetRequest,
  CreateBetResponse,
} from '@/types/api';

/**
 * Place a new bet (create order)
 */
export async function placeBet(
  request: CreateBetRequest
): Promise<CreateBetResponse> {
  return api.post<CreateBetResponse>('/bets/', request);
}

/**
 * Get bet/order details by ID
 */
export async function getBet(betId: number): Promise<Order> {
  return api.get<Order>(`/bets/${betId}`);
}

/**
 * Get trades for a specific bet/order
 */
export async function getBetTrades(betId: number): Promise<Trade[]> {
  return api.get<Trade[]>(`/bets/${betId}/trades`);
}

/**
 * Get user's orders
 * @param userId Optional user ID filter
 */
export async function getUserOrders(userId?: number): Promise<Order[]> {
  const endpoint = userId ? `/bets/?user_id=${userId}` : '/bets/';
  return api.get<Order[]>(endpoint);
}

/**
 * Cancel an open order
 * Returns unlocked amount
 */
export interface CancelOrderResponse {
  success: boolean;
  order_id: number;
  status: string;
  unlocked_amount: number;
}

export async function cancelOrder(orderId: number): Promise<CancelOrderResponse> {
  return api.delete<CancelOrderResponse>(`/bets/${orderId}`);
}
