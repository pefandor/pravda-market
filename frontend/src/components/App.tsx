import { Navigate, Route, Routes, HashRouter } from 'react-router-dom';
import { useLaunchParams, useSignal, miniApp } from '@tma.js/sdk-react';
import { AppRoot } from '@telegram-apps/telegram-ui';

import { ROUTES } from '@/navigation/routes';
import { TabLayout } from '@/components/TabLayout';
import { MarketsPage } from '@/pages/MarketsPage';
import { PortfolioPage } from '@/pages/PortfolioPage';
import { UserProfilePage } from '@/pages/UserProfilePage';
import { MarketDetailsPage } from '@/pages/MarketDetailsPage';
import { TONConnectPage } from '@/pages/TONConnectPage/TONConnectPage';
import { AdminPage } from '@/pages/AdminPage/AdminPage';

export function App() {
  const lp = useLaunchParams();
  const isDark = useSignal(miniApp.isDark);

  return (
    <AppRoot
      appearance={isDark ? 'dark' : 'light'}
      platform={['macos', 'ios'].includes(lp.tgWebAppPlatform) ? 'ios' : 'base'}
    >
      <HashRouter>
        <Routes>
          {/* Tabs layout */}
          <Route element={<TabLayout />}>
            <Route path={ROUTES.MARKETS} element={<MarketsPage />} />
            <Route path={ROUTES.PORTFOLIO} element={<PortfolioPage />} />
            <Route path={ROUTES.PROFILE} element={<UserProfilePage />} />
          </Route>

          {/* Standalone pages (no tab bar) */}
          <Route path={ROUTES.MARKET_DETAILS} element={<MarketDetailsPage />} />
          <Route path={ROUTES.TON_CONNECT} element={<TONConnectPage />} />
          <Route path={ROUTES.ADMIN} element={<AdminPage />} />

          {/* Redirects */}
          <Route path="/" element={<Navigate to={ROUTES.MARKETS} replace />} />
          <Route path="*" element={<Navigate to={ROUTES.MARKETS} replace />} />
        </Routes>
      </HashRouter>
    </AppRoot>
  );
}
