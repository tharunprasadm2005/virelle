import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, greeting, type HomeResponse, type Me, type RecipeCard } from '../lib/api';
import Layout from '../components/Layout';
import RecipeCardView from '../components/RecipeCard';
import { IconLeaf } from '../components/icons';

export default function Home({ me }: { me: Me | null }) {
  const [data, setData] = useState<HomeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [intent, setIntent] = useState('');
  const navigate = useNavigate();

  const load = useCallback(
    async (it?: string) => {
      setLoading(true);
      setError('');
      try {
        const h = await api<HomeResponse>('/api/home' + (it ? `?intent=${encodeURIComponent(it)}` : ''));
        setData(h);
        const ids = h.recommended.map((c) => c.recipe_id);
        if (ids.length) api('/api/events/shown-batch', { method: 'POST', body: JSON.stringify({ recipe_ids: ids, context: 'home' }) }).catch(() => {});
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    load();
  }, [load]);

  function goSearch() {
    navigate('/discover?q=' + encodeURIComponent(query));
  }

  function dropDisliked(id: number) {
    setData((d) => (d ? { ...d, recommended: d.recommended.filter((c) => c.recipe_id !== id) } : d));
  }

  return (
    <Layout name={me?.name}>
      <div className="hero">
        <h1>{greeting()}, {me?.name}</h1>
        <div className="searchbar">
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search recipes... (try 'quick chicken dinner')"
            onKeyDown={(e) => { if (e.key === 'Enter') goSearch(); }} />
          <button onClick={goSearch}>Search</button>
        </div>
        <div className="searchbar" style={{ marginTop: '.4rem' }}>
          <input value={intent} onChange={(e) => setIntent(e.target.value)} placeholder="Right now I'm craving... (temporary, won't change your taste profile)"
            onKeyDown={(e) => { if (e.key === 'Enter') load(intent.trim() || undefined); }} />
          <button className="ghost" onClick={() => load(intent.trim() || undefined)}>Apply</button>
        </div>
      </div>
      {loading && <p className="muted">Finding recipes for you — a few seconds on first load…</p>}
      {error && <p>Couldn't load recommendations: {error} <a href="#" onClick={(e) => { e.preventDefault(); load(); }}>Retry</a></p>}
      {data && (
        <>
          <div id="stage">
            {data.stage.stage === 'personalized' ? null : (
              <div className="banner-warn"><IconLeaf size={16} /> {data.stage.message}</div>
            )}
          </div>
          <h2>Recommended for you</h2>
          <div className="grid">
            {data.recommended.map((c: RecipeCard) => (
              <RecipeCardView key={c.recipe_id} card={c} showCook onDislike={dropDisliked} />
            ))}
          </div>
          {data.shelves.map((s) => (
            <div key={s.label}>
              <h2>{s.label}</h2>
              <div className="grid">
                {s.recipes.map((c: RecipeCard) => (
                  <RecipeCardView key={c.recipe_id} card={c} onDislike={dropDisliked} />
                ))}
              </div>
            </div>
          ))}
          <h2>Recently saved</h2>
          <div className="grid">
            {data.saved.length ? (
              data.saved.map((c: RecipeCard) => <RecipeCardView key={c.recipe_id} card={c} />)
            ) : (
              <p className="muted">Nothing saved yet — tap Save on any recipe.</p>
            )}
          </div>
        </>
      )}
    </Layout>
  );
}
