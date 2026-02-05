/**
 * BetPlacement component
 * Form for placing bets on a market
 */

import { FC, useState, useCallback, useEffect, useMemo } from 'react';
import { Button, Input, Section } from '@telegram-apps/telegram-ui';
import type { Side } from '@/types/api';
import { placeBet } from '@/services/bets';
import { bem } from '@/css/bem';

import './BetPlacement.css';

const [b] = bem('bet-placement');

export interface BetPlacementProps {
  marketId: number;
  onSuccess?: () => void;
}

// Constants
const MIN_PRICE = 1;
const MAX_PRICE = 99;
const MIN_AMOUNT = 10;

export const BetPlacement: FC<BetPlacementProps> = ({ marketId, onSuccess }) => {
  const [side, setSide] = useState<Side>('yes');
  const [price, setPrice] = useState<string>('50');
  const [amount, setAmount] = useState<string>('100');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Validation state
  const [priceError, setPriceError] = useState<string | null>(null);
  const [amountError, setAmountError] = useState<string | null>(null);

  // Auto-dismiss success message after 3 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  // Validate price input
  const validatePrice = useCallback((value: string): string | null => {
    if (value === '') return null;

    const num = parseFloat(value);

    if (isNaN(num)) {
      return 'Введите число';
    }

    if (num < MIN_PRICE) {
      return `Минимум ${MIN_PRICE}%`;
    }

    if (num > MAX_PRICE) {
      return `Максимум ${MAX_PRICE}%`;
    }

    return null;
  }, []);

  // Validate amount input
  const validateAmount = useCallback((value: string): string | null => {
    if (value === '') return null;

    const num = parseFloat(value);

    if (isNaN(num)) {
      return 'Введите число';
    }

    if (num < MIN_AMOUNT) {
      return `Минимум ${MIN_AMOUNT} ₽`;
    }

    return null;
  }, []);

  // Handle price change with validation
  const handlePriceChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setPrice(value);
    setPriceError(validatePrice(value));
  }, [validatePrice]);

  // Handle amount change with validation
  const handleAmountChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setAmount(value);
    setAmountError(validateAmount(value));
  }, [validateAmount]);

  // Check if form is valid
  const isFormValid = useMemo(() => {
    if (price === '' || amount === '') return false;
    if (priceError || amountError) return false;

    const priceNum = parseFloat(price);
    const amountNum = parseFloat(amount);

    return (
      !isNaN(priceNum) &&
      priceNum >= MIN_PRICE &&
      priceNum <= MAX_PRICE &&
      !isNaN(amountNum) &&
      amountNum >= MIN_AMOUNT
    );
  }, [price, amount, priceError, amountError]);

  const handleSubmit = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(false);

      // Final validation (should already be valid)
      const priceNum = parseFloat(price);
      const amountNum = parseFloat(amount);

      if (!isFormValid) {
        setError('Проверьте правильность введенных данных');
        return;
      }

      // Convert to API format
      const priceBasisPoints = Math.round(priceNum * 100);
      const amountKopecks = Math.round(amountNum * 100);

      await placeBet({
        market_id: marketId,
        side,
        price: priceBasisPoints,
        amount: amountKopecks,
      });

      setSuccess(true);
      setAmount('100');
      setPriceError(null);
      setAmountError(null);
      onSuccess?.();
    } catch (err) {
      console.error('Failed to place bet:', err);
      setError(err instanceof Error ? err.message : 'Не удалось разместить ставку');
    } finally {
      setLoading(false);
    }
  }, [price, amount, marketId, side, isFormValid, onSuccess]);

  return (
    <div className={b()}>
      <Section header="Разместить ставку">
        <div className={b('form')}>
          {/* Side selection */}
          <div className={b('field')}>
            <label className={b('label')}>Выберите сторону</label>
            <div className={b('side-buttons')}>
              <Button
                className={b('side-button', { active: side === 'yes' })}
                mode={side === 'yes' ? 'filled' : 'outline'}
                onClick={() => setSide('yes')}
              >
                ДА
              </Button>
              <Button
                className={b('side-button', { active: side === 'no' })}
                mode={side === 'no' ? 'filled' : 'outline'}
                onClick={() => setSide('no')}
              >
                НЕТ
              </Button>
            </div>
          </div>

          {/* Price input */}
          <div className={b('field')}>
            <label className={b('label')} htmlFor="price-input">
              Цена (%)
            </label>
            <Input
              id="price-input"
              type="number"
              value={price}
              onChange={handlePriceChange}
              min={MIN_PRICE}
              max={MAX_PRICE}
              step="1"
              placeholder="50"
            />
            {priceError ? (
              <span className={b('hint', 'error')}>{priceError}</span>
            ) : (
              <span className={b('hint')}>Вероятность события (1-99%)</span>
            )}
          </div>

          {/* Amount input */}
          <div className={b('field')}>
            <label className={b('label')} htmlFor="amount-input">
              Сумма (₽)
            </label>
            <Input
              id="amount-input"
              type="number"
              value={amount}
              onChange={handleAmountChange}
              min={MIN_AMOUNT}
              step="10"
              placeholder="100"
            />
            {amountError ? (
              <span className={b('hint', 'error')}>{amountError}</span>
            ) : (
              <span className={b('hint')}>Минимум {MIN_AMOUNT} ₽</span>
            )}
          </div>

          {/* Error message */}
          {error && <div className={b('error')}>{error}</div>}

          {/* Success message */}
          {success && <div className={b('success')}>✅ Ставка размещена!</div>}

          {/* Submit button */}
          <Button
            className={b('submit')}
            size="l"
            stretched
            loading={loading}
            disabled={!isFormValid || loading}
            onClick={handleSubmit}
          >
            Разместить ставку
          </Button>
        </div>
      </Section>
    </div>
  );
};
