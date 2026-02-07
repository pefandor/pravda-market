/**
 * BetPlacement component - Modern Fintech UI
 * Binance/Polymarket style betting form
 */

import { FC, useState, useCallback, useEffect, useMemo } from 'react';
import type { Side } from '@/types/api';
import { placeBet } from '@/services/bets';

import './BetPlacement.css';

export interface BetPlacementProps {
  marketId: number;
  onSuccess?: () => void;
}

const MIN_AMOUNT = 10;

export const BetPlacement: FC<BetPlacementProps> = ({ marketId, onSuccess }) => {
  const [side, setSide] = useState<Side>('yes');
  const [price, setPrice] = useState<number>(50);
  const [amount, setAmount] = useState<number>(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Auto-dismiss messages
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const handlePriceChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setPrice(parseInt(e.target.value) || 50);
  }, []);

  const handleAmountChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/[^\d]/g, '');
    setAmount(parseInt(value) || 0);
  }, []);

  const canSubmit = useMemo(() => {
    return price >= 1 && price <= 99 && amount >= MIN_AMOUNT;
  }, [price, amount]);

  const { profit, multiplier } = useMemo(() => {
    if (price <= 0 || amount <= 0) {
      return { profit: 0, multiplier: 0 };
    }
    const mult = 1 / (price / 100);
    const prof = amount * mult - amount;
    return { profit: prof, multiplier: mult };
  }, [price, amount]);

  const handleSubmit = useCallback(async () => {
    if (!canSubmit || loading) return;

    try {
      setLoading(true);
      setError(null);

      await placeBet({
        market_id: marketId,
        side,
        price: price / 100,
        amount,
      });

      setSuccess(true);
      setAmount(100);
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка размещения ставки');
    } finally {
      setLoading(false);
    }
  }, [price, amount, marketId, side, canSubmit, loading, onSuccess]);

  return (
    <div className="bet-placement">
      {/* Side Buttons */}
      <div className="side-buttons">
        <button
          type="button"
          className={`side-btn yes ${side === 'yes' ? 'active' : ''}`}
          onClick={() => setSide('yes')}
        >
          <span>↑</span> ДА
        </button>
        <button
          type="button"
          className={`side-btn no ${side === 'no' ? 'active' : ''}`}
          onClick={() => setSide('no')}
        >
          <span>↓</span> НЕТ
        </button>
      </div>

      {/* Price Section */}
      <div className="price-section">
        <div className="price-label">
          <span>Цена</span>
          <span className="price-value">{price}%</span>
        </div>
        <input
          type="range"
          className={`price-slider ${side}`}
          min="1"
          max="99"
          value={price}
          onChange={handlePriceChange}
          style={{ '--fill': `${price}%` } as React.CSSProperties}
        />
        <div className="price-marks">
          <span>1%</span>
          <span>50%</span>
          <span>99%</span>
        </div>
      </div>

      {/* Amount Section */}
      <div className="amount-section">
        <div className="amount-input-wrapper">
          <span className="currency">₽</span>
          <input
            type="text"
            inputMode="numeric"
            value={amount || ''}
            onChange={handleAmountChange}
            placeholder="100"
          />
        </div>
        <div className="quick-amounts">
          <button type="button" className="quick-btn" onClick={() => setAmount(a => a + 10)}>+10</button>
          <button type="button" className="quick-btn" onClick={() => setAmount(a => a + 50)}>+50</button>
          <button type="button" className="quick-btn" onClick={() => setAmount(a => a + 100)}>+100</button>
          <button type="button" className="quick-btn max" onClick={() => setAmount(1000)}>MAX</button>
        </div>
      </div>

      {/* Profit Card */}
      {canSubmit && profit > 0 && (
        <div className={`profit-card ${side === 'no' ? 'no-side' : ''}`}>
          <div className="profit-row">
            <span className="profit-label">При выигрыше</span>
            <span className="profit-value">+{profit.toFixed(0)} ₽</span>
          </div>
          <div className="profit-row">
            <span className="profit-label">Множитель</span>
            <span className="multiplier">x{multiplier.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Messages */}
      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">Ставка размещена!</div>}

      {/* Submit Button */}
      <button
        type="button"
        className={`submit-btn ${side}`}
        onClick={handleSubmit}
        disabled={!canSubmit || loading}
      >
        {loading ? 'Размещение...' : `Поставить ${amount} ₽ на ${side === 'yes' ? 'ДА' : 'НЕТ'}`}
      </button>
    </div>
  );
};
