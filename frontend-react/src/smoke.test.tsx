/** Smoke: Pantry + Cook pages render without crashing (blank-page guard). */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Pantry from './pages/Pantry';
import Cook from './pages/Cook';
import Meals from './pages/Meals';
import Shopping from './pages/Shopping';
import Taste from './pages/Taste';
import Profile from './pages/Profile';
import Research from './pages/Research';
import Discover from './pages/Discover';
import Recipe from './pages/Recipe';
import Home from './pages/Home';
import Auth from './pages/Auth';
import Onboarding from './pages/Onboarding';
import Landing from './pages/Landing';

vi.mock('./lib/api', async (orig) => {
  const actual = await orig<Record<string, unknown>>();
  return {
    ...actual,
    api: vi.fn(async (path: string) => {
      if (path === '/api/pantry') return { items: [] };
      if (path.startsWith('/api/cook/matches')) return { pantry_empty: true, matches: [], message: 'empty pantry' };
      if (path === '/api/auth/me') return { id: 1, name: 'QA', email: 'q@x.com', has_preferences: true };
      if (path === '/api/taste') return { has_history: false, message: 'Not enough activity yet.' };
      if (path === '/api/profile') return { id: 1, name: 'QA', email: 'q@x.com', member_since: '2026-01-01',
        preferences: { diet: '', cuisines: [], priorities: [], avoid_ingredients: [], max_minutes: null, nutrition_goals: [] } };
      if (path === '/api/imports') return { imports: [] };
      if (path === '/api/collections') return { collections: [] };
      if (path === '/api/research/summary') return { ablation: [], dataset: { present: true } };
      if (path === '/api/demo_users') return { users: [] };
      if (path === '/api/discover') return { sections: [] };
      if (path.startsWith('/api/recipes/search')) return { results: [], mode: 'hybrid', weights: {} };
      if (path.startsWith('/api/recipes/')) return { recipe_id: 1, name: 'Test', minutes: 10, servings: 2,
        rating: 4, review_count: 1, image_url: null, tags: [], description_full: '', ingredients: ['a'],
        instructions: ['b'], diet_estimate: null };
      if (path === '/api/home') return { greeting_for: 'QA', stage: { stage: 'getting_to_know', message: 'hi' },
        recommended: [], shelves: [], saved: [] };
      if (path === '/api/collections') return { collections: [] };
      throw new Error('unmocked ' + path);
    }),
  };
});

function renderWith(route: string, el: JSX.Element) {
  window.localStorage.setItem('tf_token', 'test');
  return render(<MemoryRouter initialEntries={[route]}>{el}</MemoryRouter>);
}

describe('page smoke', () => {
  beforeEach(() => {
    window.localStorage.setItem('tf_token', 'test');
  });

  it('Pantry renders pantry UI, not blank', async () => {
    const { container } = renderWith('/pantry', <Pantry me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('My Pantry')) throw new Error('no heading yet');
    });
    expect(container.textContent).toContain('Add to pantry');
  });

  it('Cook renders cook UI, not blank', async () => {
    const { container } = renderWith('/cook', <Cook me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('What can I cook')) throw new Error('no heading yet');
    });
    expect(container.textContent).toContain('Find recipes');
  });

  it('Meals renders planner board, not blank', async () => {
    const { container } = renderWith('/meals', <Meals me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('Meal Planner')) throw new Error('no heading yet');
    });
    expect(container.textContent).toContain('Generate my week');
  });

  it('Shopping renders list UI, not blank', async () => {
    const { container } = renderWith('/shopping', <Shopping me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('Shopping List')) throw new Error('no heading yet');
    });
    expect(container.textContent).toContain('Merge duplicates');
  });

  it('Taste renders taste UI, not blank', async () => {
    const { container } = renderWith('/taste', <Taste me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('My Taste')) throw new Error('no heading yet');
    });
  });

  it('Profile renders profile UI, not blank', async () => {
    const { container } = renderWith('/profile', <Profile me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('Profile')) throw new Error('no heading yet');
    });
    expect(container.textContent).toContain('My collections');
  });

  it('Research renders research UI, not blank', async () => {
    const { container } = renderWith('/research', <Research me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('Research')) throw new Error('no heading yet');
    });
    expect(container.textContent).toContain('Ablation');
  });

  it('Discover renders search UI, not blank', async () => {
    const { container } = renderWith('/discover', <Discover me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('Discover')) throw new Error('no heading yet');
    });
    expect(container.textContent).toContain('Import a recipe');
  });

  it('Recipe renders detail UI, not blank', async () => {
    const { container } = renderWith('/recipe?id=1', <Recipe me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('Test')) throw new Error('no recipe yet');
    });
    expect(container.textContent).toContain('Ingredients');
  });

  it('Home renders home UI, not blank', async () => {
    const { container } = renderWith('/', <Home me={{ id: 1, name: 'QA', email: 'q@x.com', has_preferences: true }} />);
    await waitFor(() => {
      if (!container.textContent?.includes('Recommended for you')) throw new Error('no heading yet');
    });
  });

  it('Auth renders login UI, not blank', async () => {
    const noop = () => {};
    const { container } = renderWith('/auth', <Auth onLogin={noop} />);
    expect(container.textContent).toContain('Virelle');
    expect(container.textContent).toContain('Try the demo account');
  });

  it('Onboarding renders pills, not blank', async () => {
    const { container } = renderWith('/onboarding', <Onboarding />);
    expect(container.textContent).toContain('Welcome to Virelle');
  });

  it('Landing renders sections, not blank', async () => {
    const { container } = renderWith('/welcome', <Landing />);
    expect(container.textContent).toContain('Know what to cook');
  });
});
