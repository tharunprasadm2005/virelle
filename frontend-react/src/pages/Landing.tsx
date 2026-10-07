import { Link } from 'react-router-dom';
import { getToken } from '../lib/api';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const SECTIONS: [string, string, string][] = [
  ['/discover', 'Discover', 'Search 500K+ recipes by craving, diet, or time.'],
  ['/pantry', 'Pantry', "Tell us what's in your kitchen."],
  ['/cook', 'What can I cook?', 'Ranked by your ingredients + your taste.'],
  ['/meals', 'Meal Planner', 'Generate your week in one tap.'],
  ['/shopping', 'Shopping List', 'Missing ingredients, merged and grouped.'],
  ['/taste', 'My Taste', 'Watch your preferences evolve.'],
  ['/profile', 'Profile', 'Tastes, collections, imports, password.'],
  ['/research', 'Research', 'The science behind the recommendations.'],
];

export default function Landing() {
  const navigate = useNavigate();
  useEffect(() => {
    if (getToken()) navigate('/');
  }, [navigate]);
  return (
    <>
      <header className="topbar">
        <Link className="logo" to="/welcome">Virelle<small>Recipes that learn your taste</small></Link>
        <nav className="mainnav" />
        <div className="userbox"><Link to="/auth">Log in</Link><Link to="/auth">Sign up</Link></div>
      </header>
      <main style={{ maxWidth: 720 }}>
        <div className="card" style={{ textAlign: 'center', padding: '2rem 1.5rem' }}>
          <h1 style={{ color: 'var(--accent)' }}>Virelle</h1>
          <p><strong>Know what to cook.</strong></p>
          <p className="muted">Half a million real recipes. Recommendations that adapt as your taste changes — then a weekly plan and shopping list to match.</p>
          <p><Link className="btn" to="/auth">Open the app →</Link> <Link className="btn ghost" to="/auth">Try the demo account</Link></p>
        </div>
        <div className="grid">
          {SECTIONS.map(([h, t, d]) => (
            <Link key={h} className="card" to={h} style={{ textDecoration: 'none', color: 'inherit' }}>
              <h2>{t}</h2><p className="muted small">{d}</p>
            </Link>
          ))}
        </div>
      </main>
    </>
  );
}
