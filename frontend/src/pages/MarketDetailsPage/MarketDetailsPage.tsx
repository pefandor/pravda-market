/**
 * MarketDetailsPage - displays market details, orderbook, and bet placement form
 */

import { FC, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Spinner, Placeholder, Section, Cell } from '@telegram-apps/telegram-ui';
import type { Market, Orderbook as OrderbookType } from '@/types/api';
import { getMarket, getOrderbook } from '@/services/markets';
import { Orderbook } from '@/components/Orderbook';
import { BetPlacement } from '@/components/BetPlacement';
import { Page } from '@/components/Page';
import { formatDeadlineFull, formatCurrency } from '@/utils/formatting';
import { sanitizeText } from '@/utils/sanitize';

import './MarketDetailsPage.css';

// Aliases for consistent naming
const formatDeadline = formatDeadlineFull;
const formatVolume = formatCurrency;

export const MarketDetailsPage: FC = () => {
  const { marketId } = useParams<{ marketId: string }>();
  const [market, setMarket] = useState<Market | null>(null);
  const [orderbook, setOrderbook] = useState<OrderbookType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (marketId) {
      loadMarketData(parseInt(marketId));
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
      getOrderbook(parseInt(marketId))
        .then(setOrderbook)
        .catch(console.error);
    }
  };

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
            <h1 className="market-details-page__title">{sanitizeText(market.title)}</h1>
            {market.description && (
              <p className="market-details-page__description">{sanitizeText(market.description)}</p>
            )}
          </div>

          {/* Market Info */}
          <div className="market-details-page__info">
            <Cell
              subtitle="Дедлайн"
              multiline
            >
              {formatDeadline(market.deadline)}
            </Cell>
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
