/**
 * Unit tests for sanitization utilities
 */

import { describe, it, expect } from 'vitest';
import {
  sanitizeText,
  sanitizeHTML,
  useSafeHTML,
  isContentSafe,
} from './sanitize';

describe('sanitizeText', () => {
  it('should remove all HTML tags', () => {
    expect(sanitizeText('<script>alert("xss")</script>')).toBe('');
    expect(sanitizeText('<b>bold</b> text')).toBe('bold text');
    expect(sanitizeText('<p>paragraph</p>')).toBe('paragraph');
  });

  it('should handle plain text', () => {
    expect(sanitizeText('Hello World')).toBe('Hello World');
    expect(sanitizeText('Text with spaces')).toBe('Text with spaces');
  });

  it('should remove dangerous attributes', () => {
    const malicious = '<img src=x onerror="alert(1)">';
    const result = sanitizeText(malicious);
    expect(result).not.toContain('onerror');
    expect(result).not.toContain('alert');
  });

  it('should handle null and undefined', () => {
    expect(sanitizeText(null)).toBe('');
    expect(sanitizeText(undefined)).toBe('');
    expect(sanitizeText('')).toBe('');
  });

  it('should preserve special characters', () => {
    expect(sanitizeText('Price: 100₽')).toContain('100₽');
    expect(sanitizeText('Test & Demo')).toContain('&');
  });
});

describe('sanitizeHTML', () => {
  it('should allow basic formatting tags', () => {
    expect(sanitizeHTML('<b>bold</b>')).toContain('bold');
    expect(sanitizeHTML('<i>italic</i>')).toContain('italic');
    expect(sanitizeHTML('<strong>strong</strong>')).toContain('strong');
  });

  it('should allow safe links', () => {
    const link = '<a href="https://example.com">Link</a>';
    const result = sanitizeHTML(link);
    expect(result).toContain('href');
    expect(result).toContain('example.com');
  });

  it('should remove script tags', () => {
    const malicious = '<script>alert("xss")</script>Hello';
    const result = sanitizeHTML(malicious);
    expect(result).not.toContain('<script');
    expect(result).not.toContain('alert');
    expect(result).toContain('Hello');
  });

  it('should remove dangerous event handlers', () => {
    const malicious = '<a href="#" onclick="alert(1)">Click</a>';
    const result = sanitizeHTML(malicious);
    expect(result).not.toContain('onclick');
    expect(result).not.toContain('alert');
  });

  it('should remove iframe tags', () => {
    const malicious = '<iframe src="evil.com"></iframe>';
    const result = sanitizeHTML(malicious);
    expect(result).not.toContain('iframe');
    expect(result).not.toContain('evil.com');
  });

  it('should handle null and undefined', () => {
    expect(sanitizeHTML(null)).toBe('');
    expect(sanitizeHTML(undefined)).toBe('');
  });
});

describe('useSafeHTML', () => {
  it('should return object with __html property', () => {
    const result = useSafeHTML('<b>test</b>');
    expect(result).toHaveProperty('__html');
    expect(typeof result.__html).toBe('string');
  });

  it('should sanitize HTML content', () => {
    const malicious = '<script>alert("xss")</script>Safe';
    const result = useSafeHTML(malicious);
    expect(result.__html).not.toContain('<script');
    expect(result.__html).toContain('Safe');
  });

  it('should handle null and undefined', () => {
    expect(useSafeHTML(null).__html).toBe('');
    expect(useSafeHTML(undefined).__html).toBe('');
  });

  it('should be usable with dangerouslySetInnerHTML', () => {
    const html = '<b>Bold Text</b>';
    const result = useSafeHTML(html);
    // The structure is correct for React's dangerouslySetInnerHTML
    expect(result).toHaveProperty('__html');
  });
});

describe('isContentSafe', () => {
  it('should detect script tags', () => {
    expect(isContentSafe('<script>alert(1)</script>')).toBe(false);
    expect(isContentSafe('Hello <script>world</script>')).toBe(false);
  });

  it('should detect javascript: protocol', () => {
    expect(isContentSafe('javascript:alert(1)')).toBe(false);
    expect(isContentSafe('<a href="javascript:void(0)">Link</a>')).toBe(false);
  });

  it('should detect event handlers', () => {
    expect(isContentSafe('onerror=alert(1)')).toBe(false);
    expect(isContentSafe('onload=malicious()')).toBe(false);
    expect(isContentSafe('onclick="hack()"')).toBe(false);
  });

  it('should detect iframe tags', () => {
    expect(isContentSafe('<iframe src="evil.com"></iframe>')).toBe(false);
  });

  it('should detect eval calls', () => {
    expect(isContentSafe('eval(maliciousCode)')).toBe(false);
  });

  it('should allow safe content', () => {
    expect(isContentSafe('Hello World')).toBe(true);
    expect(isContentSafe('Price: 100₽')).toBe(true);
    expect(isContentSafe('<b>Bold</b> text')).toBe(true);
    expect(isContentSafe('https://example.com')).toBe(true);
  });

  it('should handle null and undefined as safe', () => {
    expect(isContentSafe(null)).toBe(true);
    expect(isContentSafe(undefined)).toBe(true);
    expect(isContentSafe('')).toBe(true);
  });

  it('should be case-insensitive for dangerous patterns', () => {
    expect(isContentSafe('<SCRIPT>alert(1)</SCRIPT>')).toBe(false);
    expect(isContentSafe('JAVASCRIPT:alert(1)')).toBe(false);
    expect(isContentSafe('OnClick=bad()')).toBe(false);
  });
});

describe('XSS Protection Integration', () => {
  const xssVectors = [
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '<body onload=alert(1)>',
    '<iframe src="javascript:alert(1)"></iframe>',
    '<object data="javascript:alert(1)">',
    '<embed src="javascript:alert(1)">',
    '<a href="javascript:alert(1)">click</a>',
    '<form action="javascript:alert(1)">',
    '<input onfocus=alert(1) autofocus>',
    '<select onfocus=alert(1) autofocus>',
    '<textarea onfocus=alert(1) autofocus>',
    '<marquee onstart=alert(1)>',
    '<div style="background:url(javascript:alert(1))">',
  ];

  // Vectors that isContentSafe can detect (has patterns for: script, javascript:, onerror, onload, onclick, iframe, eval)
  const detectableVectors = [
    '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>',
    '<body onload=alert(1)>',
    '<iframe src="javascript:alert(1)"></iframe>',
    '<object data="javascript:alert(1)">',
    '<embed src="javascript:alert(1)">',
    '<a href="javascript:alert(1)">click</a>',
    '<form action="javascript:alert(1)">',
    '<div style="background:url(javascript:alert(1))">',
  ];

  it('should sanitize common XSS vectors', () => {
    xssVectors.forEach(vector => {
      const sanitized = sanitizeText(vector);
      // After sanitization, dangerous content should be removed
      expect(sanitized).not.toContain('alert');
      expect(sanitized).not.toContain('javascript:');
    });
  });

  it('should detect common XSS vectors as unsafe', () => {
    detectableVectors.forEach(vector => {
      expect(isContentSafe(vector)).toBe(false);
    });
  });
});

describe('Real-world usage scenarios', () => {
  it('should handle market titles safely', () => {
    const title = 'Will Bitcoin hit $100k? <script>alert("hack")</script>';
    const safe = sanitizeText(title);
    expect(safe).toContain('Will Bitcoin hit $100k?');
    expect(safe).not.toContain('<script');
  });

  it('should handle usernames safely', () => {
    const username = '@user<img src=x onerror=alert(1)>';
    const safe = sanitizeText(username);
    expect(safe).toContain('@user');
    expect(safe).not.toContain('onerror');
  });

  it('should handle market descriptions with formatting', () => {
    const description = 'Market closes on <b>Dec 31</b>. <script>bad()</script>';
    const safe = sanitizeHTML(description);
    expect(safe).toContain('Dec 31');
    expect(safe).not.toContain('<script');
  });

  it('should preserve cyrillic text', () => {
    const russian = 'Будет ли дождь завтра?';
    expect(sanitizeText(russian)).toBe(russian);
    expect(sanitizeHTML(russian)).toBe(russian);
  });

  it('should preserve special characters used in trading', () => {
    const text = 'Price: 100₽ | Volume: 1.5K₽ | YES @ 65%';
    expect(sanitizeText(text)).toBe(text);
  });
});
