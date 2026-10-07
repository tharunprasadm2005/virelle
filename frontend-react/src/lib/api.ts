/** Typed API client. Token in localStorage. 30s timeout via AbortController. */
const API = '';

export function getToken(): string {
  return localStorage.getItem('tf_token') || '';
}
export function setToken(t: string): void {
  localStorage.setItem('tf_token', t);
}
export function clearToken(): void {
  localStorage.removeItem('tf_token');
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 30000);
  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const tok = getToken();
    if (tok) headers['Authorization'] = `Bearer ${tok}`;
    const res = await fetch(API + path, { ...opts, signal: ctrl.signal, headers: { ...headers, ...(opts.headers as Record<string, string> || {}) } });
    if (res.status === 401) {
      if (!window.location.pathname.endsWith('/auth')) window.location.href = '/auth';
      throw new ApiError('Login required', 401);
    }
    const body = (await res.json().catch(() => ({}))) as { detail?: string } & T;
    if (!res.ok) throw new ApiError((body as { detail?: string }).detail || `Request failed (${res.status})`, res.status);
    return body as T;
  } finally {
    clearTimeout(timer);
  }
}

export function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

/* ---------- shared DTOs (mirror backend contracts) ---------- */
export interface RecipeCard {
  recipe_id: number;
  name: string;
  minutes: number | null;
  servings: number | null;
  rating: number | null;
  review_count: number;
  image_url: string | null;
  tags: string[];
  match_score?: number;
  why?: string[];
  coverage?: number;
  cook_score?: number;
}

export interface HomeStage {
  stage: 'getting_to_know' | 'personalized';
  message: string;
  shift?: number;
}

export interface HomeResponse {
  greeting_for: string;
  stage: HomeStage;
  recommended: RecipeCard[];
  shelves: { label: string; recipes: RecipeCard[] }[];
  saved: RecipeCard[];
  nutrition_goals?: string[];
}

export interface Me {
  id: number;
  name: string;
  email: string;
  has_preferences: boolean;
}
