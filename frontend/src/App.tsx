import { useEffect, useLayoutEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { LoginPanel } from './components/LoginPanel';
import { ReportWorkspace } from './components/ReportWorkspace';
import type { ColorTheme } from './components/ThemeToggle';
import { ApiError, apiRequest } from './lib/api';
import type { User } from './lib/types';

const THEME_STORAGE_KEY = 'imagen-report:color-theme';

function getInitialTheme(): ColorTheme {
  try {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (storedTheme === 'light' || storedTheme === 'dark') return storedTheme;
  } catch {
    // La preferencia del sistema sigue disponible si el navegador bloquea el almacenamiento.
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [theme, setTheme] = useState<ColorTheme>(getInitialTheme);

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content',
      theme === 'dark' ? '#0b151a' : '#f3f6f8',
    );
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // El tema continúa activo durante la sesión aunque no pueda persistirse.
    }
  }, [theme]);

  useEffect(() => {
    apiRequest<User>('/auth/me')
      .then(setUser)
      .catch((error: unknown) => {
        if (!(error instanceof ApiError) || error.status !== 401) {
          console.error('No fue posible comprobar la sesión.', error);
        }
      })
      .finally(() => setCheckingSession(false));
  }, []);

  if (checkingSession) {
    return (
      <main className="loading-screen" role="status" aria-live="polite">
        <Loader2 className="spin" size={28} />
        Comprobando sesión…
      </main>
    );
  }

  if (!user) {
    return (
      <LoginPanel
        theme={theme}
        onToggleTheme={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}
        onAuthenticated={setUser}
      />
    );
  }

  return (
    <ReportWorkspace
      user={user}
      theme={theme}
      onToggleTheme={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}
      onLogout={() => setUser(null)}
    />
  );
}
