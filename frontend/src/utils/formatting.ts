/**
 * Formatting utilities
 * Centralized formatting functions for prices, amounts, dates, etc.
 */

/**
 * Format price from basis points to percentage
 * @param basisPoints - Price in basis points (0-10000, where 5000 = 50%)
 * @returns Formatted percentage string (e.g., "50%")
 */
export function formatPrice(basisPoints: number): string {
  return `${(basisPoints / 100).toFixed(0)}%`;
}

/**
 * Format price with decimal places
 * @param basisPoints - Price in basis points
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted percentage string (e.g., "50.5%")
 */
export function formatPriceDetailed(basisPoints: number, decimals: number = 1): string {
  return `${(basisPoints / 100).toFixed(decimals)}%`;
}

/**
 * Format amount from kopecks to rubles
 * @param kopecks - Amount in kopecks (1 ruble = 100 kopecks)
 * @returns Formatted amount string (e.g., "100 ₽", "1.5K ₽", "2.3M ₽")
 */
export function formatAmount(kopecks: number): string {
  const rubles = kopecks / 100;

  if (rubles >= 1_000_000) {
    return `${(rubles / 1_000_000).toFixed(1)}M ₽`;
  }

  if (rubles >= 1_000) {
    return `${(rubles / 1_000).toFixed(1)}K ₽`;
  }

  return `${rubles.toFixed(0)} ₽`;
}

/**
 * Format amount as currency with full precision
 * @param kopecks - Amount in kopecks
 * @returns Formatted currency string (e.g., "1 234,56 ₽")
 */
export function formatCurrency(kopecks: number): string {
  const rubles = kopecks / 100;

  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
  }).format(rubles);
}

/**
 * Format volume (alias for formatCurrency for backwards compatibility)
 */
export function formatVolume(kopecks: number): string {
  return formatCurrency(kopecks);
}

/**
 * Format deadline as relative time
 * @param deadline - ISO date string
 * @returns Relative time string (e.g., "5 дн.", "12 ч.", "Скоро")
 */
export function formatDeadline(deadline: string): string {
  const date = new Date(deadline);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 1) {
    return `${diffDays} дн.`;
  }

  if (diffHours > 0) {
    return `${diffHours} ч.`;
  }

  if (diffMs > 0) {
    return 'Скоро';
  }

  return 'Завершен';
}

/**
 * Format deadline as full date
 * @param deadline - ISO date string
 * @returns Formatted date string (e.g., "5 февраля 2024, 15:30")
 */
export function formatDeadlineFull(deadline: string): string {
  const date = new Date(deadline);

  return date.toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format timestamp as date
 * @param timestamp - ISO date string
 * @returns Formatted date string (e.g., "05.02.2024, 15:30")
 */
export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);

  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format large numbers with separators
 * @param num - Number to format
 * @returns Formatted number string (e.g., "1 234 567")
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('ru-RU').format(num);
}
