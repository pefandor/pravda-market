/**
 * Orderbook component
 * Displays aggregated YES and NO orders for a market
 */

import { memo, type FC } from 'react';
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

  // Take top 10 orders for each side
  const topYesOrders = yes_orders.slice(0, 10);
  const topNoOrders = no_orders.slice(0, 10);

  return (
    <div className={b()}>
      <Section header="Order Book">
        <div className={b('container')}>
          {/* YES Orders */}
          <div className={b('side', 'yes')}>
            <div className={b('header')}>
              <span className={b('header-title')}>ДА</span>
            </div>
            <div className={b('list')}>
              {topYesOrders.length === 0 ? (
                <div className={b('empty')}>Нет ордеров</div>
              ) : (
                topYesOrders.map((order, idx) => (
                  <div key={idx} className={b('row', 'yes')}>
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
              <span className={b('header-title')}>НЕТ</span>
            </div>
            <div className={b('list')}>
              {topNoOrders.length === 0 ? (
                <div className={b('empty')}>Нет ордеров</div>
              ) : (
                topNoOrders.map((order, idx) => (
                  <div key={idx} className={b('row', 'no')}>
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
