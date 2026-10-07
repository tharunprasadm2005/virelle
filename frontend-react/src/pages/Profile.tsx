import { useEffect, useState } from 'react';
import { api, clearToken, type Me } from '../lib/api';
import { useToast } from '../components/Toast';
import Layout from '../components/Layout';
import { useNavigate } from 'react-router-dom';

const GOALS = ['high protein', 'lighter meals', 'calorie aware', 'balanced'];

interface Profile {
  id: number;
  name: string;
  email: string;
  member_since: string;
  preferences: {
    diet: string;
    cuisines: string[];
    priorities: string[];
    avoid_ingredients: string[];
    max_minutes: number | null;
    nutrition_goals: string[];
  };
}

interface Imported {
  id: number;
  title: string;
  source_name: string;
}

interface Collection {
  id: number;
  name: string;
  recipes?: { name: string }[];
}

export default function Profile({ me }: { me: Me | null }) {
  const [p, setP] = useState<Profile | null>(null);
  const [name, setName] = useState('');
  const [goals, setGoals] = useState<string[]>([]);
  const [cp, setCp] = useState('');
  const [np, setNp] = useState('');
  const [imports, setImports] = useState<Imported[]>([]);
  const [colls, setColls] = useState<Collection[]>([]);
  const [cn, setCn] = useState('');
  const toast = useToast();
  const navigate = useNavigate();

  async function load() {
    const prof = await api<Profile>('/api/profile');
    setP(prof);
    setName(prof.name);
    setGoals(prof.preferences.nutrition_goals || []);
    api<{ imports: Imported[] }>('/api/imports').then((r) => setImports(r.imports)).catch(() => {});
    api<{ collections: Collection[] }>('/api/collections').then(async (r) => {
      const full = await Promise.all(r.collections.map(async (c) => {
        const d = await api<{ recipes: { name: string }[] }>(`/api/collections/${c.id}`).catch(() => ({ recipes: [] as { name: string }[] }));
        return { ...c, recipes: d.recipes };
      }));
      setColls(full);
    }).catch(() => {});
  }

  useEffect(() => {
    load();
  }, []);

  async function saveGoals() {
    const cur = await api<Record<string, unknown>>('/api/preferences');
    await api('/api/preferences', { method: 'PUT', body: JSON.stringify({ ...cur, diet: (cur.diet as string) || '', nutrition_goals: goals }) })
      .catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
    toast('Nutrition goals saved.');
    load();
  }

  if (!p) return <Layout name={me?.name}><p className="muted">Loading…</p></Layout>;
  const pr = p.preferences;

  return (
    <Layout name={me?.name}>
      <h1>Profile</h1>
      <div className="card profile-hero">
        <div className="avatar">{(p.name || '?').trim().charAt(0).toUpperCase()}</div>
        <div>
          <h2 style={{ margin: '0 0 .15rem' }}>{p.name}</h2>
          <p className="muted" style={{ margin: 0 }}>{p.email}</p>
          <p className="small muted" style={{ margin: '.15rem 0 0' }}>Cooking with Virelle since {p.member_since.slice(0, 10)}</p>
        </div>
      </div>
      <div className="card">
        <h2>Edit profile</h2>
        <label className="f">Display name</label>
        <div className="row">
          <input value={name} onChange={(e) => setName(e.target.value)} style={{ flex: 1 }} />
          <button onClick={async () => {
            if (name.trim()) await api('/api/profile', { method: 'PUT', body: JSON.stringify({ name: name.trim() }) }).catch((e) => toast(e.message, false));
            load();
          }}>Save</button>
        </div>
      </div>
      <div className="card">
        <h2>Food preferences</h2>
        <p><strong>Diet:</strong> {pr.diet || '—'}</p>
        <p><strong>Cuisines:</strong> {(pr.cuisines || []).join(', ') || '—'}</p>
        <p><strong>Priorities:</strong> {(pr.priorities || []).join(', ') || '—'}</p>
        <p><strong>Avoids:</strong> {(pr.avoid_ingredients || []).join(', ') || '—'}</p>
        {pr.max_minutes && <p><strong>Max time:</strong> {pr.max_minutes} min</p>}
        <p><strong>Nutrition goals:</strong> {(pr.nutrition_goals || []).join(', ') || '—'}</p>
        <div className="pill-group">
          {GOALS.map((g) => (
            <button key={g} className={'pill' + (goals.includes(g) ? ' sel' : '')}
              onClick={() => setGoals((gs) => (gs.includes(g) ? gs.filter((x) => x !== g) : [...gs, g]))}>{g}</button>
          ))}
        </div>
        <p><button onClick={saveGoals}>Save nutrition goals</button></p>
        <p><a href="/onboarding">Update all preferences →</a></p>
      </div>
      <div className="card">
        <h2>Change password</h2>
        <label className="f">Current password</label>
        <input type="password" value={cp} onChange={(e) => setCp(e.target.value)} />
        <label className="f">New password</label>
        <input type="password" value={np} onChange={(e) => setNp(e.target.value)} />
        <p><button onClick={async () => {
          try {
            await api('/api/profile/password', { method: 'POST', body: JSON.stringify({ current_password: cp, new_password: np }) });
            toast('Password changed.');
            setCp('');
            setNp('');
          } catch (e) { toast(e instanceof Error ? e.message : 'Failed', false); }
        }}>Change password</button></p>
      </div>
      <div className="card">
        <h2>My collections</h2>
        <div className="row">
          <input value={cn} onChange={(e) => setCn(e.target.value)} placeholder="New collection name..." style={{ flex: 1 }} />
          <button onClick={async () => {
            if (!cn.trim()) return;
            await api('/api/collections', { method: 'POST', body: JSON.stringify({ name: cn.trim() }) }).catch((e) => toast(e.message, false));
            setCn('');
            load();
          }}>Create</button>
        </div>
        {colls.map((c) => (
          <p key={c.id}><strong>{c.name}</strong> ({(c.recipes || []).length}){' '}
            <a href="#" onClick={async (e) => { e.preventDefault(); await api(`/api/collections/${c.id}`, { method: 'DELETE' }).catch(() => {}); load(); }}>✕</a>
            <br /><span className="small muted">{(c.recipes || []).slice(0, 5).map((r) => r.name).join(' · ') || 'empty'}</span></p>
        ))}
      </div>
      <div className="card">
        <h2>My imports</h2>
        {imports.map((i) => (
          <p key={i.id}><strong>{i.title}</strong> <span className="muted small">from {i.source_name} · Imported</span>{' '}
            <a href="#" onClick={async (e) => { e.preventDefault(); await api(`/api/imports/${i.id}`, { method: 'DELETE' }).catch(() => {}); load(); }}>✕</a></p>
        ))}
        {!imports.length && <p className="muted">No imports yet — paste a recipe URL on Discover.</p>}
      </div>
      <div className="card">
        <h2>Account</h2>
        <button className="ghost" onClick={() => { clearToken(); navigate('/auth'); }}>Log out</button>
      </div>
    </Layout>
  );
}
