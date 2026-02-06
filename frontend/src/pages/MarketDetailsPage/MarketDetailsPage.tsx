/**
 * MarketDetailsPage - displays market details, orderbook, and bet placement form
 */

import { FC, useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Spinner, Placeholder, Section, Cell } from '@telegram-apps/telegram-ui';
import type { Market, Orderbook as OrderbookType } from '@/types/api';
import { getMarket, getOrderbook } from '@/services/markets';
import { Orderbook } from '@/components/Orderbook';
import { BetPlacement } from '@/components/BetPlacement';
import { Page } from '@/components/Page';
import { formatDeadlineFull, formatCurrency } from '@/utils/formatting';
import { sanitizeText } from '@/utils/sanitize';
import { useCountdown } from '@/utils/useCountdown';

import './MarketDetailsPage.css';

// Aliases for consistent naming
const formatDeadline = formatDeadlineFull;
const formatVolume = formatCurrency;

/**
 * CountdownCell - displays deadline with live countdown timer
 */
const CountdownCell: FC<{ deadline: string }> = ({ deadline }) => {
  const countdown = useCountdown(deadline);

  return (
    <Cell subtitle="Дедлайн" multiline>
      <div className="market-details-page__deadline">
        <span className="market-details-page__deadline-date">
          {formatDeadline(deadline)}
        </span>
        <span
          className={`market-details-page__countdown ${
            countdown.isExpired ? 'market-details-page__countdown--expired' :
            countdown.isUrgent ? 'market-details-page__countdown--urgent' : ''
          }`}
        >
          {countdown.isExpired ? 'Завершён' : countdown.formatted}
        </span>
      </div>
    </Cell>
  );
};

export const MarketDetailsPage: FC = () => {
  const { marketId } = useParams<{ marketId: string }>();
  const [market, setMarket] = useState<Market | null>(null);
  const [orderbook, setOrderbook] = useState<OrderbookType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (marketId) {
      const parsedId = parseInt(marketId);
      if (isNaN(parsedId)) {
        setError('Invalid market ID');
        setLoading(false);
        return;
      }
      loadMarketData(parsedId);
    }
  }, [marketId]);

  const loadMarketData = async (id: number) => {
    try {
      setLoading(true);
      setError(null);

      const [marketData, orderbookData] = await Promise.all([
        getMarket(id),
        getOrderbook(id),
      ]);

      setMarket(marketData);
      setOrderbook(orderbookData);
    } catch (err) {
      console.error('Failed to load market data:', err);
      setError(err instanceof Error ? err.message : 'Не удалось загрузить данные рынка');
    } finally {
      setLoading(false);
    }
  };

  const handleBetSuccess = () => {
    // Reload orderbook after successful bet placement
    if (marketId) {
      const parsedId = parseInt(marketId);
      if (!isNaN(parsedId)) {
        getOrderbook(parsedId)
          .then(setOrderbook)
          .catch(console.error);
      }
    }
  };

  const handleShare = useCallback(async () => {
    if (!market) return;

    const shareUrl = `https://t.me/PravdaMarketBot/app?startapp=market_${market.id}`;
    const shareText = market.title;

    // Try Web Share API first (works in Telegram WebView)
    if (navigator.share) {
      try {
        await navigator.share({
          title: shareText,
          url: shareUrl,
        });
        return;
      } catch {
        // User cancelled or share failed - fall through to clipboard
      }
    }

    // Fallback: copy to clipboard
    try {
      await navigator.clipboard.writeText(shareUrl);
      alert('Ссылка скопирована!');
    } catch {
      alert('Не удалось скопировать ссылку');
    }
  }, [market]);

  if (loading) {
    return (
      <Page>
        <div className="market-details-page__loading">
          <Spinner size="l" />
          <p>Загрузка...</p>
        </div>
      </Page>
    );
  }

  if (error || !market) {
    return (
      <Page>
        <Placeholder
          header="Ошибка загрузки"
          description={error || 'Рынок не найден'}
        />
      </Page>
    );
  }

  return (
    <Page>
      <div className="market-details-page">
        {/* Market Header */}
        <Section>
          <div className="market-details-page__header">
            <div className="market-details-page__title-row">
              <h1 className="market-details-page__title">{sanitizeText(market.title)}</h1>
              <button
                className="market-details-page__share"
                onClick={handleShare}
                aria-label="Поделиться"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                  <polyline points="16 6 12 2 8 6" />
                  <line x1="12" y1="2" x2="12" y2="15" />
                </svg>
              </button>
            </div>
            {market.description && (
              <p className="market-details-page__description">{sanitizeText(market.description)}</p>
            )}
          </div>

          {/* Market Info */}
          <div className="market-details-page__info">
            <CountdownCell deadline={market.deadline} />
            {market.volume > 0 && (
              <Cell
                subtitle="Объем торгов"
              >
                {formatVolume(market.volume)}
              </Cell>
            )}
            {market.category && (
              <Cell
                subtitle="Категория"
              >
                {sanitizeText(market.category)}
              </Cell>
            )}
          </div>
        </Section>

        {/* Orderbook */}
        {orderbook && <Orderbook orderbook={orderbook} />}

        {/* Bet Placement Form */}
        {!market.resolved && (
          <BetPlacement
            marketId={market.id}
            onSuccess={handleBetSuccess}
          />
        )}

        {/* Resolved Market Notice */}
        {market.resolved && (
          <Section>
            <Placeholder
              header="Рынок завершен"
              description={
                market.outcome
                  ? `Исход: ${market.outcome === 'yes' ? 'ДА' : 'НЕТ'}`
                  : 'Результат обрабатывается'
              }
            />
          </Section>
        )}
      </div>
    </Page>
  );
};
