import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, type Me, type RecipeCard } from '../lib/api';
import { useToast } from '../components/Toast';
import Layout from '../components/Layout';
import RecipeCardView from '../components/RecipeCard';

interface Section {
  label: string;
  recipes: RecipeCard[];
}

export default function Discover({ me }: { me: Me | null }) {
  const [params] = useSearchParams();
  const [q, setQ] = useState(params.get('q') || '');
  const [time, setTime] = useState('');
  const [diet, setDiet] = useState('');
  const [results, setResults] = useState<RecipeCard[] | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState(false);
  const [importUrl, setImportUrl] = useState('');
  const [importMsg, setImportMsg] = useState('');
  const [importing, setImporting] = useState(false);
  const toast = useToast();

  const search = useCallback(async () => {
    const query = q.trim();
    if (!query) return;
    setLoading(true);
    try {
      let url = `/api/recipes/search?q=${encodeURIComponent(query)}`;
      if (time) url += `&max_minutes=${time}`;
      if (diet) url += `&diet=${diet}`;
      const r = await api<{ results: RecipeCard[] }>(url);
      setResults(r.results);
      setSections([]);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Search failed', false);
    } finally {
      setLoading(false);
    }
  }, [q, time, diet, toast]);

  useEffect(() => {
    const initial = params.get('q');
    if (initial) {
      setQ(initial);
      api<{ results: RecipeCard[] }>(`/api/recipes/search?q=${encodeURIComponent(initial)}`)
        .then((r) => setResults(r.results))
        .catch(() => {});
    } else {
      api<{ sections: Section[] }>('/api/discover')
        .then((d) => setSections(d.sections.filter(Boolean)))
        .catch(() => {});
    }
  }, [params]);

  async function doImport() {
    const u = importUrl.trim();
    if (!u || importing) return;
    setImporting(true);
    setImportMsg('Importing…');
    try {
      const r = await api<{ title: string; source_name: string }>('/api/imports', {
        method: 'POST',
        body: JSON.stringify({ url: u }),
      });
      setImportMsg(`Imported "${r.title}" from ${r.source_name}. Find it under Profile → My imports.`);
      setImportUrl('');
    } catch (e) {
      setImportMsg(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setImporting(false);
    }
  }

  return (
    <Layout name={me?.name}>
      <h1>Discover</h1>
      <div className="searchbar">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="quick chicken dinner, healthy paneer, dessert..."
          onKeyDown={(e) => { if (e.key === 'Enter') search(); }} />
        <button onClick={search} disabled={loading}>{loading ? 'Searching…' : 'Search'}</button>
      </div>
      <div className="row" style={{ marginTop: '.6rem' }}>
        <select value={time} onChange={(e) => setTime(e.target.value)} style={{ maxWidth: 190 }}>
          <option value="">Any time</option><option value="15">Under 15 min</option>
          <option value="30">Under 30 min</option><option value="60">Under 60 min</option>
        </select>
        <select value={diet} onChange={(e) => setDiet(e.target.value)} style={{ maxWidth: 190 }}>
          <option value="">Any diet</option><option value="vegetarian">Vegetarian</option><option value="vegan">Vegan</option>
        </select>
      </div>
      {results && (
        <>
          <h2>Results ({results.length})</h2>
          <div className="grid">
            {results.length ? results.map((c) => <RecipeCardView key={c.recipe_id} card={c} />)
              : <p className="muted">No matches — try fewer words.</p>}
          </div>
        </>
      )}
      <div className="card">
        <h2>Import a recipe from a URL</h2>
        <div className="row">
          <input value={importUrl} onChange={(e) => setImportUrl(e.target.value)} placeholder="https://..." style={{ flex: 1 }} />
          <button onClick={doImport} disabled={importing}>{importing ? 'Importing…' : 'Import'}</button>
        </div>
        <p className="small muted">{importMsg}</p>
      </div>
      {sections.map((s) => (
        <div key={s.label}>
          <h2>{s.label}</h2>
          <div className="grid">{s.recipes.map((c) => <RecipeCardView key={c.recipe_id} card={c} />)}</div>
        </div>
      ))}
    </Layout>
  );
}
