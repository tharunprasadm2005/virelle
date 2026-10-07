import { useEffect, useState } from 'react';
import { api, type Me } from '../lib/api';
import Layout from '../components/Layout';

interface AblationRow {
  model: string;
  K: number;
  'P@10': number;
  'R@10': number;
  'NDCG@10': number;
  'HR@10': number;
}

interface DemoUser {
  user_id: number;
  n_interactions: number;
  n_reviews: number;
  shift: number;
}

export default function Research({ me }: { me: Me | null }) {
  const [ablation, setAblation] = useState<AblationRow[]>([]);
  const [dataset, setDataset] = useState<{ present: boolean; recipe_file?: string; interaction_file?: string; recipe_mb?: number; interaction_mb?: number; message?: string } | null>(null);
  const [demo, setDemo] = useState<DemoUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api<{ ablation: AblationRow[]; dataset: NonNullable<typeof dataset> }>('/api/research/summary'),
      api<{ users: DemoUser[] }>('/api/demo_users'),
    ])
      .then(([s, d]) => {
        setAblation(s.ablation.filter((r) => r.K === 10));
        setDataset(s.dataset);
        setDemo(d.users);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load research data'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Layout name={me?.name}>
        <h1>Research &amp; Evaluation</h1>
        <p className="muted">Loading evaluation data…</p>
      </Layout>
    );
  }
  if (error) {
    return (
      <Layout name={me?.name}>
        <h1>Research &amp; Evaluation</h1>
        <div className="card"><p>{error} <a href="#" onClick={(e) => { e.preventDefault(); window.location.reload(); }}>Retry</a></p></div>
      </Layout>
    );
  }

  return (
    <Layout name={me?.name}>
      <h1>Research &amp; Evaluation</h1>
      <p className="muted">Academic view of the adaptive recommendation engine (faculty/developer area).</p>
      <div className="card">
        <h2>How Virelle recommends</h2>
        <p className="small muted">The same engine that powers your home feed, in plain terms. Nothing here is marketing — every claim below maps to code in <code>src/recommender/</code>.</p>
        <ol className="steps engine-steps">
          <li><strong>Content match (TF-IDF).</strong> Every recipe becomes a 20,000-feature word vector from its name, description, ingredients, and tags; cosine similarity finds look-alikes of dishes you rated highly.</li>
          <li><strong>Collaborative filtering (matrix factorization).</strong> A 50-factor SVD model learns latent taste dimensions from 855K real ratings. The original prototype used scikit-surprise SVD; the shipped system uses an equivalent TruncatedSVD for portability.</li>
          <li><strong>Hybrid baseline.</strong> 70% collaborative + 30% content-based, with a popularity fallback for brand-new users — the reference system everything else is measured against.</li>
          <li><strong>Preference evolution.</strong> Your history is split into older vs recent; recent interactions decay-weight higher (exponential decay, λ=0.02, or window weights). The cosine distance between the two eras is the preference-shift score; your adaptive profile blends 30% history with 70% recent taste.</li>
          <li><strong>Review-aspect learning.</strong> A 17-aspect lexicon (taste, healthy, spicy, easy, quick…) with negation-aware sentiment turns review text into signed preference signals, aggregated per user and per recipe, matched by cosine compatibility.</li>
          <li><strong>Semantic sidecar.</strong> A MiniLM language model embeds every recipe into 384 dimensions indexed with FAISS; fused with keyword search for natural queries. TF-IDF is kept, never replaced.</li>
        </ol>
        <p className="small muted">Measured, not claimed: on a temporal split (train older, test recent liked), review-aspect signals doubled hit-rate over baseline (HR@10 0.002 vs 0.001); temporal re-weighting alone was ranking-neutral. Full protocol in <code>docs/EXPERIMENTS.md</code>.</p>
      </div>
      <div className="card">
        <h2>Dataset</h2>
        {dataset && (dataset.present ? (
          <p><strong>{dataset.recipe_file}</strong> ({dataset.recipe_mb} MB) + <strong>{dataset.interaction_file}</strong> ({dataset.interaction_mb} MB)</p>
        ) : <p>{dataset.message || 'missing'}</p>)}
      </div>
      <div className="card">
        <h2>Ablation study (real Food.com data)</h2>
        {ablation.length ? (
          <>
            <table className="metrics">
              <thead><tr><th>Model</th><th>P@10</th><th>R@10</th><th>NDCG@10</th><th>HR@10</th></tr></thead>
              <tbody>
                {ablation.map((r) => (
                  <tr key={r.model}><td>{r.model}</td><td>{r['P@10'].toFixed(4)}</td><td>{r['R@10'].toFixed(4)}</td>
                    <td>{r['NDCG@10'].toFixed(4)}</td><td>{r['HR@10'].toFixed(4)}</td></tr>
                ))}
              </tbody>
            </table>
            <p className="small muted">Review-aspect signals doubled hit-rate vs baseline; temporal re-weighting alone was neutral — reported as measured.</p>
          </>
        ) : <p className="muted">No ablation results yet. Run <code>scripts/evaluate.py</code>.</p>}
        <p className="small muted">Protocol: per-user temporal split — train on older interactions, test on recent liked ones.</p>
      </div>
      <div className="card">
        <h2>Demo users with measurable preference shift</h2>
        <table className="metrics">
          <thead><tr><th>User</th><th>Interactions</th><th>Reviews</th><th>Shift</th></tr></thead>
          <tbody>
            {demo.map((u) => (
              <tr key={u.user_id}><td>{u.user_id}</td><td>{u.n_interactions}</td><td>{u.n_reviews}</td><td>{u.shift}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
