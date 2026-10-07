import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setToken } from '../lib/api';
import { useToast } from '../components/Toast';
import type { Me } from '../lib/api';

export default function AuthPage({ onLogin }: { onLogin: (me: Me) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  async function submit(kind: 'login' | 'register' | 'demo') {
    if (busy) return;
    setBusy(true);
    try {
      let body: Record<string, string | boolean>;
      if (kind === 'demo') body = { name: 'Tharun Demo', email: 'demo@virelle.app', password: 'tasteflow-demo', demo: true };
      else if (kind === 'login') body = { email, password };
      else body = { name, email, password };
      let res;
      try {
        res = await api<{ token: string; user: Me }>('/api/auth/' + (kind === 'register' ? 'register' : 'login'), {
          method: 'POST',
          body: JSON.stringify(body),
        });
      } catch (e) {
        if (kind === 'demo') {
          res = await api<{ token: string; user: Me }>('/api/auth/register', { method: 'POST', body: JSON.stringify(body) });
        } else throw e;
      }
      setToken(res!.token);
      onLogin(res!.user);
      navigate(res!.user.has_preferences ? '/' : '/onboarding');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Authentication failed', false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 860 }} className="auth-wrap">
      <div className="card auth-split">
        <div className="auth-brand">
          <img src="/assets/virelle-mark.svg" alt="Virelle" width={56} height={56} />
          <h1>Virelle</h1>
          <p className="auth-tag">Know what to cook.</p>
          <ul className="auth-points">
            <li>Recommendations that learn your taste</li>
            <li>Pantry-aware dinner answers</li>
            <li>Weekly plan + shopping list</li>
          </ul>
        </div>
        <div className="auth-form">
          <div className="row auth-tabs" role="tablist">
            <button className={'ghost' + (mode === 'login' ? ' sel' : '')} role="tab" onClick={() => setMode('login')}>Log in</button>
            <button className={mode === 'register' ? '' : 'ghost'} role="tab" onClick={() => setMode('register')}>Sign up</button>
          </div>
        {mode === 'register' && (
          <>
            <label className="f">Your name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Tharun" />
          </>
        )}
        <label className="f">Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
        <label className="f">Password{minLengthWarning(mode)}</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
        <p><button style={{ width: '100%' }} disabled={busy} onClick={() => submit(mode)}>{busy ? 'Working…' : mode === 'login' ? 'Log in' : 'Create account →'}</button></p>
        <p className="small muted">Just looking? <a href="#" onClick={(e) => { e.preventDefault(); submit('demo'); }}>Try the demo account</a></p>
        </div>
      </div>
    </main>
  );
}

function minLengthWarning(mode: string): string {
  return mode === 'register' ? ' (min 6 characters)' : '';
}
