/**
 * Error Fallback Components
 * Reusable error UI for different scenarios
 */

import { memo, type FC } from 'react';
import { Placeholder } from '@telegram-apps/telegram-ui';
import { APIError } from '@/services/api';

import './ErrorFallbacks.css';

export interface ErrorFallbackProps {
  error: unknown;
  reset?: () => void;
}

/**
 * Helper to compare error fallback props
 */
function errorPropsAreEqual(
  prev: ErrorFallbackProps,
  next: ErrorFallbackProps
): boolean {
  // Compare error messages
  const prevMessage = prev.error instanceof Error ? prev.error.message : String(prev.error);
  const nextMessage = next.error instanceof Error ? next.error.message : String(next.error);

  // Compare reset function reference
  return prevMessage === nextMessage && prev.reset === next.reset;
}

/**
 * Generic error fallback with retry button
 */
const GenericErrorFallbackComponent: FC<ErrorFallbackProps> = ({ error, reset }) => {
  const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';

  return (
    <div className="error-fallback">
      <Placeholder
        header="Что-то пошло не так"
        description={errorMessage}
        action={
          reset && (
            <button onClick={reset} className="error-fallback__retry">
              Попробовать снова
            </button>
          )
        }
      />
    </div>
  );
};

export const GenericErrorFallback = memo(GenericErrorFallbackComponent, errorPropsAreEqual);

/**
 * API error fallback with specific messages
 */
const APIErrorFallbackComponent: FC<ErrorFallbackProps> = ({ error, reset }) => {
  let header = 'Ошибка';
  let description = 'Не удалось загрузить данные';

  if (error instanceof APIError) {
    if (error.status === 0) {
      header = 'Нет соединения';
      description = 'Проверьте подключение к интернету';
    } else if (error.status === 401 || error.status === 403) {
      header = 'Ошибка авторизации';
      description = 'Перезапустите приложение';
    } else if (error.status === 404) {
      header = 'Не найдено';
      description = 'Запрашиваемые данные не найдены';
    } else if (error.status === 429) {
      header = 'Слишком много запросов';
      description = 'Подождите немного и попробуйте снова';
    } else if (error.status >= 500) {
      header = 'Ошибка сервера';
      description = 'Сервер временно недоступен';
    }
  }

  return (
    <div className="error-fallback">
      <Placeholder
        header={header}
        description={description}
        action={
          reset && (
            <button onClick={reset} className="error-fallback__retry">
              Попробовать снова
            </button>
          )
        }
      />
    </div>
  );
};

export const APIErrorFallback = memo(APIErrorFallbackComponent, errorPropsAreEqual);

/**
 * Component-level error fallback (smaller, inline)
 */
const ComponentErrorFallbackComponent: FC<ErrorFallbackProps> = ({ error, reset }) => {
  const errorMessage = error instanceof Error ? error.message : 'Ошибка загрузки';

  return (
    <div className="error-fallback error-fallback--compact">
      <div className="error-fallback__content">
        <p className="error-fallback__message">⚠️ {errorMessage}</p>
        {reset && (
          <button onClick={reset} className="error-fallback__retry error-fallback__retry--small">
            Повторить
          </button>
        )}
      </div>
    </div>
  );
};

export const ComponentErrorFallback = memo(ComponentErrorFallbackComponent, errorPropsAreEqual);

/**
 * Full page error fallback
 */
const PageErrorFallbackComponent: FC<ErrorFallbackProps> = ({ error, reset }) => {
  const errorMessage = error instanceof Error ? error.message : 'Произошла ошибка';
  const isDev = import.meta.env.DEV;

  return (
    <div className="error-fallback error-fallback--page">
      <div className="error-fallback__content">
        <h1 className="error-fallback__title">Упс! 😔</h1>
        <p className="error-fallback__description">Что-то пошло не так</p>
        <p className="error-fallback__message">{errorMessage}</p>

        {isDev && error instanceof Error && error.stack && (
          <details className="error-fallback__details">
            <summary>Детали ошибки (dev mode)</summary>
            <pre className="error-fallback__stack">{error.stack}</pre>
          </details>
        )}

        {reset && (
          <button onClick={reset} className="error-fallback__retry">
            Перезагрузить страницу
          </button>
        )}
      </div>
    </div>
  );
};

export const PageErrorFallback = memo(PageErrorFallbackComponent, errorPropsAreEqual);
