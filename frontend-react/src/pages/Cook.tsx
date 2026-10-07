import { useCallback, useEffect, useState } from 'react';
import { api, type Me, type RecipeCard } from '../lib/api';
import { useToast } from '../components/Toast';
import Layout from '../components/Layout';
import DishImage from '../components/DishImage';
import { IconHeart, IconReceipt, IconSearch } from '../components/icons';

export default function Cook({ me }: { me: Me | null }) {
  const [diet, setDiet] = useState('');
  const [matches, setMatches] = useState<RecipeCard[]>([]);
  const [message, setMessage] = useState('');
  const [understood, setUnderstood] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [missing, setMissing] = useState<Record<number, string[]>>({});
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api<{ pantry_empty: boolean; matches: RecipeCard[]; message?: string; understood_as?: string[] }>(
        '/api/cook/matches?min_coverage=0.3&limit=24' + (diet ? `&diet=${diet}` : '')
      );
      if (r.pantry_empty) {
        setMessage(r.message || '');
        setMatches([]);
      } else if (!r.matches.length) {
        setMessage(r.message || 'No matches — add more pantry staples.');
        setUnderstood(r.understood_as || []);
        setMatches([]);
      } else {
        setMessage('');
        setMatches(r.matches);
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Search failed');
      setMatches([]);
    } finally {
      setLoading(false);
    }
  }, [diet]);

  useEffect(() => {
    load();
  }, [load]);

  async function showMissing(rid: number) {
    const m = await api<{ missing: string[] }>(`/api/cook/missing/${rid}`).catch((e) => {
      toast(e instanceof Error ? e.message : 'Failed', false);
      return null;
    });
    if (m) setMissing((prev) => ({ ...prev, [rid]: m.missing }));
  }

  async function toShop(rid: number) {
    const r = await api<{ added: number }>(`/api/cook/missing-to-shopping/${rid}`, { method: 'POST' }).catch((e) => {
      toast(e instanceof Error ? e.message : 'Failed', false);
      return null;
    });
    if (r) toast(`Added ${r.added} items to your shopping list.`);
  }

  async function saveIt(rid: number) {
    await api(`/api/interactions/${rid}`, { method: 'POST', body: JSON.stringify({ interaction_type: 'SAVE' }) })
      .then(() => toast('Saved to favorites.'))
      .catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
  }

  function metaLine(c: RecipeCard) {
    const parts: string[] = [];
    if (c.rating != null) parts.push(`${c.rating.toFixed(1)}${c.review_count ? ` (${c.review_count})` : ''}`);
    if (c.minutes != null) parts.push(`${c.minutes} min`);
    return <div className="meta-row small muted">{parts.join(' · ')}</div>;
  }

  return (
    <Layout name={me?.name}>
      <h1>What can I cook?</h1>
      <div className="card cook-hero">
        <p className="muted" style={{ marginTop: 0 }}>Ranked by your pantry, your taste, and recipe quality.</p>
        <div className="row">
          <select value={diet} onChange={(e) => setDiet(e.target.value)} style={{ maxWidth: 190 }}>
            <option value="">Any diet</option><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option>
          </select>
          <button onClick={load}><IconSearch size={16} /> Find recipes</button>
          <a className="btn ghost" href="/pantry">Manage pantry</a>
        </div>
      </div>
      {loading ? <div className="card"><p className="muted">Searching 500K recipes against your pantry — a few seconds…</p></div> :
        matches.length ? (
          <div className="grid" style={{ marginTop: '.8rem' }}>
            {matches.map((c) => (
              <div key={c.recipe_id} className="rcard cook-card">
                <DishImage name={c.name} url={c.image_url} />
                <div className="body">
                  <div className="cov-row">
                    <div className="cov-ring" style={{ ['--p' as string]: `${Math.round((c.coverage || 0) * 100)}%` }}>
                      <span>{Math.round((c.coverage || 0) * 100)}%</span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <a className="title" href={`/recipe?id=${c.recipe_id}`} style={{ color: 'inherit', textDecoration: 'none' }}>{c.name}</a>
                      {metaLine(c)}
                    </div>
                  </div>
                  <div className="actions">
                    <button className="icon" aria-label="Show missing ingredients" onClick={() => showMissing(c.recipe_id)}><IconReceipt size={16} /> Missing?</button>
                    <button className="icon" aria-label="Save recipe" onClick={() => saveIt(c.recipe_id)}><IconHeart size={16} /></button>
                  </div>
                  {missing[c.recipe_id] && (
                    <div className="small muted">
                      {missing[c.recipe_id].length ? <>Missing: {missing[c.recipe_id].join(', ')} <a href="#" onClick={(e) => { e.preventDefault(); toShop(c.recipe_id); }}>add all to shopping list</a></> : 'You have everything to cook this.'}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card empty-hero">
            <h2>{message || 'No matches yet'}</h2>
            {understood.length > 0 && <p className="small muted">We looked for: {understood.join(', ')}</p>}
            <p><a className="btn" href="/pantry">Stock your pantry →</a></p>
          </div>
        )}
    </Layout>
  );
}
