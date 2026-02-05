/**
 * useCountdown - Real-time countdown timer hook
 *
 * Updates every second and formats as "145д 3ч 20м" or "45м 30с"
 */

import { useState, useEffect } from 'react';

interface CountdownResult {
  /** Formatted countdown string (e.g., "145д 3ч 20м") */
  formatted: string;
  /** Is deadline in the past? */
  isExpired: boolean;
  /** Is less than 1 hour remaining? */
  isUrgent: boolean;
  /** Total remaining milliseconds */
  totalMs: number;
}

/**
 * Parse deadline string to Date object
 */
function parseDeadline(deadline: string): Date {
  return new Date(deadline);
}

/**
 * Format the remaining time as a human-readable string
 */
function formatCountdown(ms: number): string {
  if (ms <= 0) {
    return 'Завершён';
  }

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  // Less than 1 hour: show minutes and seconds
  if (hours < 1) {
    const m = minutes;
    const s = seconds % 60;
    return `${m}м ${s}с`;
  }

  // Less than 1 day: show hours and minutes
  if (days < 1) {
    const h = hours;
    const m = minutes % 60;
    return `${h}ч ${m}м`;
  }

  // 1+ days: show days, hours, minutes
  const d = days;
  const h = hours % 24;
  const m = minutes % 60;
  return `${d}д ${h}ч ${m}м`;
}

/**
 * Hook that provides real-time countdown to a deadline
 *
 * @param deadline - ISO date string or Date object
 * @returns CountdownResult with formatted string and status flags
 */
export function useCountdown(deadline: string | Date): CountdownResult {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    // Update every second
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const deadlineDate = typeof deadline === 'string' ? parseDeadline(deadline) : deadline;
  const totalMs = deadlineDate.getTime() - now;
  const isExpired = totalMs <= 0;
  const isUrgent = totalMs > 0 && totalMs < 60 * 60 * 1000; // < 1 hour

  return {
    formatted: formatCountdown(totalMs),
    isExpired,
    isUrgent,
    totalMs,
  };
}
