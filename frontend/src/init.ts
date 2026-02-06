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

/**
 * Initializes the application and configures its dependencies.
 */
export async function init(options: {
  debug: boolean;
  eruda: boolean;
  mockForMacOS: boolean;
}): Promise<void> {
  console.log('[INIT] Starting init()');

  // Set @telegram-apps/sdk-react debug mode and initialize it.
  setDebug(options.debug);
  console.log('[INIT] setDebug done, calling initSDK()');
  initSDK();
  console.log('[INIT] initSDK() done');

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
  console.log('[INIT] Mounting components...');
  backButton.mount.ifAvailable();
  initData.restore();
  console.log('[INIT] backButton and initData done');

  if (miniApp.mount.isAvailable()) {
    console.log('[INIT] miniApp.mount is available, mounting...');
    themeParams.mount();
    miniApp.mount();
    themeParams.bindCssVars();
    console.log('[INIT] miniApp mounted');
  } else {
    console.warn('[INIT] miniApp.mount is NOT available');
  }

  if (viewport.mount.isAvailable()) {
    console.log('[INIT] viewport.mount is available, mounting...');
    viewport.mount().then(() => {
      viewport.bindCssVars();
      console.log('[INIT] viewport mounted and CSS vars bound');
    }).catch(e => {
      console.error('[INIT] viewport.mount() failed:', e);
    });
  } else {
    console.warn('[INIT] viewport.mount is NOT available');
  }

  console.log('[INIT] init() complete');
}