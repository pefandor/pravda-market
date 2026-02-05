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
    await init({
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
      });
  } catch (e) {
    root.render(<EnvUnsupported/>);
  }
}
