/**
 * Orderbook component
 * Displays aggregated YES and NO orders for a market with visual depth bars
 */

import { memo, useMemo, type FC } from 'react';
import { Section } from '@telegram-apps/telegram-ui';
import type { Orderbook as OrderbookType } from '@/types/api';
import { bem } from '@/css/bem';
import { formatPriceDetailed, formatAmount } from '@/utils/formatting';

import './Orderbook.css';

const [b] = bem('orderbook');

export interface OrderbookProps {
  orderbook: OrderbookType;
}

// Alias for consistent naming
const formatPrice = formatPriceDetailed;

const OrderbookComponent: FC<OrderbookProps> = ({ orderbook }) => {
  const { yes_orders, no_orders } = orderbook;

  // Take top 5 orders for each side (more compact)
  const topYesOrders = yes_orders.slice(0, 5);
  const topNoOrders = no_orders.slice(0, 5);

  // Calculate max amount for bar width scaling
  const maxAmount = useMemo(() => {
    const allAmounts = [...topYesOrders, ...topNoOrders].map(o => o.amount);
    return allAmounts.length > 0 ? Math.max(...allAmounts) : 1;
  }, [topYesOrders, topNoOrders]);

  // Get best prices
  const bestYesPrice = topYesOrders[0]?.price ?? 0;
  const bestNoPrice = topNoOrders[0]?.price ?? 0;

  return (
    <div className={b()}>
      <Section header="📊 Order Book">
        {/* Best Prices Summary */}
        <div className={b('summary')}>
          <div className={b('summary-item', 'yes')}>
            <span className={b('summary-label')}>Best YES</span>
            <span className={b('summary-price')}>{bestYesPrice > 0 ? formatPrice(bestYesPrice) : '—'}</span>
          </div>
          <div className={b('summary-divider')}>
            <span className={b('summary-spread')}>
              {bestYesPrice > 0 && bestNoPrice > 0
                ? `${((1 - bestYesPrice - bestNoPrice) * 100).toFixed(1)}%`
                : '—'
              }
            </span>
            <span className={b('summary-spread-label')}>spread</span>
          </div>
          <div className={b('summary-item', 'no')}>
            <span className={b('summary-label')}>Best NO</span>
            <span className={b('summary-price')}>{bestNoPrice > 0 ? formatPrice(bestNoPrice) : '—'}</span>
          </div>
        </div>

        <div className={b('container')}>
          {/* YES Orders */}
          <div className={b('side', 'yes')}>
            <div className={b('header')}>
              <span className={b('header-icon')}>↑</span>
              <span className={b('header-title')}>ДА</span>
            </div>
            <div className={b('list')}>
              {topYesOrders.length === 0 ? (
                <div className={b('empty')}>Нет ордеров</div>
              ) : (
                topYesOrders.map((order, idx) => (
                  <div key={idx} className={b('row', 'yes')}>
                    <div
                      className={b('bar')}
                      style={{ width: `${(order.amount / maxAmount) * 100}%` }}
                    />
                    <span className={b('price')}>{formatPrice(order.price)}</span>
                    <span className={b('amount')}>{formatAmount(order.amount)}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* NO Orders */}
          <div className={b('side', 'no')}>
            <div className={b('header')}>
              <span className={b('header-icon')}>↓</span>
              <span className={b('header-title')}>НЕТ</span>
            </div>
            <div className={b('list')}>
              {topNoOrders.length === 0 ? (
                <div className={b('empty')}>Нет ордеров</div>
              ) : (
                topNoOrders.map((order, idx) => (
                  <div key={idx} className={b('row', 'no')}>
                    <div
                      className={b('bar')}
                      style={{ width: `${(order.amount / maxAmount) * 100}%` }}
                    />
                    <span className={b('price')}>{formatPrice(order.price)}</span>
                    <span className={b('amount')}>{formatAmount(order.amount)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
};

/**
 * Helper to compare order arrays
 */
function ordersAreEqual(
  a: Array<{ price: number; amount: number }>,
  b: Array<{ price: number; amount: number }>
): boolean {
  if (a.length !== b.length) return false;

  for (let i = 0; i < a.length; i++) {
    if (a[i].price !== b[i].price || a[i].amount !== b[i].amount) {
      return false;
    }
  }

  return true;
}

/**
 * Memoized version with deep orderbook comparison
 * Prevents re-renders when orderbook data hasn't changed
 */
export const Orderbook = memo(OrderbookComponent, (prevProps, nextProps) => {
  return (
    ordersAreEqual(prevProps.orderbook.yes_orders, nextProps.orderbook.yes_orders) &&
    ordersAreEqual(prevProps.orderbook.no_orders, nextProps.orderbook.no_orders)
  );
});
