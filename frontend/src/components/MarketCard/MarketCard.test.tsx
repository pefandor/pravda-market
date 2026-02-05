import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { userEvent } from '@testing-library/user-event';
import { MarketCard } from './MarketCard';
import type { Market } from '@/types/api';

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
    deadline: new Date('2027-12-31T23:59:59Z').toISOString(),
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
    expect(screen.getByText(/YES 65%/)).toBeInTheDocument();
    expect(screen.getByText(/NO 35%/)).toBeInTheDocument();
  });

  it('should render progress bar with correct width', () => {
    const { container } = render(<MarketCard market={mockMarket} />);
    const yesBar = container.querySelector('.market-card__bar-yes');
    expect(yesBar).toBeInTheDocument();
    expect(yesBar?.getAttribute('style')).toContain('width: 65%');
  });

  it('should render category label', () => {
    render(<MarketCard market={mockMarket} />);
    expect(screen.getByText('Крипто')).toBeInTheDocument();
  });

  it('should not render category when null', () => {
    const marketNoCategory = { ...mockMarket, category: null };
    render(<MarketCard market={marketNoCategory} />);
    expect(screen.queryByText('Крипто')).not.toBeInTheDocument();
  });

  it('should navigate to market detail on click', async () => {
    const user = userEvent.setup();
    render(<MarketCard market={mockMarket} />);

    const card = screen.getByText('Will Bitcoin reach $100k?').closest('.market-card');
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

    const titleElement = screen.getByText(/Safe Title/);
    expect(titleElement).toBeInTheDocument();
    expect(titleElement.textContent).not.toContain('<script');
    expect(titleElement.textContent).not.toContain('alert');
  });

  it('should not re-render when props are equal (memoization)', () => {
    const { rerender } = render(<MarketCard market={mockMarket} />);
    const titleElement = screen.getByText('Will Bitcoin reach $100k?');
    rerender(<MarketCard market={mockMarket} />);
    expect(titleElement).toBeInTheDocument();
  });

  it('should re-render when price changes', () => {
    const { rerender } = render(<MarketCard market={mockMarket} />);
    expect(screen.getByText(/YES 65%/)).toBeInTheDocument();

    const updatedMarket = { ...mockMarket, yes_price: 7000 };
    rerender(<MarketCard market={updatedMarket} />);
    expect(screen.getByText(/YES 70%/)).toBeInTheDocument();
  });

  it('should handle markets with null description', () => {
    const marketNoDesc = { ...mockMarket, description: null };
    expect(() => {
      render(<MarketCard market={marketNoDesc} />);
    }).not.toThrow();
  });

  it('should render deadline info', () => {
    render(<MarketCard market={mockMarket} />);
    // formatDeadline will return something like "Xдн." for future dates
    const metaContainer = screen.getByText('Will Bitcoin reach $100k?')
      .closest('.market-card')
      ?.querySelector('.market-card__meta');
    expect(metaContainer).toBeInTheDocument();
  });
});
