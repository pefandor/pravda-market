import { FC, useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { Placeholder } from '@telegram-apps/telegram-ui';
import type { Market } from '@/types/api';
import { getMarkets } from '@/services/markets';
import { MarketCard } from '@/components/MarketCard';
import { Skeleton } from '@/components/Skeleton';
import { Page } from '@/components/Page';

import './MarketsPage.css';

const KNOWN_CATEGORIES: Record<string, string> = {
  sports: 'Спорт',
  esports: 'Киберспорт',
  politics: 'Политика',
  crypto: 'Крипто',
  weather: 'Погода',
};

type SortOption = 'popular' | 'new' | 'ending';

const SORT_OPTIONS: { key: SortOption; label: string }[] = [
  { key: 'popular', label: 'Популярные' },
  { key: 'new', label: 'Новые' },
  { key: 'ending', label: 'Скоро' },
];

function getCategoryLabel(cat: string): string {
  return KNOWN_CATEGORIES[cat] || cat.charAt(0).toUpperCase() + cat.slice(1);
}

function SkeletonCard() {
  return (
    <div className="markets-page__skeleton-card">
      <Skeleton width="75%" height="18px" />
      <Skeleton width="100%" height="6px" borderRadius="3px" />
      <Skeleton width="60%" height="14px" />
    </div>
  );
}

export const MarketsPage: FC = () => {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [sortBy, setSortBy] = useState<SortOption>('popular');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

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

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await getMarkets();
      setMarkets(data);
    } catch {
      // silent refresh failure
    } finally {
      setRefreshing(false);
    }
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(value);
    }, 300);
  };

  const categories = useMemo(() => {
    const cats = new Set(markets.map(m => m.category).filter((c): c is string => Boolean(c)));
    return ['all', ...Array.from(cats)];
  }, [markets]);

  const filtered = useMemo(() => {
    let result = markets;

    if (activeCategory !== 'all') {
      result = result.filter(m => m.category === activeCategory);
    }

    if (debouncedQuery.trim()) {
      const q = debouncedQuery.toLowerCase();
      result = result.filter(m => m.title.toLowerCase().includes(q));
    }

    result = [...result].sort((a, b) => {
      if (sortBy === 'popular') return b.volume - a.volume;
      if (sortBy === 'new') return Date.parse(b.created_at) - Date.parse(a.created_at);
      if (sortBy === 'ending') return Date.parse(a.deadline) - Date.parse(b.deadline);
      return 0;
    });

    return result;
  }, [markets, activeCategory, debouncedQuery, sortBy]);

  return (
    <Page back={false}>
      <div className="markets-page">
        {/* Header */}
        <div className="markets-page__header">
          <h1 className="markets-page__title">Pravda Market</h1>
          <button
            className={`markets-page__refresh ${refreshing ? 'markets-page__refresh--spinning' : ''}`}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M17.65 6.35A7.96 7.96 0 0 0 12 4C7.58 4 4.01 7.58 4.01 12S7.58 20 12 20c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35Z" fill="currentColor"/>
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="markets-page__search">
          <div className="markets-page__search-wrapper">
            <svg className="markets-page__search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5Zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14Z" fill="currentColor"/>
            </svg>
            <input
              className="markets-page__search-input"
              type="text"
              placeholder="Поиск событий..."
              value={searchQuery}
              onChange={e => handleSearchChange(e.target.value)}
            />
          </div>
        </div>

        {/* Categories */}
        {!loading && categories.length > 1 && (
          <div className="markets-page__categories">
            {categories.map(cat => (
              <button
                key={cat}
                className={`markets-page__category ${activeCategory === cat ? 'markets-page__category--active' : ''}`}
                onClick={() => setActiveCategory(cat)}
              >
                {cat === 'all' ? 'Все' : getCategoryLabel(cat)}
              </button>
            ))}
          </div>
        )}

        {/* Sort */}
        {!loading && !error && markets.length > 0 && (
          <div className="markets-page__sort">
            {SORT_OPTIONS.map(opt => (
              <button
                key={opt.key}
                className={`markets-page__sort-btn ${sortBy === opt.key ? 'markets-page__sort-btn--active' : ''}`}
                onClick={() => setSortBy(opt.key)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        )}

        {/* Error */}
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

        {/* Empty */}
        {!loading && !error && filtered.length === 0 && (
          <div className="markets-page__empty">
            <div className="markets-page__empty-icon">📊</div>
            <p>
              {debouncedQuery || activeCategory !== 'all'
                ? 'Ничего не найдено. Попробуйте изменить фильтры.'
                : 'Нет активных рынков. Скоро появятся новые события!'}
            </p>
          </div>
        )}

        {/* Market list */}
        {!loading && !error && filtered.length > 0 && (
          <div className="markets-page__list">
            {filtered.map(market => (
              <MarketCard key={market.id} market={market} />
            ))}
          </div>
        )}
      </div>
    </Page>
  );
};
