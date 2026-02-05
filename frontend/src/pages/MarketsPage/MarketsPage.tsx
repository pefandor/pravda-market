/**
 * MarketsPage - displays list of active prediction markets
 */

import { FC, useEffect, useState } from 'react';
import { List, Placeholder, Spinner } from '@telegram-apps/telegram-ui';
import type { Market } from '@/types/api';
import { getMarkets } from '@/services/markets';
import { MarketCard } from '@/components/MarketCard';
import { Page } from '@/components/Page';

import './MarketsPage.css';

export const MarketsPage: FC = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMarkets();
  }, []);

  const loadMarkets = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getMarkets();
      setMarkets(data);
    } catch (err) {
      console.error('Failed to load markets:', err);
      setError(err instanceof Error ? err.message : 'Не удалось загрузить рынки');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Page back={false}>
      <div className="markets-page">
        <div className="markets-page__header">
          <h1 className="markets-page__title">Рынки прогнозов</h1>
          <p className="markets-page__subtitle">
            Ставьте на будущие события и зарабатывайте на правильных прогнозах
          </p>
        </div>

        {loading && (
          <div className="markets-page__loading">
            <Spinner size="l" />
            <p>Загрузка рынков...</p>
          </div>
        )}

        {error && !loading && (
          <Placeholder
            header="Ошибка загрузки"
            description={error}
            action={
              <button onClick={loadMarkets} className="markets-page__retry">
                Попробовать снова
              </button>
            }
          />
        )}

        {!loading && !error && markets.length === 0 && (
          <Placeholder
            header="Нет активных рынков"
            description="Скоро появятся новые рынки для прогнозов"
          />
        )}

        {!loading && !error && markets.length > 0 && (
          <List className="markets-page__list">
            {markets.map((market) => (
              <MarketCard key={market.id} market={market} />
            ))}
          </List>
        )}
      </div>
    </Page>
  );
};
