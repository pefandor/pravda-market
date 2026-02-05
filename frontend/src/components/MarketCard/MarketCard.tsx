import { memo, type FC } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Market } from '@/types/api';
import { formatPrice, formatDeadline, formatAmount } from '@/utils/formatting';
import { sanitizeText } from '@/utils/sanitize';

import './MarketCard.css';

const KNOWN_CATEGORIES: Record<string, string> = {
  sports: 'Спорт',
  esports: 'Киберспорт',
  politics: 'Политика',
  crypto: 'Крипто',
  weather: 'Погода',
};

function getCategoryLabel(cat: string | null): string | null {
  if (!cat) return null;
  return KNOWN_CATEGORIES[cat] || cat.charAt(0).toUpperCase() + cat.slice(1);
}

export interface MarketCardProps {
  market: Market;
}

const MarketCardComponent: FC<MarketCardProps> = ({ market }) => {
  const navigate = useNavigate();
  const yesPercent = market.yes_price / 100;

  return (
    <div
      className="market-card"
      onClick={() => navigate(`/market/${market.id}`)}
    >
      <div className="market-card__title">{sanitizeText(market.title)}</div>

      {/* Probability labels */}
      <div className="market-card__probs">
        <span className="market-card__prob-yes">YES {formatPrice(market.yes_price)}</span>
        <span className="market-card__prob-no">NO {formatPrice(market.no_price)}</span>
      </div>

      {/* Progress bar */}
      <div className="market-card__bar">
        <div
          className="market-card__bar-yes"
          style={{ width: `${yesPercent}%` }}
        />
        <div className="market-card__bar-no" />
      </div>

      {/* Meta footer */}
      <div className="market-card__meta">
        {market.volume > 0 && (
          <>
            <span>{formatAmount(market.volume)}</span>
            <span className="market-card__meta-sep">·</span>
          </>
        )}
        {market.category && (
          <>
            <span>{getCategoryLabel(market.category)}</span>
            <span className="market-card__meta-sep">·</span>
          </>
        )}
        <span>{formatDeadline(market.deadline)}</span>
      </div>
    </div>
  );
};

export const MarketCard = memo(MarketCardComponent, (prevProps, nextProps) => {
  return (
    prevProps.market.id === nextProps.market.id &&
    prevProps.market.title === nextProps.market.title &&
    prevProps.market.yes_price === nextProps.market.yes_price &&
    prevProps.market.no_price === nextProps.market.no_price &&
    prevProps.market.deadline === nextProps.market.deadline &&
    prevProps.market.volume === nextProps.market.volume &&
    prevProps.market.category === nextProps.market.category
  );
});
