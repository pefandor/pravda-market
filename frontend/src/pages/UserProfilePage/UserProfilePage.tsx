/**
 * UserProfilePage - displays user balance, orders, and transaction history
 */

import { FC, useEffect, useState } from 'react';
import { Section, Cell, List, Spinner, Placeholder, Badge } from '@telegram-apps/telegram-ui';
import type { UserProfile, Order, LedgerEntry } from '@/types/api';
import { getUserProfile, getUserLedger } from '@/services/user';
import { getUserOrders } from '@/services/bets';
import { Page } from '@/components/Page';
import { formatCurrency, formatPrice, formatTimestamp } from '@/utils/formatting';
import { sanitizeText } from '@/utils/sanitize';

import './UserProfilePage.css';

// Alias for consistency
const formatAmount = formatCurrency;

/**
 * Format order status
 */
function getOrderStatusBadge(status: string) {
  switch (status) {
    case 'open':
      return <Badge type="number">Открыт</Badge>;
    case 'filled':
      return <Badge type="number">Исполнен</Badge>;
    case 'cancelled':
      return <Badge type="number">Отменен</Badge>;
    default:
      return <Badge type="number">{status}</Badge>;
  }
}

/**
 * Format ledger entry type
 */
function getLedgerEntryLabel(type: string): string {
  const labels: Record<string, string> = {
    deposit: '💵 Пополнение',
    withdraw: '💸 Вывод',
    order_lock: '🔒 Блокировка (ордер)',
    order_unlock: '🔓 Разблокировка',
    trade_lock: '🔒 Блокировка (сделка)',
    settlement_win: '🎉 Выигрыш',
    settlement_loss: '😔 Проигрыш',
  };
  return labels[type] || type;
}

export const UserProfilePage: FC = () => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [profileData, ordersData, ledgerData] = await Promise.all([
        getUserProfile(),
        getUserOrders(),
        getUserLedger(),
      ]);

      setProfile(profileData);
      setOrders(ordersData);
      setLedger(ledgerData);
    } catch (err) {
      console.error('Failed to load user data:', err);
      setError(err instanceof Error ? err.message : 'Не удалось загрузить данные пользователя');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Page back={false}>
        <div className="user-profile-page__loading">
          <Spinner size="l" />
          <p>Загрузка профиля...</p>
        </div>
      </Page>
    );
  }

  if (error || !profile) {
    return (
      <Page back={false}>
        <Placeholder
          header="Ошибка загрузки"
          description={error || 'Не удалось загрузить профиль'}
          action={
            <button onClick={loadUserData} className="user-profile-page__retry">
              Попробовать снова
            </button>
          }
        />
      </Page>
    );
  }

  return (
    <Page back={false}>
      <div className="user-profile-page">
        {/* User Info */}
        <Section>
          <div className="user-profile-page__header">
            <h1 className="user-profile-page__title">
              {sanitizeText(profile.user.first_name) || 'Пользователь'}
            </h1>
            {profile.user.username && (
              <p className="user-profile-page__username">@{sanitizeText(profile.user.username)}</p>
            )}
          </div>

          {/* Balance */}
          <div className="user-profile-page__balance">
            <span className="user-profile-page__balance-label">Баланс</span>
            <span className="user-profile-page__balance-amount">
              {formatAmount(profile.balance)}
            </span>
          </div>
        </Section>

        {/* Active Orders */}
        <Section header="Активные ордера">
          {orders.filter(o => o.status === 'open').length === 0 ? (
            <Placeholder
              description="У вас нет активных ордеров"
            />
          ) : (
            <List>
              {orders
                .filter(o => o.status === 'open')
                .map(order => (
                  <Cell
                    key={order.id}
                    subtitle={`${order.side === 'yes' ? 'ДА' : 'НЕТ'} @ ${formatPrice(order.price)}`}
                    after={getOrderStatusBadge(order.status)}
                  >
                    {formatAmount(order.amount)}
                  </Cell>
                ))}
            </List>
          )}
        </Section>

        {/* Transaction History */}
        <Section header="История транзакций">
          {ledger.length === 0 ? (
            <Placeholder
              description="История транзакций пуста"
            />
          ) : (
            <List>
              {ledger.slice(0, 20).map(entry => (
                <Cell
                  key={entry.id}
                  subtitle={formatTimestamp(entry.created_at)}
                  after={
                    <span
                      className={`user-profile-page__amount ${
                        entry.amount >= 0 ? 'positive' : 'negative'
                      }`}
                    >
                      {entry.amount >= 0 ? '+' : ''}
                      {formatAmount(entry.amount)}
                    </span>
                  }
                >
                  {getLedgerEntryLabel(entry.entry_type)}
                </Cell>
              ))}
            </List>
          )}
        </Section>
      </div>
    </Page>
  );
};
