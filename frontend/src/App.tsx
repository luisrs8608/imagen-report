import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { LoginPanel } from './components/LoginPanel';
import { ReportWorkspace } from './components/ReportWorkspace';
import { ApiError, apiRequest } from './lib/api';
import type { User } from './lib/types';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

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
      <div className="loading-screen">
        <Loader2 className="spin" size={28} />
        Comprobando sesión…
      </div>
    );
  }

  if (!user) {
    return <LoginPanel onAuthenticated={setUser} />;
  }

  return <ReportWorkspace user={user} onLogout={() => setUser(null)} />;
}

