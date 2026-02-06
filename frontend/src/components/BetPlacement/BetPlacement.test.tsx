/**
 * Component tests for BetPlacement
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/test-utils';
import { userEvent } from '@testing-library/user-event';
import { BetPlacement } from './BetPlacement';
import * as betsService from '@/services/bets';

// Mock the bets service
vi.mock('@/services/bets', () => ({
  placeBet: vi.fn(),
}));

describe('BetPlacement', () => {
  const mockOnSuccess = vi.fn();
  const marketId = 123;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render bet placement form', () => {
    render(<BetPlacement marketId={marketId} />);

    expect(screen.getByRole('button', { name: /Разместить ставку/ })).toBeInTheDocument();
    expect(screen.getByLabelText(/Цена/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Сумма/)).toBeInTheDocument();
    expect(screen.getByText('ДА')).toBeInTheDocument();
    expect(screen.getByText('НЕТ')).toBeInTheDocument();
  });

  it('should have default values (YES, 50%, 100₽)', () => {
    render(<BetPlacement marketId={marketId} />);

    const priceInput = screen.getByLabelText(/Цена/) as HTMLInputElement;
    const amountInput = screen.getByLabelText(/Сумма/) as HTMLInputElement;

    expect(priceInput.value).toBe('50');
    expect(amountInput.value).toBe('100');

    // YES should be selected by default (active state)
    const yesButton = screen.getByText('ДА');
    expect(yesButton.closest('button')).toHaveClass('bet-placement--active');
  });

  it('should switch between YES and NO', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const yesButton = screen.getByText('ДА');
    const noButton = screen.getByText('НЕТ');

    // Initially YES is selected
    expect(yesButton.closest('button')).toHaveClass('bet-placement--active');

    // Click NO
    await user.click(noButton);

    // Now NO should be selected
    expect(noButton.closest('button')).toHaveClass('bet-placement--active');
  });

  it('should validate price minimum (1%)', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const priceInput = screen.getByLabelText(/Цена/);

    // Enter invalid price (< 1)
    await user.clear(priceInput);
    await user.type(priceInput, '0');

    expect(screen.getByText('Минимум 1%')).toBeInTheDocument();
  });

  it('should validate price maximum (99%)', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const priceInput = screen.getByLabelText(/Цена/);

    // Enter invalid price (> 99)
    await user.clear(priceInput);
    await user.type(priceInput, '100');

    expect(screen.getByText('Максимум 99%')).toBeInTheDocument();
  });

  it('should validate amount minimum (10₽)', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const amountInput = screen.getByLabelText(/Сумма/);

    // Enter invalid amount (< 10)
    await user.clear(amountInput);
    await user.type(amountInput, '5');

    expect(screen.getByText('Минимум 10 ₽')).toBeInTheDocument();
  });

  it('should validate non-numeric price input', async () => {
    // Note: HTML5 input type="number" prevents non-numeric characters
    // This test verifies that empty input is handled
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const priceInput = screen.getByLabelText(/Цена/);
    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    // Clear input (becomes empty, which is invalid)
    await user.clear(priceInput);

    // Submit should be disabled for empty input
    expect(submitButton).toBeDisabled();
  });

  it('should disable submit button when form is invalid', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });
    const priceInput = screen.getByLabelText(/Цена/);

    // Enter invalid price
    await user.clear(priceInput);
    await user.type(priceInput, '0');

    expect(submitButton).toBeDisabled();
  });

  it('should enable submit button when form is valid', () => {
    render(<BetPlacement marketId={marketId} />);

    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    // Default values are valid (50%, 100₽)
    expect(submitButton).not.toBeDisabled();
  });

  it('should submit bet with correct data', async () => {
    const user = userEvent.setup();
    const mockPlaceBet = vi.mocked(betsService.placeBet);
    mockPlaceBet.mockResolvedValue({
      order_id: 456,
      message: 'Order placed successfully',
      matched_trades: [],
    });

    render(<BetPlacement marketId={marketId} onSuccess={mockOnSuccess} />);

    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    // Submit with default values
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockPlaceBet).toHaveBeenCalledWith({
        market_id: marketId,
        side: 'yes',
        price: 5000,  // 50% * 100 basis points
        amount: 10000, // 100₽ * 100 kopecks
      });
    });

    // Should call onSuccess callback
    expect(mockOnSuccess).toHaveBeenCalled();

    // Should show success message
    expect(screen.getByText(/Ставка размещена/)).toBeInTheDocument();
  });

  it('should handle bet placement error', async () => {
    const user = userEvent.setup();
    const mockPlaceBet = vi.mocked(betsService.placeBet);
    mockPlaceBet.mockRejectedValue(new Error('Insufficient funds'));

    render(<BetPlacement marketId={marketId} />);

    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Insufficient funds/)).toBeInTheDocument();
    });
  });

  it('should show loading state during submission', async () => {
    const user = userEvent.setup();
    const mockPlaceBet = vi.mocked(betsService.placeBet);

    // Mock slow API call
    mockPlaceBet.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        order_id: 456,
        message: 'Order placed successfully',
        matched_trades: [],
      }), 100))
    );

    render(<BetPlacement marketId={marketId} />);

    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    await user.click(submitButton);

    // Button should be disabled during loading
    expect(submitButton).toBeDisabled();
  });

  it('should reset amount after successful submission', async () => {
    const user = userEvent.setup();
    const mockPlaceBet = vi.mocked(betsService.placeBet);
    mockPlaceBet.mockResolvedValue({
      order_id: 456,
      message: 'Order placed successfully',
      matched_trades: [],
    });

    render(<BetPlacement marketId={marketId} />);

    const amountInput = screen.getByLabelText(/Сумма/) as HTMLInputElement;
    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    // Change amount
    await user.clear(amountInput);
    await user.type(amountInput, '500');

    // Submit
    await user.click(submitButton);

    await waitFor(() => {
      // Should reset to 100
      expect(amountInput.value).toBe('100');
    });
  });

  it('should accept decimal prices', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const priceInput = screen.getByLabelText(/Цена/);
    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    await user.clear(priceInput);
    await user.type(priceInput, '65.5');

    // Should not show price validation errors
    expect(screen.queryByText('Введите число')).not.toBeInTheDocument();
    expect(screen.queryByText('Минимум 1%')).not.toBeInTheDocument();
    expect(screen.queryByText('Максимум 99%')).not.toBeInTheDocument();

    // Submit should be enabled for valid decimal price
    expect(submitButton).not.toBeDisabled();
  });

  it('should disable submit when price field is empty', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const priceInput = screen.getByLabelText(/Цена/);
    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    await user.clear(priceInput);

    expect(submitButton).toBeDisabled();
  });

  it('should disable submit when amount field is empty', async () => {
    const user = userEvent.setup();
    render(<BetPlacement marketId={marketId} />);

    const amountInput = screen.getByLabelText(/Сумма/);
    const submitButton = screen.getByRole('button', { name: /Разместить ставку/ });

    await user.clear(amountInput);

    expect(submitButton).toBeDisabled();
  });
});
