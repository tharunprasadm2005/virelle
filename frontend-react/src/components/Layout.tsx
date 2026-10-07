import { Link, NavLink, useNavigate } from 'react-router-dom';
import { clearToken, getToken } from '../lib/api';

const ITEMS: [string, string][] = [
  ['/', 'Home'],
  ['/discover', 'Discover'],
  ['/pantry', 'Pantry'],
  ['/meals', 'Meal Planner'],
  ['/shopping', 'Shopping List'],
  ['/taste', 'My Taste'],
];

export default function Layout({ children, name }: { children: React.ReactNode; name?: string }) {
  const navigate = useNavigate();
  const logged = !!getToken();
  function logout() {
    clearToken();
    navigate('/auth');
  }
  return (
    <>
      <header className="topbar">
        <Link className="logo" to="/"><img src="/assets/virelle-mark.svg" alt="Virelle" width={30} height={30} style={{ verticalAlign: -6, marginRight: 6 }} />Virelle</Link>
        <nav className="mainnav">
          {logged && ITEMS.map(([h, l]) => (
            <NavLink key={h} to={h} className={({ isActive }) => (isActive ? 'active' : '')}>{l}</NavLink>
          ))}
          {logged && <NavLink to="/research" className={({ isActive }) => (isActive ? 'active' : '')}>Research</NavLink>}
        </nav>
        <div className="userbox">
          {logged ? (
            <>
              <Link to="/profile">{name || 'Profile'}</Link>
              <a href="#" onClick={(e) => { e.preventDefault(); logout(); }}>Logout</a>
            </>
          ) : (
            <Link to="/auth">Log in</Link>
          )}
        </div>
      </header>
      <main>{children}</main>
    </>
  );
}
