/**
 * Base API client for Pravda Market
 * Handles Telegram authentication and HTTP requests
 */

import { initData } from '@tma.js/sdk-react';
import type { ErrorResponse } from '@/types/api';

// API base URL - configure based on environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Default request timeout (30 seconds)
const DEFAULT_TIMEOUT = 30000;

/**
 * API Error class
 */
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: ErrorResponse,
    public isRetryable: boolean = false
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Check if error is retryable
 */
function isRetryableError(error: unknown): boolean {
  if (error instanceof APIError) {
    // Retry on network errors (status 0)
    if (error.status === 0) return true;

    // Retry on server errors (5xx)
    if (error.status >= 500 && error.status < 600) return true;

    // Retry on rate limiting
    if (error.status === 429) return true;

    return false;
  }

  // Retry on network errors
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return true;
  }

  return false;
}

/**
 * Sleep with jitter for exponential backoff
 */
async function sleep(ms: number): Promise<void> {
  // Add random jitter (0-25% of delay) to prevent thundering herd
  const jitter = Math.random() * ms * 0.25;
  await new Promise(resolve => setTimeout(resolve, ms + jitter));
}

/**
 * Get Telegram initData for authentication
 */
function getTelegramInitData(): string | null {
  try {
    // Get the raw init data string from Telegram WebApp
    const rawInitData = initData.raw();
    if (rawInitData && typeof rawInitData === 'string') {
      return rawInitData;
    }
    return null;
  } catch (error) {
    console.warn('Failed to get Telegram initData:', error);
    return null;
  }
}

/**
 * Make an authenticated API request (internal, no retry)
 */
async function requestOnce<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_TIMEOUT
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Add Telegram authentication header
  const telegramInitData = getTelegramInitData();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Merge existing headers
  if (options.headers) {
    Object.entries(options.headers).forEach(([key, value]) => {
      if (typeof value === 'string') {
        headers[key] = value;
      }
    });
  }

  if (telegramInitData) {
    headers['Authorization'] = `twa ${telegramInitData}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    // Handle error responses
    if (!response.ok) {
      let errorData: ErrorResponse | undefined;
      try {
        errorData = await response.json();
      } catch {
        // Response body is not JSON
      }

      const isRetryable = response.status >= 500 || response.status === 429;

      throw new APIError(
        errorData?.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData,
        isRetryable
      );
    }

    // Parse successful response
    const data = await response.json();
    return data as T;
  } catch (error) {
    // Handle abort (timeout)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new APIError(
        'Request timeout - please try again',
        0,
        undefined,
        true
      );
    }

    if (error instanceof APIError) {
      throw error;
    }

    // Network or other errors (always retryable)
    throw new APIError(
      error instanceof Error ? error.message : 'Network request failed',
      0,
      undefined,
      true
    );
  } finally {
    // Always clear timeout
    clearTimeout(timeoutId);
  }
}

/**
 * Make an authenticated API request with retry logic
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  config?: {
    maxRetries?: number;
    timeoutMs?: number;
  }
): Promise<T> {
  const maxRetries = config?.maxRetries ?? 3;
  const timeoutMs = config?.timeoutMs ?? DEFAULT_TIMEOUT;

  let lastError: APIError | null = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await requestOnce<T>(endpoint, options, timeoutMs);
    } catch (error) {
      lastError = error instanceof APIError
        ? error
        : new APIError('Unknown error', 0, undefined, false);

      // Don't retry if error is not retryable
      if (!isRetryableError(error)) {
        throw lastError;
      }

      // Don't retry on last attempt
      if (attempt === maxRetries - 1) {
        throw lastError;
      }

      // Calculate backoff delay: 1s, 2s, 4s, etc.
      const baseDelay = 1000;
      const backoffDelay = baseDelay * Math.pow(2, attempt);

      console.warn(
        `Request failed (attempt ${attempt + 1}/${maxRetries}), retrying in ${backoffDelay}ms...`,
        lastError.message
      );

      await sleep(backoffDelay);
    }
  }

  // This should never happen, but TypeScript needs it
  throw lastError || new APIError('Request failed', 0);
}

/**
 * API client methods
 */
export const api = {
  /**
   * GET request
   */
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),

  /**
   * POST request
   */
  post: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  /**
   * PUT request
   */
  put: <T>(endpoint: string, data?: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  /**
   * DELETE request
   */
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
};
