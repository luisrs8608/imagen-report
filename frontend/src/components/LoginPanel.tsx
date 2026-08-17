import { FormEvent, useState } from 'react';
import { KeyRound, Loader2, LockKeyhole, MailCheck } from 'lucide-react';

import { apiRequest } from '../lib/api';
import type { LoginChallenge, User } from '../lib/types';

interface LoginPanelProps {
  onAuthenticated: (user: User) => void;
}

export function LoginPanel({ onAuthenticated }: LoginPanelProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [challenge, setChallenge] = useState<LoginChallenge | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function requestCode(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const nextChallenge = await apiRequest<LoginChallenge>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      setChallenge(nextChallenge);
      setCode('');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible iniciar sesión.');
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(event: FormEvent) {
    event.preventDefault();
    if (!challenge) return;
    setBusy(true);
    setError('');
    try {
      const user = await apiRequest<User>('/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ challenge_id: challenge.challenge_id, code }),
      });
      onAuthenticated(user);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible verificar el código.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-card" aria-labelledby="login-title">
        <div className="brand-mark"><LockKeyhole size={24} /></div>
        <p className="eyebrow">Acceso institucional</p>
        <h1 id="login-title">Imagen Report</h1>
        <p className="muted">Generación segura de informes radiológicos.</p>

        {!challenge ? (
          <form onSubmit={requestCode} className="stack-lg">
            <label>
              Usuario
              <input
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </label>
            <label>
              Contraseña
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={8}
                required
              />
            </label>
            <button type="submit" className="primary-button" disabled={busy}>
              {busy ? <Loader2 className="spin" size={18} /> : <KeyRound size={18} />}
              Enviar código
            </button>
          </form>
        ) : (
          <form onSubmit={verifyCode} className="stack-lg">
            <div className="notice success">
              <MailCheck size={18} />
              Enviamos un código a {challenge.masked_email}.
            </div>
            {challenge.development_code && (
              <div className="development-code">
                Código de desarrollo: <strong>{challenge.development_code}</strong>
              </div>
            )}
            <label>
              Código de seis dígitos
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                pattern="\d{6}"
                required
              />
            </label>
            <button type="submit" className="primary-button" disabled={busy || code.length !== 6}>
              {busy ? <Loader2 className="spin" size={18} /> : <MailCheck size={18} />}
              Verificar y entrar
            </button>
            <button type="button" className="text-button" onClick={() => setChallenge(null)}>
              Volver al acceso
            </button>
          </form>
        )}

        {error && <div className="notice error" role="alert">{error}</div>}
      </section>
    </main>
  );
}

