/**
 * TypeScript types for Pravda Market API
 * Based on backend SQLAlchemy models
 */

// ============================================================================
// Database Models
// ============================================================================

export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface Market {
  id: number;
  title: string;
  description: string | null;
  category: string | null;
  deadline: string;
  resolved: boolean;
  resolution_value: boolean | null;
  outcome: 'yes' | 'no' | null;
  resolved_at: string | null;
  yes_price: number; // in basis points (5000 = 50%)
  no_price: number;  // in basis points
  volume: number;    // in kopecks
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: number;
  user_id: number;
  market_id: number;
  side: 'yes' | 'no';
  price: number;     // in basis points (0-9999)
  amount: number;    // in kopecks
  filled: number;    // in kopecks
  status: 'open' | 'filled' | 'cancelled';
  created_at: string;
  updated_at: string;
}

export interface LedgerEntry {
  id: number;
  user_id: number;
  entry_type: 'deposit' | 'withdraw' | 'order_lock' | 'order_unlock' | 'trade_lock' | 'settlement_win' | 'settlement_loss';
  amount: number;    // in kopecks (can be negative)
  balance_after: number | null;
  order_id: number | null;
  market_id: number | null;
  description: string | null;
  created_at: string;
}

export interface Trade {
  id: number;
  market_id: number;
  yes_order_id: number;
  no_order_id: number;
  yes_user_id: number;
  no_user_id: number;
  amount: number;    // trade amount in kopecks
  price: number;     // price in basis points
  yes_cost: number;  // cost for YES side
  no_cost: number;   // cost for NO side
  created_at: string;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface OrderbookLevel {
  price: number;     // in basis points
  amount: number;    // total amount at this price level in kopecks
}

export interface Orderbook {
  market_id: number;
  yes_orders: OrderbookLevel[];
  no_orders: OrderbookLevel[];
}

export interface CreateBetRequest {
  market_id: number;
  side: 'yes' | 'no';
  price: number;     // in basis points (1-9999)
  amount: number;    // in kopecks
}

export interface CreateBetResponse {
  order_id: number;
  message: string;
  matched_trades?: Trade[];
}

export interface UserProfile {
  user: User;
  balance: number;   // in kopecks
}

export interface HealthResponse {
  status: 'ok';
  timestamp: string;
}

export interface ErrorResponse {
  detail: string;
}

// ============================================================================
// Utility Types
// ============================================================================

export type Side = 'yes' | 'no';
export type OrderStatus = 'open' | 'filled' | 'cancelled';
export type LedgerEntryType =
  | 'deposit'
  | 'withdraw'
  | 'order_lock'
  | 'order_unlock'
  | 'trade_lock'
  | 'settlement_win'
  | 'settlement_loss';
