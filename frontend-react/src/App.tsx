import { useEffect, useState } from 'react';
import { BrowserRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { api, getToken, type Me } from './lib/api';
import { ToastProvider } from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import AuthPage from './pages/Auth';
import Home from './pages/Home';
import Discover from './pages/Discover';
import Recipe from './pages/Recipe';
import Pantry from './pages/Pantry';
import Cook from './pages/Cook';
import Meals from './pages/Meals';
import Shopping from './pages/Shopping';
import Taste from './pages/Taste';
import Profile from './pages/Profile';
import Research from './pages/Research';
import Onboarding from './pages/Onboarding';
import Landing from './pages/Landing';

function RequireAuth({ me, setMe, children }: { me: Me | null; setMe: (m: Me | null) => void; children: JSX.Element }) {
  const navigate = useNavigate();
  useEffect(() => {
    if (!getToken()) {
      navigate('/welcome');
      return;
    }
    if (!me) {
      api<Me>('/api/auth/me')
        .then(setMe)
        .catch(() => navigate('/welcome'));
    }
  }, [me, navigate, setMe]);
  if (!getToken() || !me) return <main><p className="muted">Loading…</p></main>;
  return children;
}

function Guarded({ me, setMe, el }: { me: Me | null; setMe: (m: Me | null) => void; el: JSX.Element }) {
  return (
    <RequireAuth me={me} setMe={setMe}>
      <ErrorBoundary>{el}</ErrorBoundary>
    </RequireAuth>
  );
}

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/welcome" element={<Landing />} />
          <Route path="/auth" element={<AuthPage onLogin={setMe} />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/" element={<Guarded me={me} setMe={setMe} el={<Home me={me} />} />} />
          <Route path="/discover" element={<Guarded me={me} setMe={setMe} el={<Discover me={me} />} />} />
          <Route path="/recipe" element={<Guarded me={me} setMe={setMe} el={<Recipe me={me} />} />} />
          <Route path="/pantry" element={<Guarded me={me} setMe={setMe} el={<Pantry me={me} />} />} />
          <Route path="/cook" element={<Guarded me={me} setMe={setMe} el={<Cook me={me} />} />} />
          <Route path="/meals" element={<Guarded me={me} setMe={setMe} el={<Meals me={me} />} />} />
          <Route path="/shopping" element={<Guarded me={me} setMe={setMe} el={<Shopping me={me} />} />} />
          <Route path="/taste" element={<Guarded me={me} setMe={setMe} el={<Taste me={me} />} />} />
          <Route path="/profile" element={<Guarded me={me} setMe={setMe} el={<Profile me={me} />} />} />
          <Route path="/research" element={<Guarded me={me} setMe={setMe} el={<Research me={me} />} />} />
          <Route path="*" element={<Layout><div className="card"><h1>Not found</h1><p><a href="/">Back home</a></p></div></Layout>} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}
