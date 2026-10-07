import { useCallback, useEffect, useState } from 'react';
import { api, type Me } from '../lib/api';
import { useToast } from '../components/Toast';
import { IconCheck, IconPlus, IconX } from '../components/icons';
import Layout from '../components/Layout';

interface PantryItem {
  id: number;
  label: string;
  normalized_name: string;
  quantity: string;
  unit: string;
  category: string;
  available: number;
}

export default function Pantry({ me }: { me: Me | null }) {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const l = await api<{ items: PantryItem[] }>('/api/pantry');
      setItems(l.items);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Failed to load pantry', false);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function add() {
    const v = input.trim();
    if (!v || busy) return;
    setBusy(true);
    try {
      const r = await api<{ items: PantryItem[] }>('/api/pantry/items', {
        method: 'POST',
        body: JSON.stringify({ label: v }),
      });
      const corr = r.items.filter((i) => (i as PantryItem & { corrected_from?: string }).corrected_from);
      toast(corr.length ? `Added ${r.items.length} item(s) — understood “${(corr[0] as PantryItem & { corrected_from?: string }).corrected_from}” as ${corr[0].normalized_name}.`
        : `Added ${r.items.length} item(s).`);
      setInput('');
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Add failed', false);
    } finally {
      setBusy(false);
    }
  }

  async function toggle(id: number) {
    await api(`/api/pantry/items/${id}/availability`, { method: 'PATCH' }).catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
    load();
  }

  async function del(id: number) {
    await api(`/api/pantry/items/${id}`, { method: 'DELETE' }).catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
    load();
  }

  const cats: Record<string, PantryItem[]> = {};
  items.forEach((i) => {
    (cats[i.category || 'other'] = cats[i.category || 'other'] || []).push(i);
  });

  return (
    <Layout name={me?.name}>
      <h1>My Pantry</h1>
      <p className="muted">Stock your kitchen once — <a href="/cook">What can I cook?</a> does the rest.</p>
      <div className="card pantry-add">
        <label className="f">Add to pantry</label>
        <div className="row">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Try: paneer, tomato, 2 onions"
            style={{ flex: 1 }} onKeyDown={(e) => { if (e.key === 'Enter') add(); }} />
          <button onClick={add} disabled={busy}><IconPlus size={16} /> {busy ? 'Adding…' : 'Add'}</button>
        </div>
        <p className="small muted">Tip: paste several comma-separated items at once. Typos like “panner” are auto-corrected.</p>
      </div>
      {loading ? <div className="card"><p className="muted">Loading your pantry…</p></div> : (
        items.length ? Object.entries(cats).map(([c, list]) => (
          <div key={c} className="card pantry-cat">
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <h2 style={{ margin: 0, textTransform: 'capitalize' }}>{c}</h2>
              <span className="score-pill">{list.filter((i) => i.available).length}/{list.length} in stock</span>
            </div>
            {list.map((i) => (
              <div key={i.id} className={'pantry-row' + (i.available ? '' : ' off')}>
                <button className={'stock-toggle' + (i.available ? ' on' : '')} onClick={() => toggle(i.id)}
                  aria-label={`Mark ${i.label} as ${i.available ? 'unavailable' : 'available'}`}
                  title={i.available ? 'In stock — click to mark used up' : 'Marked used up — click to restock'}>
                  {i.available ? <IconCheck size={16} /> : <IconPlus size={16} />}
                </button>
                <div style={{ flex: 1 }}>
                  <div className="pantry-name">{i.label}
                    {i.quantity && <span className="tagchip">{i.quantity}{i.unit ? ' ' + i.unit : ''}</span>}
                  </div>
                  <div className="small muted">matched as “{i.normalized_name}”</div>
                </div>
                <button className="icon" aria-label={`Remove ${i.label}`} onClick={() => del(i.id)}><IconX size={16} /></button>
              </div>
            ))}
          </div>
        )) : (
          <div className="card empty-hero">
            <h2>Your pantry is empty</h2>
            <p className="muted">Add a few staples above — then <a href="/cook">see what you can cook</a>.</p>
          </div>
        )
      )}
    </Layout>
  );
}
