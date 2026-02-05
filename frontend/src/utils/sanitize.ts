/**
 * Sanitization utilities for user-generated content
 * Protects against XSS attacks using DOMPurify
 */

import DOMPurify from 'dompurify';

/**
 * Sanitize configuration for different contexts
 */
const SANITIZE_CONFIG = {
  // Strict: plain text only (removes all HTML)
  plainText: {
    ALLOWED_TAGS: [] as string[],
    ALLOWED_ATTR: [] as string[],
    KEEP_CONTENT: true,
  },

  // Basic: allows simple formatting (bold, italic, links)
  basic: {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'br'],
    ALLOWED_ATTR: ['href', 'target', 'rel'],
    ALLOW_DATA_ATTR: false,
  },
};

/**
 * Sanitize user-generated text (removes all HTML)
 * Use for: usernames, market titles, simple descriptions
 */
export function sanitizeText(text: string | null | undefined): string {
  if (!text) return '';
  return DOMPurify.sanitize(text, SANITIZE_CONFIG.plainText);
}

/**
 * Sanitize HTML with basic formatting allowed
 * Use for: market descriptions with formatting
 */
export function sanitizeHTML(html: string | null | undefined): string {
  if (!html) return '';
  return DOMPurify.sanitize(html, SANITIZE_CONFIG.basic);
}

/**
 * React hook for safe HTML rendering with dangerouslySetInnerHTML
 * Returns sanitized HTML object ready for React
 */
export function useSafeHTML(html: string | null | undefined): { __html: string } {
  return { __html: sanitizeHTML(html) };
}

/**
 * Validate that string doesn't contain potential XSS patterns
 * Returns true if safe, false if suspicious
 */
export function isContentSafe(content: string | null | undefined): boolean {
  if (!content) return true;

  // Check for common XSS patterns
  const dangerousPatterns = [
    /<script/i,
    /javascript:/i,
    /onerror=/i,
    /onload=/i,
    /onclick=/i,
    /<iframe/i,
    /eval\(/i,
  ];

  return !dangerousPatterns.some(pattern => pattern.test(content));
}
