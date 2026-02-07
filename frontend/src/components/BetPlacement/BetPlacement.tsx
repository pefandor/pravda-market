/**
 * BetPlacement component - Premium betting UI
 * Modern fintech-style form for placing bets
 */

import { FC, useState, useCallback, useEffect, useMemo } from 'react';
import { Section } from '@telegram-apps/telegram-ui';
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
const QUICK_AMOUNTS = [10, 50, 100];

export const BetPlacement: FC<BetPlacementProps> = ({ marketId, onSuccess }) => {
  const [side, setSide] = useState<Side>('yes');
  const [price, setPrice] = useState<number>(50);
  const [amount, setAmount] = useState<number>(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Auto-dismiss success message after 3 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  // Handle price slider change
  const handlePriceChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setPrice(parseInt(e.target.value) || 50);
  }, []);

  // Handle amount input change
  const handleAmountChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/[^\d]/g, '');
    setAmount(parseInt(value) || 0);
  }, []);

  // Quick amount buttons
  const handleQuickAmount = useCallback((delta: number) => {
    setAmount(prev => Math.max(MIN_AMOUNT, prev + delta));
  }, []);

  // MAX button - set to a reasonable max (could be user balance in future)
  const handleMaxAmount = useCallback(() => {
    setAmount(1000);
  }, []);

  // Check if form is valid
  const isFormValid = useMemo(() => {
    return price >= MIN_PRICE && price <= MAX_PRICE && amount >= MIN_AMOUNT;
  }, [price, amount]);

  // Calculate potential profit and multiplier
  const { potentialProfit, multiplier, winChance } = useMemo(() => {
    if (price <= 0 || amount <= 0) {
      return { potentialProfit: 0, multiplier: 0, winChance: 0 };
    }

    const priceDecimal = price / 100;
    const mult = 1 / priceDecimal;
    const profit = amount * mult - amount;

    return {
      potentialProfit: profit,
      multiplier: mult,
      winChance: price,
    };
  }, [price, amount]);

  const handleSubmit = useCallback(async () => {
    if (!isFormValid || loading) return;

    try {
      setLoading(true);
      setError(null);
      setSuccess(false);

      const priceDecimal = price / 100;

      await placeBet({
        market_id: marketId,
        side,
        price: priceDecimal,
        amount: amount,
      });

      setSuccess(true);
      setAmount(100);
      onSuccess?.();
    } catch (err) {
      console.error('Failed to place bet:', err);
      setError(err instanceof Error ? err.message : 'Не удалось разместить ставку');
    } finally {
      setLoading(false);
    }
  }, [price, amount, marketId, side, isFormValid, loading, onSuccess]);

  return (
    <div className={b()}>
      <Section header="Разместить ставку">
        <div className={b('form')}>
          {/* Side Selection - YES/NO */}
          <div className={b('sides')}>
            <button
              type="button"
              className={b('side-btn', { yes: true, active: side === 'yes' })}
              onClick={() => setSide('yes')}
            >
              <span className={b('side-icon')}>↑</span>
              <span className={b('side-text')}>ДА</span>
            </button>
            <button
              type="button"
              className={b('side-btn', { no: true, active: side === 'no' })}
              onClick={() => setSide('no')}
            >
              <span className={b('side-icon')}>↓</span>
              <span className={b('side-text')}>НЕТ</span>
            </button>
          </div>

          {/* Price Slider */}
          <div className={b('price-section')}>
            <label className={b('label')}>Цена</label>
            <div className={b('slider-wrapper')}>
              <div className={b('slider-badge', side)}>
                {price}%
              </div>
              <div className={b('slider-container')}>
                <div className={b('slider-track')}>
                  <div
                    className={b('slider-fill', side)}
                    style={{ width: `${price}%` }}
                  />
                </div>
                <input
                  type="range"
                  className={b('slider', side)}
                  value={price}
                  onChange={handlePriceChange}
                  min={MIN_PRICE}
                  max={MAX_PRICE}
                  step="1"
                />
              </div>
              <div className={b('slider-labels')}>
                <span>1%</span>
                <span>50%</span>
                <span>99%</span>
              </div>
            </div>
          </div>

          {/* Amount Input with Quick Buttons */}
          <div className={b('amount-section')}>
            <label className={b('label')}>Сумма</label>
            <div className={b('amount-input-wrapper')}>
              <span className={b('amount-icon')}>₽</span>
              <input
                type="text"
                inputMode="numeric"
                className={b('amount-input')}
                value={amount || ''}
                onChange={handleAmountChange}
                placeholder="100"
              />
            </div>
            <div className={b('quick-amounts')}>
              {QUICK_AMOUNTS.map(val => (
                <button
                  key={val}
                  type="button"
                  className={b('quick-btn')}
                  onClick={() => handleQuickAmount(val)}
                >
                  +{val}
                </button>
              ))}
              <button
                type="button"
                className={b('quick-btn', 'max')}
                onClick={handleMaxAmount}
              >
                MAX
              </button>
            </div>
            <span className={b('amount-hint')}>Минимум {MIN_AMOUNT} ₽</span>
          </div>

          {/* Profit Calculator Card */}
          {isFormValid && potentialProfit > 0 && (
            <div className={b('profit-card', side)}>
              <div className={b('profit-main')}>
                <span className={b('profit-label')}>При выигрыше</span>
                <span className={b('profit-value')}>+{potentialProfit.toFixed(0)} ₽</span>
                <span className={b('profit-chance')}>Шанс: {winChance}%</span>
              </div>
              <div className={b('profit-multiplier')}>
                <span className={b('multiplier-value')}>x{multiplier.toFixed(2)}</span>
              </div>
            </div>
          )}

          {/* Error message */}
          {error && <div className={b('error')}>{error}</div>}

          {/* Success message */}
          {success && (
            <div className={b('success')}>
              Ставка размещена!
            </div>
          )}

          {/* Submit Button */}
          <button
            type="button"
            className={b('submit', { [side]: true, disabled: !isFormValid || loading })}
            onClick={handleSubmit}
            disabled={!isFormValid || loading}
          >
            {loading ? (
              <span className={b('submit-loading')}>Размещение...</span>
            ) : (
              <>
                Поставить {amount} ₽ на {side === 'yes' ? 'ДА' : 'НЕТ'}
              </>
            )}
          </button>
        </div>
      </Section>
    </div>
  );
};
