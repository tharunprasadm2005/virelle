import { useCallback, useEffect, useState } from 'react';
import { api, type Me } from '../lib/api';
import { useToast } from '../components/Toast';
import Layout from '../components/Layout';
import { IconCheck, IconPlus, IconX } from '../components/icons';

interface Item {
  id: number;
  label: string;
  category: string;
  quantity: string;
  checked: number;
}

export default function Shopping({ me }: { me: Me | null }) {
  const [items, setItems] = useState<Item[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const l = await api<{ items: Item[] }>('/api/shopping-list');
      setItems(l.items);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Failed to load', false);
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
      const parts = v.split('—').length > 1 ? v.split('—') : v.split(' - ').length > 1 ? v.split(' - ') : [v, ''];
      await api('/api/shopping-list/items', {
        method: 'POST',
        body: JSON.stringify({ label: parts[0].trim(), quantity: (parts[1] || '').trim() }),
      });
      setInput('');
      await load();
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Add failed', false);
    } finally {
      setBusy(false);
    }
  }

  async function toggle(id: number) {
    await api(`/api/shopping-list/items/${id}`, { method: 'PATCH' }).catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
    load();
  }

  async function del(id: number) {
    await api(`/api/shopping-list/items/${id}`, { method: 'DELETE' }).catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
    load();
  }

  async function clearDone() {
    await api('/api/shopping-list/clear-completed', { method: 'POST' }).catch((e) => toast(e instanceof Error ? e.message : 'Failed', false));
    load();
  }

  async function merge() {
    const r = await api<{ merged: number }>('/api/shopping-list/merge-duplicates', { method: 'POST' }).catch((e) => {
      toast(e instanceof Error ? e.message : 'Failed', false);
      return null;
    });
    if (r) toast(`Merged ${r.merged} duplicate entries.`);
    load();
  }

  const cats: Record<string, Item[]> = {};
  items.forEach((i) => {
    (cats[i.category || 'other'] = cats[i.category || 'other'] || []).push(i);
  });
  const done = items.filter((i) => i.checked).length;

  return (
    <Layout name={me?.name}>
      <h1>Shopping List</h1>
      <div className="card shop-add">
        <div className="row">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Add item... (e.g. Paneer — 500 g, or several comma-separated)"
            style={{ flex: 1 }} onKeyDown={(e) => { if (e.key === 'Enter') add(); }} />
          <button onClick={add} disabled={busy}><IconPlus size={16} /> {busy ? 'Adding…' : 'Add'}</button>
        </div>
        <div className="row" style={{ marginTop: '.5rem' }}>
          <button className="ghost" onClick={merge}>Merge duplicates</button>
          <button className="ghost" onClick={clearDone}>Clear completed</button>
        </div>
      </div>
      {loading ? <div className="card"><p className="muted">Loading your list…</p></div> : (
        items.length ? (
          <>
            <div className="card shop-progress">
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <strong>{done} of {items.length} bought</strong>
                <span className="small muted">{items.length ? Math.round((done / items.length) * 100) : 0}%</span>
              </div>
              <div className="cov-bar" style={{ marginTop: '.4rem' }}>
                <div style={{ width: `${items.length ? Math.round((done / items.length) * 100) : 0}%` }} />
              </div>
            </div>
            {Object.entries(cats).map(([c, list]) => (
              <div key={c} className="card shop-cat-card">
                <h2 style={{ margin: 0, textTransform: 'capitalize' }}>{c} <span className="muted small">· {list.length}</span></h2>
                {list.map((i) => (
                  <div key={i.id} className={'shop-row' + (i.checked ? ' done' : '')}>
                    <button className={'stock-toggle' + (i.checked ? ' on' : '')}
                      aria-label={`Mark ${i.label} as ${i.checked ? 'not bought' : 'bought'}`}
                      onClick={() => toggle(i.id)}>
                      {i.checked ? <IconCheck size={16} /> : null}
                    </button>
                    <div style={{ flex: 1 }}>
                      <span className="shop-label">{i.label}</span>
                      {i.quantity && <span className="tagchip">{i.quantity}</span>}
                    </div>
                    <button className="icon" aria-label={`Remove ${i.label}`} onClick={() => del(i.id)}><IconX size={16} /></button>
                  </div>
                ))}
              </div>
            ))}
          </>
        ) : (
          <div className="card empty-hero">
            <h2>Nothing to buy yet</h2>
            <p className="muted">Add items above, tap the shopping-list button on any recipe, or send missing ingredients from <a href="/cook">What can I cook?</a>.</p>
          </div>
        )
      )}
    </Layout>
  );
}
