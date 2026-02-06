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

const root = ReactDOM.createRoot(document.getElementById('root')!);

// Simple error display for critical failures
function showError(message: string) {
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

if (isAdminRoute) {
  // Admin page works without Telegram SDK
  root.render(
    <StrictMode>
      <AdminRoot />
    </StrictMode>,
  );
} else {
  // Normal Telegram Mini App flow
  try {
    const launchParams = retrieveLaunchParams();
    const { tgWebAppPlatform: platform } = launchParams;
    const debug = (launchParams.tgWebAppStartParam || '').includes('debug')
      || import.meta.env.DEV;

    // Configure all application dependencies.
    init({
      debug,
      eruda: debug && ['ios', 'android'].includes(platform),
      mockForMacOS: platform === 'macos',
    })
      .then(() => {
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
    console.error('Launch params error:', e);
    try {
      root.render(<EnvUnsupported/>);
    } catch {
      showError('Telegram SDK unavailable');
    }
  }
}
