// Include Telegram UI styles first to allow our code override the package CSS.
import '@telegram-apps/telegram-ui/dist/styles.css';

import ReactDOM from 'react-dom/client';
import { StrictMode } from 'react';
import { retrieveLaunchParams } from '@tma.js/sdk-react';

import { Root } from '@/components/Root.tsx';
import { AdminRoot } from '@/components/AdminRoot.tsx';
import { EnvUnsupported } from '@/components/EnvUnsupported.tsx';
import { init } from '@/init.ts';

import './index.css';

// Mock the environment in case, we are outside Telegram.
import './mockEnv.ts';

// Global error handler
window.onerror = (msg, url, line, col, error) => {
  console.error('[BOOT] Global error:', msg, url, line, col, error);
  return false;
};
window.onunhandledrejection = (event) => {
  console.error('[BOOT] Unhandled rejection:', event.reason);
};

const root = ReactDOM.createRoot(document.getElementById('root')!);

console.log('[BOOT] index.tsx loaded, root element:', document.getElementById('root'));

// Simple error display for critical failures
function showError(message: string) {
  console.error('[BOOT] showError called:', message);
  root.render(
    <div style={{ padding: 20, color: '#fff', background: '#1a1a2e', minHeight: '100vh' }}>
      <h2>Ошибка загрузки</h2>
      <p>{message}</p>
      <p style={{ fontSize: 12, opacity: 0.7 }}>Попробуйте перезапустить приложение</p>
    </div>
  );
}

// Check if we're on admin route - render without Telegram SDK
const isAdminRoute = window.location.hash.startsWith('#/admin');
console.log('[BOOT] isAdminRoute:', isAdminRoute, 'hash:', window.location.hash);

if (isAdminRoute) {
  // Admin page works without Telegram SDK
  root.render(
    <StrictMode>
      <AdminRoot />
    </StrictMode>,
  );
} else {
  // Normal Telegram Mini App flow
  console.log('[BOOT] Starting Telegram Mini App flow');
  try {
    console.log('[BOOT] Calling retrieveLaunchParams...');
    const launchParams = retrieveLaunchParams();
    console.log('[BOOT] launchParams:', JSON.stringify(launchParams, null, 2));
    const { tgWebAppPlatform: platform } = launchParams;
    const debug = (launchParams.tgWebAppStartParam || '').includes('debug')
      || import.meta.env.DEV;

    // Configure all application dependencies.
    console.log('[BOOT] Calling init with debug:', debug, 'platform:', platform);
    init({
      debug,
      eruda: debug && ['ios', 'android'].includes(platform),
      mockForMacOS: platform === 'macos',
    })
      .then(() => {
        console.log('[BOOT] init() resolved, rendering Root');
        root.render(
          <StrictMode>
            <Root/>
          </StrictMode>,
        );
      })
      .catch((e) => {
        console.error('Init failed:', e);
        showError(`Init error: ${e?.message || 'Unknown error'}`);
      });
  } catch (e) {
    console.error('[BOOT] Launch params error:', e);
    try {
      console.log('[BOOT] Rendering EnvUnsupported');
      root.render(<EnvUnsupported/>);
    } catch (e2) {
      console.error('[BOOT] EnvUnsupported render failed:', e2);
      showError('Telegram SDK unavailable');
    }
  }
}
