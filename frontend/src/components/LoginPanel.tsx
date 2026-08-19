import { FormEvent, useState } from 'react';
import {
  FileCheck2,
  KeyRound,
  Loader2,
  LockKeyhole,
  MailCheck,
  Mic,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

import { apiRequest } from '../lib/api';
import type { LoginChallenge, User } from '../lib/types';
import { ThemeToggle, type ColorTheme } from './ThemeToggle';

interface LoginPanelProps {
  theme: ColorTheme;
  onToggleTheme: () => void;
  onAuthenticated: (user: User) => void;
}

export function LoginPanel({ theme, onToggleTheme, onAuthenticated }: LoginPanelProps) {
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
    <main className="auth-shell" id="main-content">
      <a className="skip-link" href="#login-title">Saltar al formulario de acceso</a>
      <div className="auth-layout">
        <section className="auth-context" aria-labelledby="product-title">
          <div className="auth-brand">
            <div className="brand-mark"><LockKeyhole size={24} aria-hidden="true" /></div>
            <div>
              <p className="eyebrow">Flujo clínico asistido</p>
              <h1 id="product-title">Imagen Report</h1>
            </div>
          </div>
          <p className="auth-lead">
            Del dictado al documento final, con revisión profesional en cada informe.
          </p>
          <ol className="auth-flow" aria-label="Flujo de creación del informe">
            <li><span><Mic size={17} aria-hidden="true" /></span><div><strong>Capture el dictado</strong><small>Transcriba y corrija el texto original.</small></div></li>
            <li><span><Sparkles size={17} aria-hidden="true" /></span><div><strong>Genere el borrador</strong><small>Elija el modelo de IA adecuado.</small></div></li>
            <li><span><FileCheck2 size={17} aria-hidden="true" /></span><div><strong>Revise y publique</strong><small>Cree el documento y el PDF en Drive.</small></div></li>
          </ol>
          <div className="auth-trust"><ShieldCheck size={17} aria-hidden="true" /> El informe siempre requiere aprobación profesional.</div>
        </section>

        <section className="auth-card" aria-labelledby="login-title">
          <ThemeToggle theme={theme} onToggle={onToggleTheme} className="auth-theme-toggle" />
          <div className="auth-card-heading">
            <p className="eyebrow">Acceso institucional</p>
            <h2 id="login-title">Iniciar sesión</h2>
            <p className="muted">Use sus credenciales y el código enviado a su correo.</p>
          </div>

          {!challenge ? (
            <form onSubmit={requestCode} className="stack-lg">
              <label>
                Usuario
                <input
                  name="username"
                  autoComplete="username"
                  spellCheck={false}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  required
                />
              </label>
              <label>
                Contraseña
                <input
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  minLength={8}
                  required
                />
              </label>
              <button type="submit" className="primary-button auth-submit" disabled={busy}>
                {busy ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <KeyRound size={18} aria-hidden="true" />}
                {busy ? 'Enviando…' : 'Enviar código'}
              </button>
            </form>
          ) : (
            <form onSubmit={verifyCode} className="stack-lg">
              <div className="notice success" role="status" aria-live="polite">
                <MailCheck size={18} aria-hidden="true" />
                <span>Enviamos un código a <strong className="breakable">{challenge.masked_email}</strong>.</span>
              </div>
              {challenge.development_code && (
                <div className="development-code">
                  Código de desarrollo: <strong>{challenge.development_code}</strong>
                </div>
              )}
              <label>
                Código de seis dígitos
                <input
                  name="otp"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  spellCheck={false}
                  value={code}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                  pattern="\d{6}"
                  placeholder="000000"
                  required
                />
              </label>
              <button type="submit" className="primary-button auth-submit" disabled={busy || code.length !== 6}>
                {busy ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <MailCheck size={18} aria-hidden="true" />}
                {busy ? 'Verificando…' : 'Verificar y entrar'}
              </button>
              <button type="button" className="text-button" onClick={() => setChallenge(null)}>
                Volver al acceso
              </button>
            </form>
          )}

          {error && <div className="notice error auth-error" role="alert">{error}</div>}
        </section>
      </div>
    </main>
  );
}
