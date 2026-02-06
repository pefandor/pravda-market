// Buffer polyfill for @ton/ton and @ton/core (must be first!)
import { Buffer } from 'buffer';
(window as any).Buffer = Buffer;

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

// DEBUG: Visual boot log overlay
const bootLogs: string[] = [];
function logBoot(msg: string) {
  console.log('[BOOT]', msg);
  bootLogs.push(`${new Date().toISOString().slice(11,23)} ${msg}`);
  const debugEl = document.getElementById('boot-debug');
  if (debugEl) {
    debugEl.innerText = bootLogs.slice(-15).join('\n');
  }
}

// Create debug overlay
const debugDiv = document.createElement('div');
debugDiv.id = 'boot-debug';
debugDiv.style.cssText = 'position:fixed;top:0;left:0;right:0;background:rgba(0,0,0,0.9);color:#0f0;font-family:monospace;font-size:10px;padding:8px;z-index:99999;max-height:40vh;overflow:auto;white-space:pre-wrap;';
document.body.appendChild(debugDiv);

logBoot('Debug overlay created');

// Global error handler
window.onerror = (msg, url, line, col, error) => {
  logBoot(`ERROR: ${msg} at ${url}:${line}`);
  console.error('[BOOT] Global error:', msg, url, line, col, error);
  return false;
};
window.onunhandledrejection = (event) => {
  logBoot(`UNHANDLED: ${event.reason}`);
  console.error('[BOOT] Unhandled rejection:', event.reason);
};

const root = ReactDOM.createRoot(document.getElementById('root')!);

logBoot('Root element: ' + (document.getElementById('root') ? 'OK' : 'MISSING'));

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
logBoot(`isAdminRoute: ${isAdminRoute}, hash: ${window.location.hash}`);

if (isAdminRoute) {
  // Admin page works without Telegram SDK
  logBoot('Rendering AdminRoot');
  root.render(
    <StrictMode>
      <AdminRoot />
    </StrictMode>,
  );
} else {
  // Normal Telegram Mini App flow
  logBoot('Starting Telegram Mini App flow');
  try {
    logBoot('Calling retrieveLaunchParams...');
    const launchParams = retrieveLaunchParams();
    logBoot(`Platform: ${launchParams.tgWebAppPlatform}, Version: ${launchParams.tgWebAppVersion}`);
    const { tgWebAppPlatform: platform } = launchParams;
    const debug = (launchParams.tgWebAppStartParam || '').includes('debug')
      || import.meta.env.DEV;

    // Configure all application dependencies.
    logBoot(`Calling init() debug=${debug} platform=${platform}`);
    init({
      debug,
      eruda: debug && ['ios', 'android'].includes(platform),
      mockForMacOS: platform === 'macos',
    })
      .then(() => {
        logBoot('init() resolved, rendering Root');
        // Hide debug overlay after successful boot (with delay)
        setTimeout(() => {
          const el = document.getElementById('boot-debug');
          if (el) el.style.display = 'none';
        }, 3000);
        root.render(
          <StrictMode>
            <Root/>
          </StrictMode>,
        );
      })
      .catch((e) => {
        logBoot(`init() FAILED: ${e?.message || e}`);
        showError(`Init error: ${e?.message || 'Unknown error'}`);
      });
  } catch (e: any) {
    logBoot(`Launch params ERROR: ${e?.message || e}`);
    try {
      logBoot('Rendering EnvUnsupported');
      root.render(<EnvUnsupported/>);
    } catch (e2: any) {
      logBoot(`EnvUnsupported FAILED: ${e2?.message || e2}`);
      showError('Telegram SDK unavailable');
    }
  }
}
