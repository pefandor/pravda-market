/**
 * AdminPage - Admin panel for market resolution and user management
 *
 * Features:
 * - Market list with resolution controls
 * - User deposit interface
 */

import { FC, useEffect, useState, useCallback } from 'react';
import { Section, Cell, List, Spinner, Input, Button } from '@telegram-apps/telegram-ui';
import {
  getAdminToken,
  setAdminToken,
  getMarkets,
  resolveMarket,
  getUsers,
  depositToUser,
  type AdminMarket,
  type AdminUser,
} from '@/services/admin';
import { formatCurrency } from '@/utils/formatting';

import './AdminPage.css';

type Tab = 'markets' | 'users';

export const AdminPage: FC = () => {
  const [token, setToken] = useState(getAdminToken() || '');
  const [isAuthenticated, setIsAuthenticated] = useState(!!getAdminToken());
  const [activeTab, setActiveTab] = useState<Tab>('markets');

  const [markets, setMarkets] = useState<AdminMarket[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Deposit form state
  const [depositTelegramId, setDepositTelegramId] = useState('');
  const [depositAmount, setDepositAmount] = useState('');

  const loadData = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      setLoading(true);
      setError(null);
      const [marketsData, usersData] = await Promise.all([
        getMarkets(),
        getUsers(),
      ]);
      setMarkets(marketsData);
      setUsers(usersData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
      if (err instanceof Error && err.message.includes('token')) {
        setIsAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleLogin = () => {
    if (!token.trim()) {
      setError('Введите admin token');
      return;
    }
    setAdminToken(token.trim());
    setIsAuthenticated(true);
  };

  const handleResolve = async (marketId: number, outcome: 'yes' | 'no') => {
    const market = markets.find(m => m.id === marketId);
    if (!market) return;

    const confirmMsg = `Резолвить маркет "${market.title}" как ${outcome.toUpperCase()}?`;
    if (!window.confirm(confirmMsg)) return;

    try {
      setLoading(true);
      setError(null);
      await resolveMarket(marketId, outcome);
      setSuccess(`Маркет #${marketId} резолвнут как ${outcome.toUpperCase()}`);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resolve market');
    } finally {
      setLoading(false);
    }
  };

  const handleDeposit = async () => {
    const telegramId = parseInt(depositTelegramId);
    const amount = parseFloat(depositAmount);

    if (isNaN(telegramId) || telegramId <= 0) {
      setError('Введите корректный Telegram ID');
      return;
    }
    if (isNaN(amount) || amount <= 0 || amount > 100000) {
      setError('Введите сумму от 0 до 100,000');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await depositToUser(telegramId, amount);
      setSuccess(`Депозит ${amount}₽ выполнен. Новый баланс: ${result.new_balance_rubles}₽`);
      setDepositTelegramId('');
      setDepositAmount('');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deposit');
    } finally {
      setLoading(false);
    }
  };

  // Clear messages after 5 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  // Login screen
  if (!isAuthenticated) {
    return (
      <div className="admin-page__wrapper">
        <div className="admin-page">
          <Section header="Admin Login">
            <div className="admin-page__login">
              <Input
                type="password"
                placeholder="Admin Token"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
              {error && <div className="admin-page__error">{error}</div>}
              <Button size="l" stretched onClick={handleLogin}>
                Войти
              </Button>
            </div>
          </Section>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page__wrapper">
      <div className="admin-page">
        <h1 className="admin-page__title">Admin Panel</h1>

        {/* Tabs */}
        <div className="admin-page__tabs">
          <button
            className={`admin-page__tab ${activeTab === 'markets' ? 'admin-page__tab--active' : ''}`}
            onClick={() => setActiveTab('markets')}
          >
            Маркеты
          </button>
          <button
            className={`admin-page__tab ${activeTab === 'users' ? 'admin-page__tab--active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            Пользователи
          </button>
        </div>

        {/* Messages */}
        {error && <div className="admin-page__error">{error}</div>}
        {success && <div className="admin-page__success">{success}</div>}

        {loading && (
          <div className="admin-page__loading">
            <Spinner size="m" />
          </div>
        )}

        {/* Markets Tab */}
        {activeTab === 'markets' && !loading && (
          <Section header={`Маркеты (${markets.length})`}>
            <List>
              {markets.map((market) => (
                <div key={market.id} className="admin-page__market">
                  <div className="admin-page__market-info">
                    <span className="admin-page__market-id">#{market.id}</span>
                    <span className="admin-page__market-title">{market.title}</span>
                    {market.resolved && (
                      <span className="admin-page__market-resolved">
                        {market.outcome?.toUpperCase()}
                      </span>
                    )}
                  </div>
                  {!market.resolved && (
                    <div className="admin-page__market-actions">
                      <button
                        className="admin-page__resolve admin-page__resolve--yes"
                        onClick={() => handleResolve(market.id, 'yes')}
                      >
                        YES
                      </button>
                      <button
                        className="admin-page__resolve admin-page__resolve--no"
                        onClick={() => handleResolve(market.id, 'no')}
                      >
                        NO
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </List>
          </Section>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && !loading && (
          <>
            {/* Deposit Form */}
            <Section header="Депозит пользователю">
              <div className="admin-page__deposit-form">
                <Input
                  type="number"
                  placeholder="Telegram ID"
                  value={depositTelegramId}
                  onChange={(e) => setDepositTelegramId(e.target.value)}
                />
                <Input
                  type="number"
                  placeholder="Сумма (₽)"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                />
                <Button size="m" onClick={handleDeposit} disabled={loading}>
                  Депозит
                </Button>
              </div>
            </Section>

            {/* Users List */}
            <Section header={`Пользователи (${users.length})`}>
              <List>
                {users.map((user) => (
                  <Cell
                    key={user.id}
                    subtitle={`ID: ${user.telegram_id}`}
                    after={
                      <span className="admin-page__user-balance">
                        {formatCurrency(user.balance_rubles)}
                      </span>
                    }
                  >
                    {user.first_name || user.username || `User #${user.id}`}
                  </Cell>
                ))}
              </List>
            </Section>
          </>
        )}
      </div>
    </div>
  );
};
