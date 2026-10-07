import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api, type Me } from '../lib/api';
import { useToast } from '../components/Toast';
import Layout from '../components/Layout';
import DishImage from '../components/DishImage';
import { IconClock, IconHeart, IconPot, IconServings, IconStar, IconThumbDown, IconThumbUp } from '../components/icons';

interface Detail {
  recipe_id: number;
  name: string;
  minutes: number | null;
  servings: number | null;
  rating: number | null;
  review_count: number;
  image_url: string | null;
  tags: string[];
  description_full: string;
  ingredients: string[];
  instructions: string[];
  diet_estimate?: { vegetarian: boolean; vegan: boolean; gluten_free: boolean; allergens_detected: string[] } | null;
}

interface Collection {
  id: number;
  name: string;
}

type InteractKind = 'SAVE' | 'LIKE' | 'DISLIKE' | 'COOKED';

export default function Recipe({ me }: { me: Me | null }) {
  const [params] = useSearchParams();
  const id = params.get('id') || '';
  const [r, setR] = useState<Detail | null>(null);
  const [why, setWhy] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [stars, setStars] = useState(0);
  const [notes, setNotes] = useState('');
  const [fbMsg, setFbMsg] = useState('');
  const [colls, setColls] = useState<Collection[]>([]);
  const [collSel, setCollSel] = useState('');
  const [step, setStep] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (!id) return;
    api<Detail>(`/api/recipes/${id}`)
      .then((d) => {
        setR(d);
        api<{ recommended: { recipe_id: number; why: string[] }[] }>('/api/home')
          .then((h) => {
            const hit = h.recommended.find((x) => x.recipe_id === Number(id));
            if (hit) setWhy(hit.why);
          })
          .catch(() => {});
        api<{ collections: Collection[] }>('/api/collections')
          .then((c) => setColls(c.collections))
          .catch(() => {});
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'));
  }, [id]);

  const react = useCallback(
    async (kind: InteractKind) => {
      if (busy) return;
      setBusy(true);
      try {
        await api(`/api/interactions/${id}`, { method: 'POST', body: JSON.stringify({ interaction_type: kind }) });
        toast(kind === 'SAVE' ? 'Saved to favorites' : kind === 'LIKE' ? 'Liked' : kind === 'DISLIKE' ? 'Noted — fewer like this' : 'Marked as cooked');
      } catch (e) {
        toast(e instanceof Error ? e.message : 'Failed', false);
      } finally {
        setBusy(false);
      }
    },
    [busy, id, toast]
  );

  async function rate(n: number) {
    setStars(n);
    // a low rating must never record a LIKE (it would inject a 5-star signal)
    if (n >= 4) await react('LIKE');
    else if (n <= 2) await react('DISLIKE');
    await api(`/api/interactions/${id}`, { method: 'POST', body: JSON.stringify({ interaction_type: 'RATED', rating: n }) }).catch(() => {});
    setFbMsg(`Rated ${n} stars — thanks, this improves your recommendations.`);
  }

  async function feedback() {
    if (!notes.trim()) {
      setFbMsg('Write a few words first.');
      return;
    }
    await api(`/api/interactions/${id}`, { method: 'POST', body: JSON.stringify({ interaction_type: 'REVIEW', review_text: notes.trim() }) }).catch(() => {});
    setFbMsg('Thanks! Your taste profile will learn from this.');
    setNotes('');
  }

  async function addShop() {
    const res = await api<{ added: number }>(`/api/shopping-list/from-recipe/${id}`, { method: 'POST' }).catch((e) => {
      toast(e instanceof Error ? e.message : 'Failed', false);
      return null;
    });
    if (res) toast(`Added ${res.added} ingredients to your shopping list.`);
  }

  async function toColl() {
    if (!collSel) {
      toast('Create a collection on your Profile page first.', false);
      return;
    }
    await api(`/api/collections/${collSel}/items`, {
      method: 'POST',
      body: JSON.stringify({ recipe_id: Number(id), source: 'foodcom' }),
    }).catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
    toast('Added to collection.');
  }

  if (error) return <Layout name={me?.name}><div className="card"><p>{error}</p></div></Layout>;
  if (!r) return <Layout name={me?.name}><p className="muted">Loading recipe…</p></Layout>;

  return (
    <Layout name={me?.name}>
      <div className="card">
        <div className="detail-hero">
          <div className="detail-media"><DishImage name={r.name} url={r.image_url} /></div>
          <div style={{ flex: 1, minWidth: 240 }}>
            <h1>{r.name}</h1>
            <div className="meta-row">
              {r.rating != null && <span><IconStar size={14} /> {r.rating.toFixed(1)}{r.review_count ? ` (${r.review_count})` : ''}</span>}
              {r.minutes != null && <span><IconClock size={14} /> {r.minutes} min</span>}
              {r.servings != null && <span><IconServings size={14} /> {Math.round(r.servings)} servings</span>}
            </div>
            <div>{(r.tags || []).map((t) => <span key={t} className="tagchip">{t}</span>)}</div>
            {r.diet_estimate && (
              <div className="small muted" style={{ marginTop: '.4rem' }}>
                Estimated: {r.diet_estimate.vegetarian ? '✓ vegetarian ' : ''}{r.diet_estimate.vegan ? '✓ vegan ' : ''}
                {r.diet_estimate.gluten_free ? '✓ gluten-free ' : ''}
                {r.diet_estimate.allergens_detected.length ? `· contains: ${r.diet_estimate.allergens_detected.join(', ')}` : ''} (estimated)
              </div>
            )}
            {why.length > 0 && (
              <div className="banner-ok" style={{ marginTop: '.6rem' }}>
                <strong>Why recommended?</strong>
                <ul>{why.map((e, i) => <li key={i}>{e}</li>)}</ul>
              </div>
            )}
            <div className="row" style={{ marginTop: '.6rem' }}>
              <button className="icon" aria-label="Save recipe" onClick={() => react('SAVE')} disabled={busy}><IconHeart /> Save</button>
              <button className="icon" aria-label="Like recipe" onClick={() => react('LIKE')} disabled={busy}><IconThumbUp /> Like</button>
              <button className="icon" aria-label="Dislike recipe" onClick={() => react('DISLIKE')} disabled={busy}><IconThumbDown /> Not for me</button>
              <button className="icon" aria-label="Mark as cooked" onClick={() => react('COOKED')} disabled={busy}><IconPot /> I cooked this</button>
              <button className="ghost" onClick={addShop}>Shopping list</button>
            </div>
            <div className="row" style={{ marginTop: '.4rem' }}>
              <select value={collSel} onChange={(e) => setCollSel(e.target.value)} style={{ maxWidth: 220 }}>
                <option value="">Pick a collection…</option>
                {colls.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <button className="ghost" onClick={toColl}>Add to collection</button>
            </div>
          </div>
        </div>
      </div>
      <div className="card">
        <h2>Ingredients</h2>
        <ul className="ings">{r.ingredients.length ? r.ingredients.map((i, n) => <li key={n}>{i}</li>) : <li className="muted">No ingredient list in dataset.</li>}</ul>
      </div>
      <div className="card">
        <h2>Instructions</h2>
        {r.instructions.length ? (
          <>
            <ol className="steps">{r.instructions.map((s, n) => <li key={n}>{s}</li>)}</ol>
            <p><button onClick={() => setStep(0)}>Start cooking</button></p>
            {step !== null && (
              <div className="card">
                <h3><span className="step-dot now">{step + 1}</span> Step {step + 1} of {r.instructions.length}</h3>
                <p>{r.instructions[step]}</p>
                <div className="row">
                  <button className="ghost" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0}>← Previous</button>
                  {step < r.instructions.length - 1
                    ? <button onClick={() => setStep(Math.min(r.instructions.length - 1, step + 1))}>Next →</button>
                    : <button onClick={() => { react('COOKED'); setStep(null); }}>✔ Finished cooking</button>}
                </div>
              </div>
            )}
          </>
        ) : <p className="muted">No instructions in dataset.</p>}
        {r.description_full && <p className="muted">{r.description_full.slice(0, 600)}</p>}
      </div>
      <div className="card">
        <h2>Your feedback</h2>
        <label className="f">How was it? (1–5)</label>
        <div className="row">{[1, 2, 3, 4, 5].map((n) => <button key={n} className="icon" aria-label={`Rate ${n} stars`} onClick={() => rate(n)}><IconStar /></button>)}</div>
        {stars > 0 && <p className="small muted">You rated {stars} stars</p>}
        <label className="f">Taste notes (optional)</label>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="e.g. loved the mild flavor, quick to make" />
        <p><button onClick={feedback}>Submit feedback</button></p>
        <p className="small muted">{fbMsg}</p>
      </div>
    </Layout>
  );
}
