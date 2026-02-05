/**
 * AdminRoot - Standalone root component for admin page
 *
 * Renders without Telegram SDK dependencies.
 * Works in regular browser with ADMIN_TOKEN authentication.
 */

import { AppRoot } from '@telegram-apps/telegram-ui';
import { AdminPage } from '@/pages/AdminPage/AdminPage';

export function AdminRoot() {
  // Check system dark mode preference
  const isDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? true;

  return (
    <AppRoot appearance={isDark ? 'dark' : 'light'} platform="base">
      <AdminPage />
    </AppRoot>
  );
}
