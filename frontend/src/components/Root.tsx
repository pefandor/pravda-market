import { TonConnectUIProvider } from '@tonconnect/ui-react';

import { App } from '@/components/App.tsx';
import { ErrorBoundary } from '@/components/ErrorBoundary.tsx';
import { PageErrorFallback } from '@/components/ErrorFallbacks';
import { AuthProvider } from '@/contexts/AuthContext';
import { publicUrl } from '@/helpers/publicUrl.ts';

export function Root() {
  return (
    <ErrorBoundary fallback={PageErrorFallback}>
      <AuthProvider>
        <TonConnectUIProvider
          manifestUrl={publicUrl('tonconnect-manifest.json')}
        >
          <App/>
        </TonConnectUIProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
