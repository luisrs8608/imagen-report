import { FormEvent, useEffect, useRef, useState } from 'react';
import {
  CheckCircle2,
  KeyRound,
  Loader2,
  Save,
  ShieldCheck,
  UserCheck,
  UserPlus,
  UsersRound,
  UserX,
  X,
} from 'lucide-react';

import { apiRequest } from '../lib/api';
import type { AdminUser, User } from '../lib/types';

interface UserManagementPanelProps {
  currentUser: User;
  onClose: () => void;
  onCurrentUserPasswordReset: () => void;
}

interface CreateUserForm {
  username: string;
  email: string;
  password: string;
  is_admin: boolean;
}

const emptyCreateForm: CreateUserForm = {
  username: '',
  email: '',
  password: '',
  is_admin: false,
};

export function UserManagementPanel({
  currentUser,
  onClose,
  onCurrentUserPasswordReset,
}: UserManagementPanelProps) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [emailDrafts, setEmailDrafts] = useState<Record<number, string>>({});
  const [createForm, setCreateForm] = useState<CreateUserForm>(emptyCreateForm);
  const [resetUserId, setResetUserId] = useState<number | null>(null);
  const [resetPassword, setResetPassword] = useState('');
  const [busyKey, setBusyKey] = useState<string | null>('load');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    const previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    document.body.style.overflow = 'hidden';
    window.requestAnimationFrame(() => closeButtonRef.current?.focus());
    const handleDialogKeyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !overlayRef.current) return;

      const focusable = Array.from(overlayRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      ));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', handleDialogKeyboard);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleDialogKeyboard);
      previouslyFocused?.focus();
    };
  }, [onClose]);

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    setBusyKey('load');
    setError('');
    try {
      const loadedUsers = await apiRequest<AdminUser[]>('/admin/users');
      setUsers(loadedUsers);
      setEmailDrafts(Object.fromEntries(loadedUsers.map((user) => [user.id, user.email])));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible cargar los usuarios.');
    } finally {
      setBusyKey(null);
    }
  }

  function replaceUser(updatedUser: AdminUser) {
    setUsers((current) => current.map((user) => (user.id === updatedUser.id ? updatedUser : user)));
    setEmailDrafts((current) => ({ ...current, [updatedUser.id]: updatedUser.email }));
  }

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setBusyKey('create');
    setError('');
    setSuccess('');
    try {
      const created = await apiRequest<AdminUser>('/admin/users', {
        method: 'POST',
        body: JSON.stringify(createForm),
      });
      setUsers((current) => [...current, created].sort((a, b) => a.username.localeCompare(b.username)));
      setEmailDrafts((current) => ({ ...current, [created.id]: created.email }));
      setCreateForm(emptyCreateForm);
      setSuccess(`Usuario ${created.username} creado correctamente.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible crear el usuario.');
    } finally {
      setBusyKey(null);
    }
  }

  async function updateUser(user: AdminUser, changes: Partial<Pick<AdminUser, 'email' | 'is_active' | 'is_admin'>>, message: string) {
    const actionKey = `update-${user.id}`;
    setBusyKey(actionKey);
    setError('');
    setSuccess('');
    try {
      const updated = await apiRequest<AdminUser>(`/admin/users/${user.id}`, {
        method: 'PATCH',
        body: JSON.stringify(changes),
      });
      replaceUser(updated);
      setSuccess(message);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible actualizar el usuario.');
    } finally {
      setBusyKey(null);
    }
  }

  async function saveEmail(user: AdminUser) {
    const email = (emailDrafts[user.id] || '').trim();
    if (!email || email === user.email) return;
    await updateUser(user, { email }, `Correo de ${user.username} actualizado.`);
  }

  async function toggleActive(user: AdminUser) {
    const action = user.is_active ? 'desactivar' : 'activar';
    if (!window.confirm(`¿Deseas ${action} al usuario ${user.username}?`)) return;
    await updateUser(
      user,
      { is_active: !user.is_active },
      `Usuario ${user.username} ${user.is_active ? 'desactivado' : 'activado'}.`,
    );
  }

  async function toggleAdmin(user: AdminUser) {
    const action = user.is_admin ? 'quitar el rol de administrador a' : 'hacer administrador a';
    if (!window.confirm(`¿Deseas ${action} ${user.username}?`)) return;
    await updateUser(
      user,
      { is_admin: !user.is_admin },
      `Rol de ${user.username} actualizado.`,
    );
  }

  async function resetUserPassword(event: FormEvent, user: AdminUser) {
    event.preventDefault();
    setBusyKey(`password-${user.id}`);
    setError('');
    setSuccess('');
    try {
      await apiRequest<void>(`/admin/users/${user.id}/reset-password`, {
        method: 'POST',
        body: JSON.stringify({ password: resetPassword }),
      });
      setResetPassword('');
      setResetUserId(null);
      if (user.id === currentUser.id) {
        onCurrentUserPasswordReset();
        return;
      }
      setSuccess(`Contraseña de ${user.username} restablecida. Sus sesiones anteriores fueron cerradas.`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No fue posible restablecer la contraseña.');
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div ref={overlayRef} className="admin-overlay" role="dialog" aria-modal="true" aria-labelledby="user-management-title">
      <section className="admin-panel">
        <header className="admin-panel-header">
          <div>
            <span className="admin-panel-icon"><UsersRound size={22} /></span>
            <div>
              <p className="eyebrow">Administración</p>
              <h1 id="user-management-title">Gestión de usuarios</h1>
              <p>Solo las cuentas creadas aquí pueden acceder a la aplicación.</p>
            </div>
          </div>
          <button ref={closeButtonRef} type="button" className="icon-button" onClick={onClose} aria-label="Cerrar gestión de usuarios">
            <X size={19} />
          </button>
        </header>

        <div className="admin-panel-body">
          {error && <div className="notice error" role="alert">{error}</div>}
          {success && <div className="notice success" role="status" aria-live="polite"><CheckCircle2 size={18} />{success}</div>}

          <div className="admin-layout">
            <form className="user-create-card" onSubmit={createUser}>
              <div className="section-title">
                <UserPlus size={19} />
                <div><h2>Crear usuario</h2><p>Defina el acceso inicial y el correo que recibirá el OTP.</p></div>
              </div>
              <label>
                Usuario
                <input
                  name="username"
                  autoComplete="off"
                  spellCheck={false}
                  value={createForm.username}
                  onChange={(event) => setCreateForm((current) => ({ ...current, username: event.target.value.toLowerCase() }))}
                  minLength={3}
                  maxLength={80}
                  pattern="[a-zA-Z0-9_.-]+"
                  placeholder="Ej.: doctor.apellido…"
                  required
                />
              </label>
              <label>
                Correo para el OTP
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  spellCheck={false}
                  value={createForm.email}
                  onChange={(event) => setCreateForm((current) => ({ ...current, email: event.target.value }))}
                  placeholder="Ej.: doctor@gmail.com…"
                  required
                />
              </label>
              <label>
                Contraseña inicial
                <input
                  name="password"
                  type="password"
                  value={createForm.password}
                  onChange={(event) => setCreateForm((current) => ({ ...current, password: event.target.value }))}
                  minLength={12}
                  autoComplete="new-password"
                  placeholder="Mínimo 12 caracteres…"
                  required
                />
              </label>
              <label className="admin-check">
                <input
                  name="is_admin"
                  type="checkbox"
                  checked={createForm.is_admin}
                  onChange={(event) => setCreateForm((current) => ({ ...current, is_admin: event.target.checked }))}
                />
                <span><strong>Otorgar rol de administrador</strong><small>Podrá crear y modificar otros usuarios.</small></span>
              </label>
              <button type="submit" className="primary-button" disabled={busyKey !== null}>
                {busyKey === 'create' ? <Loader2 className="spin" size={18} /> : <UserPlus size={18} />}
                Crear usuario
              </button>
            </form>

            <section className="user-list-card">
              <div className="section-title list-title">
                <UsersRound size={19} />
                <div><h2>Usuarios autorizados</h2><p>{users.length} usuario{users.length === 1 ? '' : 's'} registrado{users.length === 1 ? '' : 's'}.</p></div>
                <button type="button" className="text-button" onClick={loadUsers} disabled={busyKey !== null}>Actualizar</button>
              </div>

              {busyKey === 'load' ? (
                <div className="admin-loading"><Loader2 className="spin" size={24} /> Cargando usuarios…</div>
              ) : (
                <div className="admin-user-list">
                  {users.map((user) => {
                    const isSelf = user.id === currentUser.id;
                    const emailChanged = (emailDrafts[user.id] || '').trim() !== user.email;
                    return (
                      <article className={`admin-user-row ${user.is_active ? '' : 'inactive'}`} key={user.id}>
                        <div className="admin-user-summary">
                          <div className="user-avatar">{user.username.slice(0, 2).toUpperCase()}</div>
                          <div>
                            <strong>{user.username}{isSelf ? ' (tú)' : ''}</strong>
                            <div className="user-badges">
                              <span className={user.is_active ? 'active' : 'inactive'}>{user.is_active ? 'Activo' : 'Inactivo'}</span>
                              {user.is_admin && <span className="admin"><ShieldCheck size={12} /> Administrador</span>}
                            </div>
                          </div>
                        </div>

                        <div className="admin-email-editor">
                          <input
                            name={`email-${user.id}`}
                            type="email"
                            aria-label={`Correo de ${user.username}`}
                            autoComplete="off"
                            spellCheck={false}
                            value={emailDrafts[user.id] || ''}
                            onChange={(event) => setEmailDrafts((current) => ({ ...current, [user.id]: event.target.value }))}
                          />
                          <button type="button" className="compact-button" onClick={() => saveEmail(user)} disabled={!emailChanged || busyKey !== null}>
                            <Save size={14} /> Guardar correo
                          </button>
                        </div>

                        <div className="admin-user-actions">
                          <button type="button" onClick={() => toggleActive(user)} disabled={isSelf || busyKey !== null}>
                            {user.is_active ? <UserX size={15} /> : <UserCheck size={15} />}
                            {user.is_active ? 'Desactivar' : 'Activar'}
                          </button>
                          <button type="button" onClick={() => toggleAdmin(user)} disabled={isSelf || busyKey !== null}>
                            <ShieldCheck size={15} /> {user.is_admin ? 'Quitar admin' : 'Hacer admin'}
                          </button>
                          <button type="button" onClick={() => { setResetUserId(user.id); setResetPassword(''); setError(''); setSuccess(''); }} disabled={busyKey !== null}>
                            <KeyRound size={15} /> Restablecer contraseña
                          </button>
                        </div>

                        {resetUserId === user.id && (
                          <form className="password-reset-row" onSubmit={(event) => resetUserPassword(event, user)}>
                            <label>
                              Nueva contraseña para {user.username}
                              <input name={`password-${user.id}`} type="password" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} minLength={12} autoComplete="new-password" placeholder="Mínimo 12 caracteres…" required />
                            </label>
                            <div>
                              <button type="button" className="text-button" onClick={() => { setResetUserId(null); setResetPassword(''); }}>Cancelar</button>
                              <button type="submit" className="primary-button" disabled={resetPassword.length < 12 || busyKey !== null}>
                                {busyKey === `password-${user.id}` ? <Loader2 className="spin" size={16} /> : <KeyRound size={16} />}
                                Guardar contraseña
                              </button>
                            </div>
                          </form>
                        )}
                      </article>
                    );
                  })}
                </div>
              )}
            </section>
          </div>
        </div>
      </section>
    </div>
  );
}
