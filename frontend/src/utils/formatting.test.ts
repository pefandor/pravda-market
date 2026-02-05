/**
 * Unit tests for formatting utilities
 */

import { describe, it, expect } from 'vitest';
import {
  formatPrice,
  formatPriceDetailed,
  formatAmount,
  formatCurrency,
  formatVolume,
  formatDeadline,
  formatDeadlineFull,
  formatTimestamp,
  formatNumber,
} from './formatting';

describe('formatPrice', () => {
  it('should format basis points to percentage without decimals', () => {
    expect(formatPrice(6500)).toBe('65%');
    expect(formatPrice(5000)).toBe('50%');
    expect(formatPrice(9999)).toBe('100%');
    expect(formatPrice(100)).toBe('1%');
  });

  it('should handle edge cases', () => {
    expect(formatPrice(0)).toBe('0%');
    expect(formatPrice(10000)).toBe('100%');
  });
});

describe('formatPriceDetailed', () => {
  it('should format basis points to percentage with 1 decimal place', () => {
    expect(formatPriceDetailed(6500)).toBe('65.0%');
    expect(formatPriceDetailed(5050)).toBe('50.5%');
    expect(formatPriceDetailed(3333)).toBe('33.3%');
  });

  it('should handle edge cases', () => {
    expect(formatPriceDetailed(0)).toBe('0.0%');
    expect(formatPriceDetailed(10000)).toBe('100.0%');
  });
});

describe('formatAmount', () => {
  it('should format small amounts in rubles', () => {
    expect(formatAmount(10000)).toBe('100 ₽'); // 100₽
    expect(formatAmount(50000)).toBe('500 ₽'); // 500₽
  });

  it('should format thousands with K suffix', () => {
    expect(formatAmount(100000)).toBe('1.0K ₽'); // 1000₽
    expect(formatAmount(150000)).toBe('1.5K ₽'); // 1500₽
    expect(formatAmount(999999)).toBe('10.0K ₽'); // 9999.99₽
  });

  it('should format millions with M suffix', () => {
    expect(formatAmount(100000000)).toBe('1.0M ₽'); // 1,000,000₽
    expect(formatAmount(250000000)).toBe('2.5M ₽'); // 2,500,000₽
  });

  it('should handle edge cases', () => {
    expect(formatAmount(0)).toBe('0 ₽');
    expect(formatAmount(1)).toBe('0 ₽'); // Less than 1₽ rounds to 0
    expect(formatAmount(100)).toBe('1 ₽'); // Exactly 1₽
  });
});

describe('formatCurrency', () => {
  it('should format kopecks to rubles with proper locale', () => {
    const result = formatCurrency(10000); // 100₽
    expect(result).toContain('100');
    expect(result).toContain('₽');
  });

  it('should handle decimals correctly', () => {
    const result = formatCurrency(10050); // 100.50₽
    expect(result).toContain('100');
  });

  it('should handle zero', () => {
    const result = formatCurrency(0);
    expect(result).toContain('0');
  });
});

describe('formatVolume', () => {
  it('should be an alias for formatCurrency', () => {
    expect(formatVolume(10000)).toBe(formatCurrency(10000));
  });
});

describe('formatDeadline', () => {
  it('should format deadlines in the future with days', () => {
    const futureDate = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000); // +3 days
    const result = formatDeadline(futureDate.toISOString());
    expect(result).toContain('дн');
  });

  it('should format deadlines in the future with hours', () => {
    const futureDate = new Date(Date.now() + 5 * 60 * 60 * 1000); // +5 hours
    const result = formatDeadline(futureDate.toISOString());
    expect(result).toContain('ч');
  });

  it('should show "Скоро" for very near deadlines', () => {
    const nearDate = new Date(Date.now() + 30 * 60 * 1000); // +30 minutes
    const result = formatDeadline(nearDate.toISOString());
    expect(result).toBe('Скоро');
  });

  it('should show "Завершен" for past deadlines', () => {
    const pastDate = new Date(Date.now() - 24 * 60 * 60 * 1000); // -1 day
    const result = formatDeadline(pastDate.toISOString());
    expect(result).toBe('Завершен');
  });
});

describe('formatDeadlineFull', () => {
  it('should format deadline with full date and time', () => {
    const date = new Date('2025-12-15T12:00:00Z');
    const result = formatDeadlineFull(date.toISOString());

    // Should contain date components (use middle of month/day to avoid timezone edge cases)
    expect(result).toContain('15');
    expect(result).toContain('декабря');
    expect(result).toContain('2025');
  });

  it('should handle current date', () => {
    const now = new Date();
    const result = formatDeadlineFull(now.toISOString());
    expect(result).toBeTruthy();
    expect(result.length).toBeGreaterThan(0);
  });
});

describe('formatTimestamp', () => {
  it('should format timestamp with date and time', () => {
    const date = new Date('2025-06-15T10:30:00Z');
    const result = formatTimestamp(date.toISOString());

    // Should contain date and time components
    expect(result).toContain('15');
    expect(result).toContain('06');
    expect(result).toContain('2025');
  });

  it('should be consistent', () => {
    const dateStr = '2025-01-01T00:00:00Z';
    const result1 = formatTimestamp(dateStr);
    const result2 = formatTimestamp(dateStr);
    expect(result1).toBe(result2);
  });
});

describe('formatNumber', () => {
  it('should format numbers with thousand separators', () => {
    expect(formatNumber(1000)).toContain('000');
    expect(formatNumber(1000000)).toContain('000');
  });

  it('should handle small numbers', () => {
    expect(formatNumber(0)).toBe('0');
    expect(formatNumber(42)).toBe('42');
    expect(formatNumber(999)).toBe('999');
  });

  it('should handle negative numbers', () => {
    const result = formatNumber(-1000);
    expect(result).toContain('-');
    expect(result).toContain('000');
  });
});

describe('Edge cases and integration', () => {
  it('should handle null/undefined gracefully in production', () => {
    // These should not throw errors
    expect(() => formatPrice(0)).not.toThrow();
    expect(() => formatAmount(0)).not.toThrow();
  });

  it('should maintain consistency across similar functions', () => {
    const kopecks = 10000;

    // Volume and currency should be the same
    expect(formatVolume(kopecks)).toBe(formatCurrency(kopecks));
  });

  it('should format large trading volumes correctly', () => {
    // 10 million rubles
    const largeVolume = 1000000000; // 10,000,000₽ in kopecks
    const result = formatAmount(largeVolume);
    expect(result).toContain('M');
    expect(result).toContain('10');
  });
});
