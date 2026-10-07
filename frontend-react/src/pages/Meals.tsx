import { useCallback, useEffect, useState } from 'react';
import { api, type Me, type RecipeCard } from '../lib/api';
import { useToast } from '../components/Toast';
import Layout from '../components/Layout';
import DishImage from '../components/DishImage';
import { IconSpark } from '../components/icons';

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
const SLOTS = ['breakfast', 'lunch', 'dinner'];
type Grid = Record<string, Record<string, RecipeCard | null>>;

function monday(): string {
  const d = new Date();
  const day = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - day);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`; // local date: toISOString() can shift a day behind UTC
}

export default function Meals({ me }: { me: Me | null }) {
  const [week, setWeek] = useState(monday());
  const [grid, setGrid] = useState<Grid>({});
  const [pick, setPick] = useState<{ day: string; slot: string } | null>(null);
  const [pq, setPq] = useState('');
  const [options, setOptions] = useState<RecipeCard[]>([]);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const p = await api<{ grid: Grid }>(`/api/meal-plans?week_start=${week}`);
      setGrid(p.grid);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Failed to load plan', false);
    }
  }, [week, toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function clearSlot(day: string, slot: string) {
    const p = await api<{ grid: Grid }>(`/api/meal-plans/slot?week_start=${week}`, {
      method: 'PUT',
      body: JSON.stringify({ day, slot, recipe_id: null }),
    }).catch((e) => {
      toast(e instanceof Error ? e.message : 'Failed', false);
      return null;
    });
    if (p) setGrid(p.grid);
  }

  async function generate() {
    if (busy) return;
    setBusy(true);
    try {
      const p = await api<{ grid: Grid }>(`/api/meal-plans/generate?week_start=${week}`, { method: 'POST' });
      setGrid(p.grid);
      toast('Week generated from your taste.');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Generation failed', false);
    } finally {
      setBusy(false);
    }
  }

  async function searchPick() {
    const r = await api<{ results: RecipeCard[] }>(`/api/recipes/search?q=${encodeURIComponent(pq.trim() || 'dinner')}&limit=12`).catch(() => null);
    if (r) setOptions(r.results);
  }

  async function choose(rid: number) {
    if (!pick) return;
    const p = await api<{ grid: Grid }>(`/api/meal-plans/slot?week_start=${week}`, {
      method: 'PUT',
      body: JSON.stringify({ day: pick.day, slot: pick.slot, recipe_id: rid }),
    }).catch((e) => {
      toast(e instanceof Error ? e.message : 'Failed', false);
      return null;
    });
    if (p) {
      setGrid(p.grid);
      setPick(null);
    }
  }

  function shiftWeek(delta: number) {
    const d = new Date(week + 'T12:00:00');
    d.setDate(d.getDate() + delta * 7);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    setWeek(`${y}-${m}-${dd}`);
  }

  return (
    <Layout name={me?.name}>
      <h1>Meal Planner</h1>
      <div className="card plan-bar">
        <div className="row">
          <button className="icon" aria-label="Previous week" onClick={() => shiftWeek(-1)}>‹</button>
          <input type="date" value={week} onChange={(e) => setWeek(e.target.value)} style={{ maxWidth: 170 }} aria-label="Week start" />
          <button className="icon" aria-label="Next week" onClick={() => shiftWeek(1)}>›</button>
          <button className="ghost" onClick={generate} disabled={busy}>{busy ? 'Generating…' : <><IconSpark size={16} /> Generate my week</>}</button>
        </div>
        <p className="small muted" style={{ margin: '0.4rem 0 0' }}>Week starts Monday · filled from your taste — saved recipes first, no repeats.</p>
      </div>
      <div className="week">
        {DAYS.map((d) => (
          <div key={d} className="daycol plan-day">
            <div className="plan-dayhead">{d.slice(0, 3)}</div>
            {SLOTS.map((s) => {
              const r = grid[d]?.[s];
              return (
                <div key={s} className="mealslot">
                  <div className="small muted plan-slot">{s}</div>
                  {r ? (
                    <div className="plan-meal">
                      <a href={`/recipe?id=${r.recipe_id}`}>{r.name}</a>
                      <button className="mini-x" aria-label={`Remove ${r.name}`} onClick={() => clearSlot(d, s)}>✕</button>
                    </div>
                  ) : (
                    <button className="plan-add" onClick={() => { setPick({ day: d, slot: s }); setOptions([]); }}>+ add</button>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {pick && (
        <div className="card pick-sheet">
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <h2 style={{ margin: 0, textTransform: 'capitalize' }}>{pick.day} · {pick.slot}</h2>
            <button className="ghost" onClick={() => setPick(null)}>Close</button>
          </div>
          <div className="row" style={{ marginTop: '.5rem' }}>
            <input value={pq} onChange={(e) => setPq(e.target.value)} placeholder="Search recipes..."
              onKeyDown={(e) => { if (e.key === 'Enter') searchPick(); }} style={{ flex: 1 }} />
            <button onClick={searchPick}>Search</button>
          </div>
          <div style={{ marginTop: '.6rem' }}>
            {options.map((c) => (
              <div key={c.recipe_id} className="pick-row">
                <DishImage name={c.name} url={c.image_url} />
                <div style={{ flex: 1 }}>
                  <div className="title">{c.name}</div>
                  <div className="small muted">{c.minutes != null ? `${c.minutes} min` : ''}{c.rating != null ? ` · ${c.rating.toFixed(1)} stars` : ''}</div>
                </div>
                <button onClick={() => choose(c.recipe_id)}>Add</button>
              </div>
            ))}
            {!options.length && <p className="muted small">Search above to pick a dish for this slot.</p>}
          </div>
        </div>
      )}
    </Layout>
  );
}
