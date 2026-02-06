import { FC, useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Section, Cell, List, Spinner, Placeholder } from '@telegram-apps/telegram-ui';
import { useTonConnectUI, useTonWallet } from '@tonconnect/ui-react';
import type { UserProfile, LedgerEntry } from '@/types/api';
import { getUserProfile, getUserLedger } from '@/services/user';
import { Page } from '@/components/Page';
import { formatCurrency, formatTimestamp } from '@/utils/formatting';
import { sanitizeText } from '@/utils/sanitize';
import { createDepositTransaction, MIN_DEPOSIT_TON, ESCROW_ADDRESS } from '@/services/ton';

import './UserProfilePage.css';

const formatAmount = formatCurrency;

function getLedgerEntryLabel(type: string): string {
  const labels: Record<string, string> = {
    deposit: 'Пополнение',
    withdraw: 'Вывод',
    order_lock: 'Блокировка (ордер)',
    order_unlock: 'Разблокировка',
    trade_lock: 'Блокировка (сделка)',
    settlement_win: 'Выигрыш',
    settlement_loss: 'Проигрыш',
  };
  return labels[type] || type;
}

export const UserProfilePage: FC = () => {
  const navigate = useNavigate();
  const [tonConnectUI] = useTonConnectUI();
  const wallet = useTonWallet();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Deposit state
  const [depositAmount, setDepositAmount] = useState<string>('');
  const [depositLoading, setDepositLoading] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    loadUserData();
  }, []);

  // Auto-hide toast after 5 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleDeposit = useCallback(async () => {
    if (!profile) return;

    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount < MIN_DEPOSIT_TON) {
      setToast({ type: 'error', message: `Минимум ${MIN_DEPOSIT_TON} TON` });
      return;
    }

    if (!wallet) {
      // Open wallet connection modal
      await tonConnectUI.openModal();
      return;
    }

    try {
      setDepositLoading(true);

      // Create and send transaction
      const transaction = createDepositTransaction(amount, profile.user.telegram_id);
      await tonConnectUI.sendTransaction(transaction);

      // Success!
      setToast({
        type: 'success',
        message: `Транзакция отправлена! ${amount} TON будет зачислено после подтверждения.`,
      });
      setDepositAmount('');

      // Reload data after a short delay
      setTimeout(() => loadUserData(), 3000);
    } catch (err) {
      console.error('Deposit failed:', err);
      const errorMessage = err instanceof Error ? err.message : 'Не удалось отправить транзакцию';
      setToast({ type: 'error', message: errorMessage });
    } finally {
      setDepositLoading(false);
    }
  }, [profile, depositAmount, wallet, tonConnectUI]);

  const loadUserData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profileData, ledgerData] = await Promise.all([
        getUserProfile(),
        getUserLedger(),
      ]);
      setProfile(profileData);
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
            <p className="user-profile-page__telegram-id">ID: {profile.user.telegram_id}</p>
          </div>

          {/* Balance */}
          <div className="user-profile-page__balance">
            <span className="user-profile-page__balance-label">Баланс</span>
            <span className="user-profile-page__balance-amount">
              {formatAmount(profile.balance)}
            </span>
          </div>

        </Section>

        {/* Toast Notification */}
        {toast && (
          <div className={`user-profile-page__toast user-profile-page__toast--${toast.type}`}>
            {toast.message}
          </div>
        )}

        {/* Deposit Section */}
        <Section header="Пополнить баланс">
          <div className="user-profile-page__deposit">
            <div className="user-profile-page__deposit-info">
              <span className="user-profile-page__deposit-icon">💎</span>
              <div className="user-profile-page__deposit-text">
                <p className="user-profile-page__deposit-title">TON Deposit</p>
                <p className="user-profile-page__deposit-subtitle">
                  {wallet
                    ? `Кошелёк: ${wallet.account.address.slice(0, 6)}...${wallet.account.address.slice(-4)}`
                    : 'Подключите кошелёк для пополнения'}
                </p>
              </div>
            </div>

            <div className="user-profile-page__deposit-form">
              <div className="user-profile-page__deposit-input-wrapper">
                <input
                  type="number"
                  className="user-profile-page__deposit-input"
                  placeholder={`Мин. ${MIN_DEPOSIT_TON}`}
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  min={MIN_DEPOSIT_TON}
                  step="0.1"
                  disabled={depositLoading}
                />
                <span className="user-profile-page__deposit-currency">TON</span>
              </div>

              <div className="user-profile-page__deposit-presets">
                {[0.5, 1, 5, 10].map((amount) => (
                  <button
                    key={amount}
                    className="user-profile-page__deposit-preset"
                    onClick={() => setDepositAmount(amount.toString())}
                    disabled={depositLoading}
                  >
                    {amount}
                  </button>
                ))}
              </div>

              <button
                className="user-profile-page__deposit-button"
                onClick={handleDeposit}
                disabled={depositLoading || (!wallet && !depositAmount)}
              >
                {depositLoading ? (
                  <Spinner size="s" />
                ) : wallet ? (
                  'Пополнить'
                ) : (
                  'Подключить кошелёк'
                )}
              </button>
            </div>

            <p className="user-profile-page__deposit-address">
              Контракт: {ESCROW_ADDRESS.slice(0, 12)}...
            </p>
          </div>
        </Section>

        {/* TON Connect Management */}
        <Section>
          <Cell onClick={() => navigate('/ton-connect')}>
            {wallet ? 'Управление кошельком' : 'Подключить кошелёк TON'}
          </Cell>
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
