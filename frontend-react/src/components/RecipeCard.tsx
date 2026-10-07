import { useState } from 'react';
import { api } from '../lib/api';
import { useToast } from './Toast';
import DishImage from './DishImage';
import { IconClock, IconHeart, IconServings, IconStar, IconThumbDown, IconThumbUp, IconPot } from './icons';
import type { RecipeCard } from '../lib/api';

const ACTION_LABEL: Record<string, string> = {
  SAVE: 'Saved to favorites',
  LIKE: 'Liked — more like this coming',
  DISLIKE: 'Got it — fewer like this',
  COOKED: 'Marked as cooked',
};

export default function RecipeCardView({ card, showCook = false, onDislike }: { card: RecipeCard; showCook?: boolean; onDislike?: (id: number) => void }) {
  const toast = useToast();
  const [saved, setSaved] = useState(false);
  const [liked, setLiked] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  async function act(kind: 'SAVE' | 'LIKE' | 'DISLIKE' | 'COOKED') {
    if (busy) return;
    setBusy(kind);
    try {
      await api(`/api/interactions/${card.recipe_id}`, {
        method: 'POST',
        body: JSON.stringify({ interaction_type: kind }),
      });
      if (kind === 'SAVE') setSaved(true);
      if (kind === 'LIKE') setLiked(true);
      if (kind === 'DISLIKE' && onDislike) onDislike(card.recipe_id);
      toast(ACTION_LABEL[kind]);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Action failed', false);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rcard">
      <DishImage name={card.name} url={card.image_url} />
      <div className="body">
        <a className="title" href={`/recipe?id=${card.recipe_id}`} style={{ color: 'inherit', textDecoration: 'none' }}>
          {card.name}
        </a>
        <div className="meta-row">
          {card.rating != null && <span><IconStar size={14} /> {card.rating.toFixed(1)}{card.review_count ? ` (${card.review_count})` : ''}</span>}
          {card.minutes != null && <span><IconClock size={14} /> {card.minutes} min</span>}
          {card.servings != null && <span><IconServings size={14} /> {Math.round(card.servings)} servings</span>}
        </div>
        {card.match_score != null && <div className="small muted">Matches you: {Math.round(card.match_score * 100)}%</div>}
        {card.coverage != null && <div className="small"><strong>{Math.round(card.coverage * 100)}% ingredient coverage</strong></div>}
        <div>
          {(card.tags || []).slice(0, 3).map((t) => (
            <span key={t} className="tagchip">{t}</span>
          ))}
        </div>
        <div className="actions">
          <button className={'icon' + (saved ? ' on' : '')} title="Save" aria-label="Save recipe" disabled={busy !== null} onClick={() => act('SAVE')}><IconHeart /></button>
          <button className={'icon' + (liked ? ' on' : '')} title="Like" aria-label="Like recipe" disabled={busy !== null} onClick={() => act('LIKE')}><IconThumbUp /></button>
          <button className="icon" title="Not for me" aria-label="Dislike recipe" disabled={busy !== null} onClick={() => act('DISLIKE')}><IconThumbDown /></button>
          {showCook && <button className="icon" title="I cooked this" aria-label="Mark as cooked" disabled={busy !== null} onClick={() => act('COOKED')}><IconPot /></button>}
        </div>
      </div>
    </div>
  );
}
