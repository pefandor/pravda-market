/**
 * MarketCard component
 * Displays a single market with its details
 */

import { memo, type FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { Cell, Badge } from '@telegram-apps/telegram-ui';
import type { Market } from '@/types/api';
import { bem } from '@/css/bem';
import { formatPrice, formatDeadline, formatVolume } from '@/utils/formatting';
import { sanitizeText } from '@/utils/sanitize';

import './MarketCard.css';

const [b] = bem('market-card');

export interface MarketCardProps {
  market: Market;
}

const MarketCardComponent: FC<MarketCardProps> = ({ market }) => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/market/${market.id}`);
  };

  return (
    <Cell
      className={b()}
      onClick={handleClick}
      subtitle={
        <div className={b('info')}>
          <span className={b('deadline')}>🕐 {formatDeadline(market.deadline)}</span>
          {market.volume > 0 && (
            <span className={b('volume')}>💰 {formatVolume(market.volume)}</span>
          )}
        </div>
      }
      after={
        <div className={b('prices')}>
          <Badge type="number" className={b('price', 'yes')}>
            ДА {formatPrice(market.yes_price)}
          </Badge>
          <Badge type="number" className={b('price', 'no')}>
            НЕТ {formatPrice(market.no_price)}
          </Badge>
        </div>
      }
    >
      <div className={b('title')}>{sanitizeText(market.title)}</div>
    </Cell>
  );
};

/**
 * Memoized version with custom comparison
 * Only re-renders if market properties actually change
 */
export const MarketCard = memo(MarketCardComponent, (prevProps, nextProps) => {
  // Return true if props are equal (skip re-render)
  // Return false if props changed (re-render)
  return (
    prevProps.market.id === nextProps.market.id &&
    prevProps.market.title === nextProps.market.title &&
    prevProps.market.yes_price === nextProps.market.yes_price &&
    prevProps.market.no_price === nextProps.market.no_price &&
    prevProps.market.deadline === nextProps.market.deadline &&
    prevProps.market.volume === nextProps.market.volume
  );
});
