/**
 * Test utilities for component testing
 * Provides custom render functions with required providers
 */

import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AppRoot } from '@telegram-apps/telegram-ui';

/**
 * Custom render function that wraps components with required providers
 * - AppRoot for Telegram UI components
 * - BrowserRouter for routing components
 */
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AppRoot>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </AppRoot>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

// Re-export everything from @testing-library/react
export * from '@testing-library/react';

// Override render with our custom version
export { customRender as render };
