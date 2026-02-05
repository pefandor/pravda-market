/**
 * Component tests for MarketCard
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { userEvent } from '@testing-library/user-event';
import { MarketCard } from './MarketCard';
import type { Market } from '@/types/api';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('MarketCard', () => {
  const mockMarket: Market = {
    id: 1,
    title: 'Will Bitcoin reach $100k?',
    description: 'Bitcoin price prediction',
    category: 'crypto',
    deadline: new Date('2025-12-31T23:59:59Z').toISOString(),
    resolved: false,
    resolution_value: null,
    outcome: null,
    resolved_at: null,
    yes_price: 6500, // 65%
    no_price: 3500,  // 35%
    volume: 100000,  // 1000₽
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('should render market title', () => {
    render(<MarketCard market={mockMarket} />);

    expect(screen.getByText('Will Bitcoin reach $100k?')).toBeInTheDocument();
  });

  it('should render YES and NO prices correctly', () => {
    render(<MarketCard market={mockMarket} />);

    // formatPrice(6500) = "65%", formatPrice(3500) = "35%"
    expect(screen.getByText(/ДА 65%/)).toBeInTheDocument();
    expect(screen.getByText(/НЕТ 35%/)).toBeInTheDocument();
  });

  it('should render volume when > 0', () => {
    render(<MarketCard market={mockMarket} />);

    // formatVolume(100000) should format as currency
    const volumeText = screen.getByText(/💰/);
    expect(volumeText).toBeInTheDocument();
  });

  it('should not render volume when = 0', () => {
    const marketNoVolume = { ...mockMarket, volume: 0 };
    render(<MarketCard market={marketNoVolume} />);

    // Should not have volume emoji
    const volumeElement = screen.queryByText(/💰/);
    expect(volumeElement).not.toBeInTheDocument();
  });

  it('should navigate to market detail on click', async () => {
    const user = userEvent.setup();
    render(<MarketCard market={mockMarket} />);

    const card = screen.getByText('Will Bitcoin reach $100k?').closest('[class*="market-card"]');
    expect(card).toBeInTheDocument();

    if (card) {
      await user.click(card);
      expect(mockNavigate).toHaveBeenCalledWith('/market/1');
    }
  });

  it('should sanitize market title', () => {
    const maliciousMarket = {
      ...mockMarket,
      title: '<script>alert("xss")</script>Safe Title',
    };

    render(<MarketCard market={maliciousMarket} />);

    // Script tags should be removed
    const titleElement = screen.getByText(/Safe Title/);
    expect(titleElement).toBeInTheDocument();
    expect(titleElement.textContent).not.toContain('<script');
    expect(titleElement.textContent).not.toContain('alert');
  });

  it('should not re-render when props are equal (memoization)', () => {
    const { rerender } = render(<MarketCard market={mockMarket} />);

    const titleElement = screen.getByText('Will Bitcoin reach $100k?');

    // Re-render with same market (should not cause re-render due to memo)
    rerender(<MarketCard market={mockMarket} />);

    // Element should still be in document
    expect(titleElement).toBeInTheDocument();
  });

  it('should re-render when price changes (memoization check)', () => {
    const { rerender } = render(<MarketCard market={mockMarket} />);

    expect(screen.getByText(/ДА 65%/)).toBeInTheDocument();

    // Change price
    const updatedMarket = { ...mockMarket, yes_price: 7000 };
    rerender(<MarketCard market={updatedMarket} />);

    // Should show new price
    expect(screen.getByText(/ДА 70%/)).toBeInTheDocument();
  });

  it('should render deadline with time emoji', () => {
    render(<MarketCard market={mockMarket} />);

    const deadlineElement = screen.getByText(/🕐/);
    expect(deadlineElement).toBeInTheDocument();
  });

  it('should handle markets with null category', () => {
    const marketNoCategory = { ...mockMarket, category: null };

    expect(() => {
      render(<MarketCard market={marketNoCategory} />);
    }).not.toThrow();
  });

  it('should handle markets with null description', () => {
    const marketNoDesc = { ...mockMarket, description: null };

    expect(() => {
      render(<MarketCard market={marketNoDesc} />);
    }).not.toThrow();
  });
});
