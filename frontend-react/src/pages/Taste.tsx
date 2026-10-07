import { useEffect, useState } from 'react';
import { api, type Me } from '../lib/api';
import Layout from '../components/Layout';
import { IconCheck, IconLeaf, IconSpark, IconX } from '../components/icons';

interface TasteData {
  has_history: boolean;
  message?: string;
  shift?: number;
  n_old?: number;
  n_recent?: number;
  evolution_ready?: boolean;
  evolution_note?: string | null;
  cuisines?: { label: string; count: number }[];
  aspects?: Record<string, number>;
  onboarding?: Record<string, unknown>;
}

export default function Taste({ me }: { me: Me | null }) {
  const [t, setT] = useState<TasteData | null>(null);
  const [evo, setEvo] = useState<{ earlier_recipes: { name: string }[]; recent_recipes: { name: string }[] } | null>(null);

  useEffect(() => {
    api<TasteData>('/api/taste')
      .then((d) => {
        setT(d);
        if (d.has_history && d.evolution_ready) {
          api<{ has_history: boolean; earlier_recipes: { name: string }[]; recent_recipes: { name: string }[] }>('/api/taste/evolution')
            .then((e) => { if (e.has_history) setEvo(e); })
            .catch(() => {});
        }
      })
      .catch(() => setT({ has_history: false, message: 'Could not load taste profile.' }));
  }, []);

  if (!t) return <Layout name={me?.name}><p className="muted">Loading…</p></Layout>;
  if (!t.has_history) {
    return (
      <Layout name={me?.name}>
        <h1>My Taste</h1>
        <div className="card"><p>{t.message}</p><p><a href="/discover">Discover recipes</a> to get started.</p></div>
      </Layout>
    );
  }
  const entries = Object.entries(t.aspects || {});
  const likes = entries.filter(([, v]) => v > 0.25);
  const dislikes = entries.filter(([, v]) => v < -0.25);
  const maxC = Math.max(1, ...(t.cuisines || []).map((c) => c.count));

  return (
    <Layout name={me?.name}>
      <h1>My Taste</h1>
      <div className="card">
        <h2>What you usually enjoy</h2>
        {(t.cuisines || []).slice(0, 8).map((c) => (
          <div key={c.label} className="bar">
            <span style={{ width: 130 }}>{c.label}</span>
            <div className="fill" style={{ width: `${(c.count / maxC) * 220}px` }} />
            <span className="muted small">{c.count}</span>
          </div>
        ))}
        {!(t.cuisines || []).length && <p className="muted">Like a few recipes and your pattern will appear here.</p>}
      </div>
      <div className="card">
        <h2>From your reviews</h2>
        {entries.length ? (
          <>
            <p className="small muted">Learned from the words in your reviews — not from ratings alone.</p>
            <div className="pill-group" style={{ marginBottom: '.4rem' }}>
              {likes.map(([a]) => <span key={a} className="tagchip chip-like"><IconCheck size={14} /> {a}</span>)}
              {!likes.length && <span className="muted small">No strong likes detected yet.</span>}
            </div>
            <div className="pill-group">
              {dislikes.map(([a]) => <span key={a} className="tagchip chip-dislike"><IconX size={14} /> {a}</span>)}
            </div>
          </>
        ) : <p className="muted">No review notes yet — write feedback on recipes you try.</p>}
      </div>
      <div className="card">
        <h2>How your taste is moving</h2>
        {(t.shift || 0) > 0.15
          ? <p><IconLeaf size={16} /> <strong>Evolving</strong> — your recent picks differ from your older ones.</p>
          : <p><IconSpark size={16} /> <strong>Steady</strong> — your recent picks match your history.</p>}
        <div className="shift-meter">
          <div className="shift-fill" style={{ width: `${Math.round((t.shift || 0) * 100)}%` }} />
        </div>
        <p>Preference shift: <strong>{((t.shift || 0) * 100).toFixed(1)}%</strong>
          <span className="muted small"> ({t.n_old} older vs {t.n_recent} recent)</span></p>
        {t.evolution_ready ? (
          evo ? (
            <div className="evo-timeline">
              <div className="evo-col">
                <div className="evo-head">Earlier</div>
                {evo.earlier_recipes.map((x, i) => <div key={i} className="evo-chip">{x.name}</div>)}
              </div>
              <div className="evo-arrow" aria-hidden="true">↓</div>
              <div className="evo-col">
                <div className="evo-head">Recent</div>
                {evo.recent_recipes.map((x, i) => <div key={i} className="evo-chip recent">{x.name}</div>)}
              </div>
            </div>
          ) : <p className="muted">Loading earlier vs recent…</p>
        ) : <p className="muted">{t.evolution_note}</p>}
      </div>
    </Layout>
  );
}
