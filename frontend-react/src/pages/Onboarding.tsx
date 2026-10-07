import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { useToast } from '../components/Toast';

const DIETS = ['vegetarian', 'non-vegetarian', 'vegan', 'eggetarian'];
const CUISINES = ['indian', 'south indian', 'chinese', 'italian', 'mexican', 'american', 'other'];
const PRIORITIES = ['quick', 'easy', 'healthy', 'high protein', 'budget friendly'];

export default function Onboarding() {
  const [diet, setDiet] = useState('');
  const [cuisines, setCuisines] = useState<string[]>([]);
  const [priorities, setPriorities] = useState<string[]>([]);
  const [avoid, setAvoid] = useState('');
  const [mins, setMins] = useState('');
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  function toggle(list: string[], v: string, set: (x: string[]) => void) {
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  }

  async function save() {
    if (busy) return;
    setBusy(true);
    try {
      await api('/api/preferences', {
        method: 'PUT',
        body: JSON.stringify({
          diet,
          cuisines,
          priorities,
          avoid_ingredients: avoid.split(',').map((s) => s.trim()).filter(Boolean),
          max_minutes: parseInt(mins) || null,
        }),
      });
      navigate('/');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Save failed', false);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 640 }}>
      <div className="card" style={{ marginTop: '2rem' }}>
        <h1>Welcome to Virelle</h1>
        <p>Let's understand your taste.</p>
        <label className="f">What type of food do you prefer?</label>
        <div className="pill-group">
          {DIETS.map((d) => (
            <button key={d} className={'pill' + (diet === d ? ' sel' : '')} onClick={() => setDiet(d)}>
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </button>
          ))}
        </div>
        <label className="f">Favorite cuisines</label>
        <div className="pill-group">
          {CUISINES.map((c) => (
            <button key={c} className={'pill' + (cuisines.includes(c) ? ' sel' : '')} onClick={() => toggle(cuisines, c, setCuisines)}>
              {c.split(' ').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
            </button>
          ))}
        </div>
        <label className="f">What matters to you?</label>
        <div className="pill-group">
          {PRIORITIES.map((p) => (
            <button key={p} className={'pill' + (priorities.includes(p) ? ' sel' : '')} onClick={() => toggle(priorities, p, setPriorities)}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
        <label className="f">Ingredients to avoid (comma separated)</label>
        <input value={avoid} onChange={(e) => setAvoid(e.target.value)} placeholder="e.g. peanuts, mushrooms" />
        <label className="f">Max cooking time (minutes, optional)</label>
        <input type="number" min={5} max={1440} value={mins} onChange={(e) => setMins(e.target.value)} placeholder="e.g. 30" />
        <p><button onClick={save} disabled={busy} style={{ width: '100%' }}>{busy ? 'Saving…' : 'Continue →'}</button></p>
        <p className="small"><a href="/">Skip for now</a></p>
      </div>
    </main>
  );
}
