/**
 * TON Blockchain Service
 *
 * Functions for creating TON transactions for the Pravda Market escrow contract.
 */

import { beginCell, toNano } from '@ton/ton';

// Escrow contract address (testnet)
export const ESCROW_ADDRESS = 'kQCCEQCxcKFt89YFL5qa3Hc_nwV7vRxhHtvLcXhdM34Fmmhy';

// Deposit opcode (must match contract)
const DEPOSIT_OPCODE = 0x00000001;

// Minimum deposit amount in TON
export const MIN_DEPOSIT_TON = 0.1;

/**
 * Create a deposit transaction for TON Connect
 *
 * @param amountTon - Amount to deposit in TON
 * @param telegramId - User's Telegram ID (used as memo)
 * @returns Transaction object for TON Connect sendTransaction
 */
export function createDepositTransaction(amountTon: number, telegramId: number) {
  // Validate amount
  if (amountTon < MIN_DEPOSIT_TON) {
    throw new Error(`Minimum deposit is ${MIN_DEPOSIT_TON} TON`);
  }

  // Build payload with opcode and telegram_id
  // Format: uint32 opcode + uint64 telegram_id
  const payload = beginCell()
    .storeUint(DEPOSIT_OPCODE, 32)
    .storeUint(telegramId, 64)
    .endCell();

  // Convert payload to base64-encoded BOC
  const payloadBase64 = payload.toBoc().toString('base64');

  // Create transaction for TON Connect
  return {
    validUntil: Math.floor(Date.now() / 1000) + 600, // 10 minutes
    messages: [
      {
        address: ESCROW_ADDRESS,
        amount: toNano(amountTon).toString(),
        payload: payloadBase64,
      },
    ],
  };
}

/**
 * Format TON amount for display
 *
 * @param nanoTon - Amount in nanoTON
 * @returns Formatted string with TON symbol
 */
export function formatTonAmount(nanoTon: bigint | string | number): string {
  const ton = Number(nanoTon) / 1e9;
  return `${ton.toFixed(2)} TON`;
}

/**
 * Get explorer URL for a transaction
 *
 * @param txHash - Transaction hash
 * @param testnet - Whether to use testnet explorer
 * @returns Explorer URL
 */
export function getExplorerUrl(txHash: string, testnet = true): string {
  const baseUrl = testnet
    ? 'https://testnet.tonscan.org/tx'
    : 'https://tonscan.org/tx';
  return `${baseUrl}/${txHash}`;
}

// ============================================================================
// Withdrawal API Functions
// ============================================================================

import { api } from './api';
import type {
  WithdrawalRequest,
  CreateWithdrawalRequest,
  WithdrawalListResponse,
} from '@/types/api';

// Withdrawal constants
export const MIN_WITHDRAWAL_TON = 1.0;
export const WITHDRAWAL_FEE_TON = 0.05;
export const MAX_WITHDRAWAL_PER_DAY_TON = 1000;

/**
 * Create a withdrawal request
 *
 * @param tonAddress - Destination TON wallet address
 * @param amountTon - Amount to withdraw in TON
 * @returns Withdrawal request details
 */
export async function createWithdrawal(
  tonAddress: string,
  amountTon: number
): Promise<WithdrawalRequest> {
  const request: CreateWithdrawalRequest = {
    ton_address: tonAddress,
    amount_ton: amountTon,
  };
  return api.post<WithdrawalRequest>('/withdrawals', request);
}

/**
 * Get list of user's withdrawal requests
 *
 * @param limit - Max results (default 20)
 * @param offset - Pagination offset
 * @param status - Filter by status
 * @returns List of withdrawals with total count
 */
export async function getWithdrawals(
  limit = 20,
  offset = 0,
  status?: string
): Promise<WithdrawalListResponse> {
  const params = new URLSearchParams();
  params.set('limit', limit.toString());
  params.set('offset', offset.toString());
  if (status) params.set('status', status);

  return api.get<WithdrawalListResponse>(`/withdrawals?${params.toString()}`);
}

/**
 * Get a specific withdrawal request
 *
 * @param id - Withdrawal request ID
 * @returns Withdrawal request details
 */
export async function getWithdrawal(id: number): Promise<WithdrawalRequest> {
  return api.get<WithdrawalRequest>(`/withdrawals/${id}`);
}

/**
 * Cancel a pending withdrawal request
 *
 * @param id - Withdrawal request ID
 * @returns Success message
 */
export async function cancelWithdrawal(
  id: number
): Promise<{ message: string; id: number }> {
  return api.delete<{ message: string; id: number }>(`/withdrawals/${id}`);
}
