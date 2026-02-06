import {
  setDebug,
  themeParams,
  initData,
  viewport,
  init as initSDK,
  mockTelegramEnv,
  retrieveLaunchParams,
  emitEvent,
  miniApp,
  backButton,
} from '@tma.js/sdk-react';

// Helper to log to debug overlay
function logInit(msg: string) {
  console.log('[INIT]', msg);
  const debugEl = document.getElementById('boot-debug');
  if (debugEl) {
    debugEl.innerText += `\n${new Date().toISOString().slice(11,23)} [INIT] ${msg}`;
  }
}

/**
 * Initializes the application and configures its dependencies.
 */
export async function init(options: {
  debug: boolean;
  eruda: boolean;
  mockForMacOS: boolean;
}): Promise<void> {
  logInit('Starting init()');

  // Set @telegram-apps/sdk-react debug mode and initialize it.
  setDebug(options.debug);
  logInit('setDebug done, calling initSDK()');
  initSDK();
  logInit('initSDK() done');

  // Add Eruda if needed.
  options.eruda && void import('eruda').then(({ default: eruda }) => {
    eruda.init();
    eruda.position({ x: window.innerWidth - 50, y: 0 });
  });

  // Telegram for macOS has a ton of bugs, including cases, when the client doesn't
  // even response to the "web_app_request_theme" method. It also generates an incorrect
  // event for the "web_app_request_safe_area" method.
  if (options.mockForMacOS) {
    let firstThemeSent = false;
    mockTelegramEnv({
      onEvent(event, next) {
        if (event.name === 'web_app_request_theme') {
          let tp: any;
          if (firstThemeSent) {
            tp = themeParams.state();
          } else {
            firstThemeSent = true;
            tp = retrieveLaunchParams().tgWebAppThemeParams || {};
          }
          return emitEvent('theme_changed', { theme_params: tp });
        }

        if (event.name === 'web_app_request_safe_area') {
          return emitEvent('safe_area_changed', { left: 0, top: 0, right: 0, bottom: 0 });
        }

        next();
      },
    });
  }

  // Mount all components used in the project.
  logInit('Mounting components...');
  backButton.mount.ifAvailable();
  initData.restore();
  logInit('backButton and initData done');

  if (miniApp.mount.isAvailable()) {
    logInit('miniApp.mount available, mounting...');
    themeParams.mount();
    miniApp.mount();
    themeParams.bindCssVars();
    logInit('miniApp mounted');
  } else {
    logInit('WARN: miniApp.mount NOT available');
  }

  if (viewport.mount.isAvailable()) {
    logInit('viewport.mount available, mounting...');
    viewport.mount().then(() => {
      viewport.bindCssVars();
      logInit('viewport mounted');
    }).catch(e => {
      logInit(`viewport.mount FAILED: ${e?.message || e}`);
    });
  } else {
    logInit('WARN: viewport.mount NOT available');
  }

  logInit('init() complete');
}