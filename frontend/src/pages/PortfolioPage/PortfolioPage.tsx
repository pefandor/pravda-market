import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Spinner, Placeholder } from '@telegram-apps/telegram-ui';
import type { Order, UserProfile } from '@/types/api';
import { getUserProfile } from '@/services/user';
import { getUserOrders } from '@/services/bets';
import { formatCurrency, formatPrice } from '@/utils/formatting';
import { Page } from '@/components/Page';

import './PortfolioPage.css';

export const PortfolioPage: FC = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profileData, ordersData] = await Promise.all([
        getUserProfile(),
        getUserOrders(),
      ]);
      setProfile(profileData);
      setOrders(ordersData);
    } catch (err) {
      console.error('Failed to load portfolio:', err);
      setError(err instanceof Error ? err.message : 'Не удалось загрузить портфель');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Page back={false}>
        <div className="portfolio-page__loading">
          <Spinner size="l" />
          <p>Загрузка портфеля...</p>
        </div>
      </Page>
    );
  }

  if (error || !profile) {
    return (
      <Page back={false}>
        <Placeholder
          header="Ошибка загрузки"
          description={error || 'Не удалось загрузить портфель'}
          action={
            <button onClick={loadData} className="portfolio-page__retry">
              Попробовать снова
            </button>
          }
        />
      </Page>
    );
  }

  const activeOrders = orders.filter(o => o.status === 'open' || o.status === 'filled');
  const lockedAmount = orders
    .filter(o => o.status === 'open')
    .reduce((sum, o) => sum + (o.amount - o.filled), 0);

  return (
    <Page back={false}>
      <div className="portfolio-page">
        {/* Balance card */}
        <div className="portfolio-page__balance-card">
          <div className="portfolio-page__balance-total">
            {formatCurrency(profile.balance)}
          </div>
          <div className="portfolio-page__balance-row">
            <span className="portfolio-page__balance-label">Доступно</span>
            <span>{formatCurrency(profile.balance - lockedAmount)}</span>
          </div>
          <div className="portfolio-page__balance-row">
            <span className="portfolio-page__balance-label">Залочено</span>
            <span>{formatCurrency(lockedAmount)}</span>
          </div>
        </div>

        {/* Active orders */}
        <div className="portfolio-page__section-header">
          Активные ставки ({activeOrders.length})
        </div>

        {activeOrders.length === 0 ? (
          <div className="portfolio-page__empty">
            <div className="portfolio-page__empty-icon">📊</div>
            <div className="portfolio-page__empty-text">
              У вас пока нет ставок.<br />
              Перейдите на вкладку Рынки, чтобы сделать первую ставку.
            </div>
          </div>
        ) : (
          activeOrders.map((order) => (
            <div
              key={order.id}
              className="portfolio-page__order"
              onClick={() => navigate(`/market/${order.market_id}`)}
            >
              <div className="portfolio-page__order-title">
                Маркет #{order.market_id}
              </div>
              <div className="portfolio-page__order-details">
                <span
                  className={`portfolio-page__order-side portfolio-page__order-side--${order.side}`}
                >
                  {order.side === 'yes' ? 'ДА' : 'НЕТ'} @ {formatPrice(order.price)}
                </span>
                <span>{formatCurrency(order.amount)}</span>
                <span>{order.status === 'open' ? 'Открыт' : 'Исполнен'}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </Page>
  );
};
